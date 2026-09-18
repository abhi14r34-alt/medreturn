"""Transfer-learning training for the waste classifier.

    python -m ml.train

Pipeline: dataset -> split -> preprocessing -> augmentation -> transfer
learning -> per-epoch validation -> best-checkpoint selection -> save.

The checkpoint stores the class list alongside the weights, so the serving
layer can never mismatch labels against a different model.

Nothing here prints a metric it did not measure. If you have no labelled
dataset yet, this script will tell you so and exit rather than producing a
model that appears trained.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets
from torchvision.models import (
    MobileNet_V3_Small_Weights,
    EfficientNet_B0_Weights,
    efficientnet_b0,
    mobilenet_v3_small,
)

from ml.config import config
from ml.preprocessing.transforms import build_transforms


def build_model(architecture: str, num_classes: int, pretrained: bool) -> nn.Module:
    """Load an ImageNet backbone and replace the classifier head."""
    if architecture == "efficientnet_b0":
        weights = EfficientNet_B0_Weights.DEFAULT if pretrained else None
        model = efficientnet_b0(weights=weights)
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(in_features, num_classes)
    else:
        weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
        model = mobilenet_v3_small(weights=weights)
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(in_features, num_classes)
    return model


def set_backbone_trainable(model: nn.Module, trainable: bool) -> None:
    for name, parameter in model.named_parameters():
        if not name.startswith("classifier"):
            parameter.requires_grad = trainable


def load_datasets():
    dataset_dir = Path(config.dataset_dir)
    if not dataset_dir.exists() or not any(dataset_dir.iterdir()):
        print(
            f"No dataset found at {dataset_dir}.\n\n"
            "Expected layout:\n"
            "  ml/dataset/<Class Name>/image001.jpg\n\n"
            "One folder per class, matching CLASSES in ml/config.py. See\n"
            "ml/dataset/README.md. Training cannot proceed without labelled data.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    train_tf, eval_tf = build_transforms(config.image_size)

    # ImageFolder derives classes from directory names.
    full = datasets.ImageFolder(dataset_dir)
    if full.classes != config.classes:
        print(
            "Dataset folders do not match CLASSES in ml/config.py.\n"
            f"  folders: {full.classes}\n"
            f"  config:  {config.classes}\n"
            "Fix one of them before training; a mismatch here silently mislabels "
            "every prediction the API makes.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    total = len(full)
    n_val = int(total * config.val_split)
    n_test = int(total * config.test_split)
    n_train = total - n_val - n_test
    if min(n_train, n_val, n_test) <= 0:
        print(f"Dataset is too small to split ({total} images).", file=sys.stderr)
        raise SystemExit(2)

    generator = torch.Generator().manual_seed(config.seed)
    train_set, val_set, test_set = random_split(
        full, [n_train, n_val, n_test], generator=generator
    )

    # Subsets share the parent transform, so wrap them to apply the right one.
    train_set.dataset = datasets.ImageFolder(dataset_dir, transform=train_tf)
    val_set.dataset = datasets.ImageFolder(dataset_dir, transform=eval_tf)
    test_set.dataset = datasets.ImageFolder(dataset_dir, transform=eval_tf)

    return train_set, val_set, test_set, full.classes


def run_epoch(model, loader, criterion, optimizer, device, train: bool):
    model.train() if train else model.eval()
    total_loss, correct, seen = 0.0, 0, 0

    with torch.set_grad_enabled(train):
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            if train:
                optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            if train:
                loss.backward()
                optimizer.step()

            total_loss += loss.item() * labels.size(0)
            correct += (outputs.argmax(1) == labels).sum().item()
            seen += labels.size(0)

    return total_loss / seen, correct / seen


def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    train_set, val_set, test_set, classes = load_datasets()
    print(f"Images -> train {len(train_set)} | val {len(val_set)} | test {len(test_set)}")

    train_loader = DataLoader(train_set, batch_size=config.batch_size, shuffle=True,
                              num_workers=config.num_workers)
    val_loader = DataLoader(val_set, batch_size=config.batch_size,
                            num_workers=config.num_workers)
    test_loader = DataLoader(test_set, batch_size=config.batch_size,
                             num_workers=config.num_workers)

    model = build_model(config.architecture, len(classes), config.pretrained).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate,
                                  weight_decay=config.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=2)

    config.output_dir.mkdir(parents=True, exist_ok=True)

    best_val_loss = float("inf")
    epochs_without_improvement = 0
    history = []

    for epoch in range(1, config.epochs + 1):
        # Warm up the new head before unfreezing the pretrained backbone.
        set_backbone_trainable(model, epoch > config.freeze_backbone_epochs)

        train_loss, train_acc = run_epoch(model, train_loader, criterion,
                                          optimizer, device, train=True)
        val_loss, val_acc = run_epoch(model, val_loader, criterion,
                                      optimizer, device, train=False)
        scheduler.step(val_loss)

        history.append({
            "epoch": epoch, "train_loss": round(train_loss, 4),
            "train_accuracy": round(train_acc, 4),
            "val_loss": round(val_loss, 4), "val_accuracy": round(val_acc, 4),
        })
        print(f"epoch {epoch:>3}  train_loss {train_loss:.4f}  train_acc {train_acc:.4f}"
              f"  val_loss {val_loss:.4f}  val_acc {val_acc:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_without_improvement = 0
            torch.save({
                "state_dict": model.state_dict(),
                "classes": classes,
                "architecture": config.architecture,
                "image_size": config.image_size,
                "trained_at": datetime.utcnow().isoformat(),
                "config": {k: str(v) for k, v in asdict(config).items()},
            }, config.checkpoint_path)
            print(f"  saved best checkpoint -> {config.checkpoint_path}")
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= config.patience:
                print(f"Early stopping at epoch {epoch}.")
                break

    # Final numbers come from the held-out test split and the best weights.
    checkpoint = torch.load(config.checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint["state_dict"])
    test_loss, test_acc = run_epoch(model, test_loader, criterion,
                                    optimizer, device, train=False)

    with open(config.output_dir / "history.json", "w") as fh:
        json.dump(history, fh, indent=2)

    print("\nTraining finished.")
    print(f"  Held-out test loss:     {test_loss:.4f}")
    print(f"  Held-out test accuracy: {test_acc:.4f}")
    print("\nRun `python -m ml.evaluate` for precision, recall, F1 and the "
          "confusion matrix. Those are the figures to quote - not these.")


if __name__ == "__main__":
    main()
