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
from torch.utils.data import DataLoader, Subset, WeightedRandomSampler
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


def _stratified_indices(targets: list[int], classes: list[str]):
    """Make deterministic train/validation/test splits per label.

    A random split can put none of a small class in validation or test. That
    makes accuracy look good while hiding that the model cannot recognise a
    minority label, which is especially risky for waste handling.
    """
    by_class: dict[int, list[int]] = {index: [] for index in range(len(classes))}
    for index, target in enumerate(targets):
        by_class[target].append(index)

    generator = torch.Generator().manual_seed(config.seed)
    train_indices: list[int] = []
    val_indices: list[int] = []
    test_indices: list[int] = []

    for class_index, indices in by_class.items():
        count = len(indices)
        if count < config.min_images_per_class:
            raise ValueError(
                f"Class '{classes[class_index]}' has {count} images; at least "
                f"{config.min_images_per_class} are required for train/validation/test."
            )

        shuffled = torch.tensor(indices)[torch.randperm(count, generator=generator)].tolist()
        # Reserve at least one item for each held-out split. The remaining
        # images are training data, so every class is still represented there.
        n_val = max(1, round(count * config.val_split))
        n_test = max(1, round(count * config.test_split))
        if count - n_val - n_test < 1:
            n_val, n_test = 1, 1

        val_indices.extend(shuffled[:n_val])
        test_indices.extend(shuffled[n_val:n_val + n_test])
        train_indices.extend(shuffled[n_val + n_test:])

    return train_indices, val_indices, test_indices


def load_datasets(include_reference: bool = False):
    dataset_dir = Path(config.dataset_dir)
    if not dataset_dir.exists() or not any(dataset_dir.iterdir()):
        print(
            f"No dataset found at {dataset_dir}.\n\n"
            "Expected layout:\n"
            "  ml/dataset/<Label Name>/image001.jpg\n\n"
            "Each folder becomes a model label. See ml/dataset/README.md. "
            "Training cannot proceed without labelled data.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    train_tf, eval_tf = build_transforms(config.image_size)

    # ImageFolder derives classes from directory names. The list is persisted
    # in the checkpoint so serving uses the same labels without a fixed list.
    full = datasets.ImageFolder(dataset_dir)
    if len(full.classes) < 2:
        print("At least two labelled folders are required for classification.", file=sys.stderr)
        raise SystemExit(2)

    try:
        train_indices, val_indices, test_indices = _stratified_indices(
            full.targets, full.classes
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    # Each subset needs its own ImageFolder because it has a different image
    # transform. All three still use the same, deterministic indices.
    train_set = Subset(datasets.ImageFolder(dataset_dir, transform=train_tf), train_indices)
    val_set = Subset(datasets.ImageFolder(dataset_dir, transform=eval_tf), val_indices)
    test_set = Subset(datasets.ImageFolder(dataset_dir, transform=eval_tf), test_indices)

    if include_reference:
        # The rejection guard must compare deterministic embeddings. Do not use
        # the randomly augmented training transform for its reference images.
        reference_set = Subset(
            datasets.ImageFolder(dataset_dir, transform=eval_tf), train_indices
        )
        return train_set, val_set, test_set, full.classes, reference_set

    return train_set, val_set, test_set, full.classes


def class_balanced_sampler(train_set: Subset) -> WeightedRandomSampler:
    """Sample smaller classes as often as large ones during training."""
    targets = train_set.dataset.targets
    labels = [targets[index] for index in train_set.indices]
    counts = torch.bincount(torch.tensor(labels), minlength=len(train_set.dataset.classes))
    weights = [1.0 / counts[label].item() for label in labels]
    return WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)


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


def _feature_embeddings(model: nn.Module, images: torch.Tensor) -> torch.Tensor:
    """Return a normalized backbone feature vector for each image.

    The classifier must choose one of its labels, even for a photograph of a
    person or a blank screen.  Comparing its backbone features to reviewed
    training images gives the serving layer a separate, open-set rejection
    signal before it trusts that forced label.
    """
    features = model.features(images)
    features = model.avgpool(features)
    features = torch.flatten(features, 1)
    return torch.nn.functional.normalize(features, dim=1)


def build_similarity_guard(
    model: nn.Module,
    reference_set: Subset,
    validation_set: Subset,
    device: torch.device,
) -> dict:
    """Calibrate an open-set rejection threshold on the validation split."""
    def collect(dataset: Subset) -> tuple[torch.Tensor, torch.Tensor]:
        vectors, labels = [], []
        loader = DataLoader(dataset, batch_size=config.batch_size,
                            num_workers=config.num_workers)
        with torch.no_grad():
            for images, batch_labels in loader:
                vectors.append(_feature_embeddings(model, images.to(device)).cpu())
                labels.append(batch_labels.cpu())
        return torch.cat(vectors), torch.cat(labels)

    model.eval()
    references, reference_labels = collect(reference_set)
    validation, validation_labels = collect(validation_set)
    similarity = validation @ references.T
    same_label = reference_labels.unsqueeze(0) == validation_labels.unsqueeze(1)
    nearest_same_label = similarity.masked_fill(~same_label, -1.0).max(dim=1).values

    # Reject only the least similar five percent of known validation images.
    # This is intentionally conservative: the gate is a safety fallback, not
    # a substitute for collecting representative negative examples.
    threshold = float(torch.quantile(nearest_same_label, 0.05))
    return {
        "method": "nearest_feature_cosine",
        "threshold": threshold,
        "calibration_quantile": 0.05,
        "validation_samples": len(validation_set),
        "reference_features": references.to(torch.float16),
    }


def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    train_set, val_set, test_set, classes, reference_set = load_datasets(
        include_reference=True
    )
    print(f"Images -> train {len(train_set)} | val {len(val_set)} | test {len(test_set)}")

    train_loader = DataLoader(
        train_set,
        batch_size=config.batch_size,
        sampler=class_balanced_sampler(train_set),
        num_workers=config.num_workers,
    )
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
                "class_to_idx": {name: index for index, name in enumerate(classes)},
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

    checkpoint["similarity_guard"] = build_similarity_guard(
        model, reference_set, val_set, device
    )
    torch.save(checkpoint, config.checkpoint_path)

    with open(config.output_dir / "history.json", "w") as fh:
        json.dump(history, fh, indent=2)

    print("\nTraining finished.")
    print(f"  Held-out test loss:     {test_loss:.4f}")
    print(f"  Held-out test accuracy: {test_acc:.4f}")
    print("\nRun `python -m ml.evaluate` for precision, recall, F1 and the "
          "confusion matrix. Those are the figures to quote - not these.")


if __name__ == "__main__":
    main()
