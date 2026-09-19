"""Evaluate the trained checkpoint on the held-out test split.

    python -m ml.evaluate

Writes ml/models/metrics.json with accuracy, macro/weighted precision,
recall, F1, per-class figures and the confusion matrix. These are the only
numbers that should ever appear in a report or on the Model Information
page. Nothing is estimated or rounded up for presentation.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime

import torch
from torch.utils.data import DataLoader

from ml.config import config
from ml.train import build_model, load_datasets


def confusion_matrix(y_true, y_pred, n: int):
    matrix = [[0] * n for _ in range(n)]
    for true, pred in zip(y_true, y_pred):
        matrix[true][pred] += 1
    return matrix


def prf_per_class(matrix, index):
    tp = matrix[index][index]
    fp = sum(matrix[r][index] for r in range(len(matrix))) - tp
    fn = sum(matrix[index]) - tp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)
    return precision, recall, f1, sum(matrix[index])


def main() -> None:
    if not config.checkpoint_path.exists():
        print(f"No checkpoint at {config.checkpoint_path}. Train first: "
              "python -m ml.train", file=sys.stderr)
        raise SystemExit(2)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _train, _val, test_set, classes = load_datasets()
    loader = DataLoader(test_set, batch_size=config.batch_size)

    checkpoint = torch.load(config.checkpoint_path, map_location=device)
    if checkpoint.get("classes") != classes:
        print("Checkpoint class list differs from the dataset. Retrain before "
              "evaluating; the metrics would be meaningless.", file=sys.stderr)
        raise SystemExit(2)

    architecture = checkpoint.get("architecture", config.architecture)
    model = build_model(architecture, len(classes), pretrained=False)
    model.load_state_dict(checkpoint["state_dict"])
    model.to(device).eval()

    y_true, y_pred = [], []
    with torch.no_grad():
        for images, labels in loader:
            outputs = model(images.to(device))
            y_pred.extend(outputs.argmax(1).cpu().tolist())
            y_true.extend(labels.tolist())

    matrix = confusion_matrix(y_true, y_pred, len(classes))
    accuracy = sum(matrix[i][i] for i in range(len(classes))) / max(1, len(y_true))

    per_class, macro_p, macro_r, macro_f1, weighted_f1 = {}, 0.0, 0.0, 0.0, 0.0
    for index, name in enumerate(classes):
        precision, recall, f1, support = prf_per_class(matrix, index)
        per_class[name] = {
            "precision": round(precision, 4), "recall": round(recall, 4),
            "f1": round(f1, 4), "support": support,
        }
        macro_p += precision
        macro_r += recall
        macro_f1 += f1
        weighted_f1 += f1 * support

    n = len(classes)
    metrics = {
        "evaluated_at": datetime.utcnow().isoformat(),
        "checkpoint": str(config.checkpoint_path),
        "test_images": len(y_true),
        "classes": classes,
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_p / n, 4),
        "macro_recall": round(macro_r / n, 4),
        "macro_f1": round(macro_f1 / n, 4),
        "weighted_f1": round(weighted_f1 / max(1, len(y_true)), 4),
        "per_class": per_class,
        "confusion_matrix": matrix,
    }

    with open(config.metrics_path, "w") as fh:
        json.dump(metrics, fh, indent=2)

    print(f"Test images: {len(y_true)}")
    print(f"Accuracy:    {metrics['accuracy']}")
    print(f"Macro F1:    {metrics['macro_f1']}")
    print("\nPer class:")
    for name, values in per_class.items():
        print(f"  {name:<20} P {values['precision']:.3f}  R {values['recall']:.3f}"
              f"  F1 {values['f1']:.3f}  n={values['support']}")
    print(f"\nWritten to {config.metrics_path}")
    print("Copy these into the model_versions row for this version.")


if __name__ == "__main__":
    main()
