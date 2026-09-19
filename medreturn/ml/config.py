"""Training configuration.

Classes are deliberately *not* declared here. ``ImageFolder`` learns them
from the directory names in ``ml/dataset`` and writes that exact list into the
checkpoint. This lets a deployment recognise the labels it was actually
trained on instead of forcing every image into a source-code category list.
"""

import os
from dataclasses import dataclass
from pathlib import Path
ROOT = Path(__file__).resolve().parent


@dataclass
class TrainConfig:
    # Keep the hand-labelled dataset as the default, while allowing an
    # alternate prepared dataset to be selected without editing source code.
    # This is useful for reproducible pilot training runs, e.g. with a public
    # source dataset kept separate from locally collected images.
    dataset_dir: Path = Path(os.environ.get("ML_DATASET_DIR", ROOT / "dataset"))
    # Keep pilot checkpoints separate from the checkpoint served by the API.
    output_dir: Path = Path(os.environ.get("ML_OUTPUT_DIR", ROOT / "models"))
    checkpoint_name: str = "model.pth"

    architecture: str = "mobilenet_v3_small"  # or "efficientnet_b0"
    pretrained: bool = True                    # transfer learning, not from scratch
    freeze_backbone_epochs: int = 3            # warm up the head first

    image_size: int = 224
    batch_size: int = 32
    epochs: int = 25
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    patience: int = 6                          # early stopping

    val_split: float = 0.15
    test_split: float = 0.15
    min_images_per_class: int = 3
    seed: int = 42
    # A single-process loader is the reliable default on Windows and in
    # restricted deployment environments. Raise this on a Linux GPU runner.
    num_workers: int = 0

    @property
    def checkpoint_path(self) -> Path:
        return self.output_dir / self.checkpoint_name

    @property
    def metrics_path(self) -> Path:
        return self.output_dir / "metrics.json"


config = TrainConfig()
