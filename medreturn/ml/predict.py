"""Single-image prediction from the command line.

    python -m ml.predict path/to/image.jpg

Useful for sanity-checking a checkpoint outside the API. It applies the
same confidence gate the backend uses, so the routing decision shown here
matches what the service would do.
"""

from __future__ import annotations

import argparse
import sys

import torch
from PIL import Image

from ml.config import config
from ml.preprocessing.transforms import build_transforms
from ml.train import build_model

CONFIDENCE_THRESHOLD = 0.80  # keep in step with backend CONFIDENCE_THRESHOLD


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--threshold", type=float, default=CONFIDENCE_THRESHOLD)
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    if not config.checkpoint_path.exists():
        print(f"No checkpoint at {config.checkpoint_path}. Train first.",
              file=sys.stderr)
        raise SystemExit(2)

    checkpoint = torch.load(config.checkpoint_path, map_location="cpu")
    classes = checkpoint["classes"]

    model = build_model(checkpoint.get("architecture", config.architecture),
                        len(classes), pretrained=False)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    _train_tf, eval_tf = build_transforms(checkpoint.get("image_size", 224))
    tensor = eval_tf(Image.open(args.image).convert("RGB")).unsqueeze(0)

    with torch.no_grad():
        probabilities = torch.softmax(model(tensor), dim=1)[0]

    top = torch.topk(probabilities, min(args.top_k, len(classes)))
    print(f"Image: {args.image}\n")
    for score, index in zip(top.values.tolist(), top.indices.tolist()):
        print(f"  {classes[index]:<22} {score:.4f}")

    best_score = top.values[0].item()
    best_class = classes[top.indices[0].item()]
    print()
    if best_score >= args.threshold:
        compartment = chr(ord("A") + classes.index(best_class))
        print(f"Decision: ACCEPTED -> COMPARTMENT {compartment}")
    else:
        print(f"Decision: QUARANTINED (confidence {best_score:.2f} < "
              f"threshold {args.threshold:.2f}) -> human verification required")


if __name__ == "__main__":
    main()
