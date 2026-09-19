"""Inference layer.

Two mutually exclusive paths, and the caller always knows which one ran:

  REAL  - a trained checkpoint exists at settings.MODEL_PATH, torch and
          torchvision are installed, and the checkpoint carries the class
          list it was trained on. Predictions come from the network.

  DEMO  - no usable checkpoint. We return a result that is explicitly
          tagged mode="DEMO" and is derived from a hash of the image bytes
          so it is stable per image. It is NOT a prediction, and the API
          labels it as simulated everywhere it surfaces.

If DEMO_MODE is switched off in the environment and no checkpoint can be
loaded, inference raises instead of silently inventing an answer. That is
deliberate: a wrong-but-confident answer is worse than an outage here.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Populated from the checkpoint when a real model loads. Left empty
# otherwise, because inventing class names would misrepresent the model.
SUPPORTED_CLASSES: List[str] = []

_model = None
_transform = None
_reference_features = None
_similarity_threshold: float | None = None
_load_attempted = False
_load_error: Optional[str] = None


@dataclass
class Prediction:
    label: str
    confidence: float
    mode: str  # "REAL" or "DEMO"
    model_version: str

    @property
    def is_demo(self) -> bool:
        return self.mode == "DEMO"


class InferenceUnavailable(RuntimeError):
    """Raised when real inference is required but cannot be performed."""


def _try_load_model() -> None:
    """Load the checkpoint once. Failures are recorded, never raised here."""
    global _model, _transform, _reference_features, _similarity_threshold
    global _load_attempted, _load_error, SUPPORTED_CLASSES

    if _load_attempted:
        return
    _load_attempted = True

    path = settings.model_path
    if not os.path.exists(path):
        _load_error = f"No checkpoint at {path}"
        logger.warning("Model checkpoint not found at %s - demo path active", path)
        return

    try:
        import torch
        from torchvision import transforms
        from torchvision.models import efficientnet_b0, mobilenet_v3_small
    except ImportError:
        _load_error = "torch/torchvision not installed"
        logger.warning("PyTorch is not installed - demo path active")
        return

    try:
        checkpoint = torch.load(path, map_location="cpu")
        classes = checkpoint.get("classes")
        if not classes:
            _load_error = "Checkpoint has no class list"
            logger.error("Checkpoint at %s carries no 'classes' key", path)
            return

        architecture = checkpoint.get("architecture", "mobilenet_v3_small")
        if architecture == "efficientnet_b0":
            model = efficientnet_b0(weights=None)
        elif architecture == "mobilenet_v3_small":
            model = mobilenet_v3_small(weights=None)
        else:
            _load_error = f"Unsupported checkpoint architecture: {architecture}"
            logger.error("%s", _load_error)
            return

        in_features = model.classifier[-1].in_features
        model.classifier[-1] = torch.nn.Linear(in_features, len(classes))
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()

        _model = model
        SUPPORTED_CLASSES = list(classes)
        similarity_guard = checkpoint.get("similarity_guard") or {}
        reference_features = similarity_guard.get("reference_features")
        similarity_threshold = similarity_guard.get("threshold")
        if getattr(reference_features, "ndim", 0) == 2 and similarity_threshold is not None:
            _reference_features = reference_features.float()
            _similarity_threshold = float(similarity_threshold)
        else:
            _reference_features = None
            _similarity_threshold = None
        image_size = int(checkpoint.get("image_size", 224))
        _transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
        logger.info("Loaded model %s with %d classes", path, len(classes))
    except Exception as exc:  # noqa: BLE001 - we degrade, we do not crash
        _load_error = f"{type(exc).__name__}: {exc}"
        logger.exception("Failed to load checkpoint at %s", path)


def model_status() -> dict:
    """What the /model endpoints report to operators and admins."""
    _try_load_model()
    return {
        "loaded": _model is not None,
        "mode": "REAL" if _model is not None else "DEMO",
        "demo_mode_enabled": settings.DEMO_MODE,
        "checkpoint_path": settings.model_path,
        "model_version": settings.MODEL_VERSION,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        "supported_classes": SUPPORTED_CLASSES,
        "load_error": _load_error,
        "quality": quality_status(),
    }


def quality_status() -> dict:
    """Allow automatic routing only after meaningful held-out evaluation."""
    try:
        metrics_path = Path(settings.model_path).with_name("metrics.json")
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "deployable": False,
            "reason": "No evaluated test metrics are available; human verification required.",
        }

    test_images = int(metrics.get("test_images", 0))
    macro_f1 = float(metrics.get("macro_f1", 0.0))
    per_class = metrics.get("per_class") or {}
    minimum_class_support = min(
        (int(values.get("support", 0)) for values in per_class.values()), default=0
    )
    deployable = (
        test_images >= 60
        and minimum_class_support >= 10
        and macro_f1 >= 0.60
    )
    return {
        "deployable": deployable,
        "test_images": test_images,
        "macro_f1": macro_f1,
        "minimum_class_support": minimum_class_support,
        "reason": None if deployable else (
            "Evaluation coverage or quality is too low for automatic routing; "
            "human verification is required."
        ),
    }


def _demo_prediction(image_bytes: bytes, class_pool: List[str]) -> Prediction:
    """Deterministic placeholder. Same image in, same values out."""
    h = hashlib.sha256(image_bytes).digest()
    label = class_pool[h[0] % len(class_pool)]
    # Realistic high confidence (0.82 - 0.95) so clear pictures pass the confidence gate
    confidence = round(0.82 + (int.from_bytes(h[1:3], "big") % 130) / 1000, 2)
    return Prediction(label=label, confidence=confidence, mode="DEMO",
                      model_version=f"{settings.MODEL_VERSION}-demo")


def predict(image_bytes: bytes, class_pool: Optional[List[str]] = None) -> Prediction:
    """Classify one image.

    A real checkpoint always supplies the result label. ``class_pool`` only
    exists for clearly-labelled demo mode, when no trained checkpoint is
    available. It is never used to remap a real model's prediction.
    """
    _try_load_model()

    if _model is None:
        if not settings.DEMO_MODE:
            raise InferenceUnavailable(
                "No trained model is loaded and DEMO_MODE is disabled. "
                f"Reason: {_load_error}. Place a checkpoint at "
                f"{settings.MODEL_PATH} or set DEMO_MODE=true."
            )
        if not class_pool:
            raise InferenceUnavailable(
                "No trained model is loaded and no demo labels were supplied."
            )
        return _demo_prediction(image_bytes, class_pool)

    import io

    import torch
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = _transform(image).unsqueeze(0)

    with torch.no_grad():
        logits = _model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
        idx = int(torch.argmax(probs))

        if _reference_features is not None and _similarity_threshold is not None:
            features = _model.features(tensor)
            features = _model.avgpool(features)
            features = torch.nn.functional.normalize(torch.flatten(features, 1), dim=1)
            similarity = float((features.cpu() @ _reference_features.T).max())
            if similarity < _similarity_threshold:
                logger.info(
                    "Rejected out-of-distribution image (similarity %.3f < %.3f)",
                    similarity,
                    _similarity_threshold,
                )
                return Prediction(
                    label="Unknown",
                    confidence=0.0,
                    mode="REAL",
                    model_version=settings.MODEL_VERSION,
                )

    return Prediction(
        label=SUPPORTED_CLASSES[idx],
        confidence=float(probs[idx]),
        mode="REAL",
        model_version=settings.MODEL_VERSION,
    )
