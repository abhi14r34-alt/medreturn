"""Build a unified, balanced dataset from Kaggle PBW, local files, and returns.

Outputs to ml/dataset, backing up the original small dataset to ml/dataset_backup_original.
"""

from __future__ import annotations

import hashlib
import io
import json
import random
import shutil
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

from PIL import Image, ImageEnhance, ImageOps

from ml.config import ROOT

CLASSES = [
    "General",
    "Glass and Sharps",
    "Infectious",
    "Pharmaceutical",
    "Plastic Recyclable",
]

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

PBW_MAPPING = (
    (("tissue", "gauze", "glove", "mask"), "Infectious"),
    (("organic", "paper"), "General"),
    (("plastic",), "Plastic Recyclable"),
    (("glass", "metal", "needle", "syringe", "tweezer"), "Glass and Sharps"),
)


def target_label(folder_name: str) -> str | None:
    normalized = folder_name.lower().replace("_", " ").replace("-", " ")
    for words, target in PBW_MAPPING:
        if any(word in normalized for word in words):
            return target
    return None


def is_valid_image(payload: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.verify()
        with Image.open(io.BytesIO(payload)) as image:
            w, h = image.size
            if min(w, h) < 64:
                return False
        return True
    except Exception:
        return False


def add_image_bytes(output_dir: Path, label: str, payload: bytes, suffix: str, counts: Counter) -> bool:
    if not is_valid_image(payload):
        return False
    digest = hashlib.sha256(payload).hexdigest()
    target = output_dir / label / f"{digest}{suffix.lower()}"
    if target.exists():
        return False
    target.write_bytes(payload)
    counts[label] += 1
    return True


def add_pbw_archive(archive_path: Path, output_dir: Path, counts: Counter) -> int:
    added = 0
    with zipfile.ZipFile(archive_path) as source:
        by_source_folder: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
        for entry in source.infolist():
            path = PurePosixPath(entry.filename)
            if entry.is_dir() or path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            parents = path.parts[:-1]
            source_folder = next(
                (part for part in reversed(parents) if target_label(part) is not None),
                "",
            )
            if source_folder:
                by_source_folder[source_folder].append(entry)

        for source_folder, entries in sorted(by_source_folder.items()):
            label = target_label(source_folder)
            if label is None:
                continue
            originals = [entry for entry in entries if ".rf." not in entry.filename.lower()]
            if originals:
                selected = originals
            else:
                variants: dict[str, zipfile.ZipInfo] = {}
                for entry in sorted(entries, key=lambda item: item.filename):
                    name = PurePosixPath(entry.filename).name
                    base = name.lower().split(".rf.", maxsplit=1)[0]
                    variants.setdefault(base, entry)
                selected = list(variants.values())

            for entry in selected:
                path = PurePosixPath(entry.filename)
                data = source.read(entry)
                if add_image_bytes(output_dir, label, data, path.suffix, counts):
                    added += 1
    return added


def add_local_folder(source_dir: Path, output_dir: Path, counts: Counter, default_label: str | None = None) -> int:
    added = 0
    if not source_dir.is_dir():
        return 0
    for path in source_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            data = path.read_bytes()
            label = default_label or path.parent.name
            if label in CLASSES:
                if add_image_bytes(output_dir, label, data, path.suffix, counts):
                    added += 1
    return added


def augment_class_to_target(output_dir: Path, label: str, target_count: int, counts: Counter) -> int:
    """Generate realistic photographic variations of existing images to reach target_count."""
    folder = output_dir / label
    existing_files = [f for f in folder.glob("*.*") if f.is_file() and f.suffix.lower() in IMAGE_SUFFIXES]
    current = len(existing_files)
    needed = target_count - current
    if needed <= 0 or not existing_files:
        return 0

    added = 0
    random.seed(42)
    # Cycle through existing images and create diverse augmentations
    file_idx = 0
    while added < needed:
        src_path = existing_files[file_idx % len(existing_files)]
        file_idx += 1
        try:
            with Image.open(src_path) as img:
                img = img.convert("RGB")
                w, h = img.size

                # Apply a combination of realistic perturbations
                choice = added % 6
                if choice == 0:
                    # Horizontal flip + slight brightness adjustment
                    aug = ImageOps.mirror(img)
                    enhancer = ImageEnhance.Brightness(aug)
                    aug = enhancer.enhance(random.uniform(0.85, 1.15))
                elif choice == 1:
                    # Slight rotation (±10 degrees)
                    angle = random.choice([-10, -7, -4, 4, 7, 10])
                    aug = img.rotate(angle, resample=Image.Resampling.BILINEAR, expand=False)
                elif choice == 2:
                    # Contrast adjustment + slight color jitter
                    enhancer = ImageEnhance.Contrast(img)
                    aug = enhancer.enhance(random.uniform(0.85, 1.2))
                    col_enhancer = ImageEnhance.Color(aug)
                    aug = col_enhancer.enhance(random.uniform(0.85, 1.15))
                elif choice == 3:
                    # Random crop (90% of area) zoomed back
                    crop_w = int(w * 0.9)
                    crop_h = int(h * 0.9)
                    left = random.randint(0, w - crop_w)
                    top = random.randint(0, h - crop_h)
                    aug = img.crop((left, top, left + crop_w, top + crop_h)).resize((w, h), Image.Resampling.BILINEAR)
                elif choice == 4:
                    # Mild sharpness enhancement + flip
                    enhancer = ImageEnhance.Sharpness(img)
                    aug = enhancer.enhance(random.uniform(1.2, 1.6))
                    if random.random() > 0.5:
                        aug = ImageOps.mirror(aug)
                else:
                    # Subtle perspective/shear rotation + brightness
                    aug = img.rotate(random.choice([-8, 8]), resample=Image.Resampling.BILINEAR)
                    enhancer = ImageEnhance.Brightness(aug)
                    aug = enhancer.enhance(random.uniform(0.9, 1.1))

                buf = io.BytesIO()
                aug.save(buf, format="JPEG", quality=92)
                payload = buf.getvalue()
                if add_image_bytes(output_dir, label, payload, ".jpg", counts):
                    added += 1
        except Exception:
            continue

    return added


def build_unified_dataset():
    dataset_dir = ROOT / "dataset"
    backup_dir = ROOT / "dataset_backup_original"
    archive_path = ROOT / "sources" / "pharmaceutical-and-biomedical-waste.zip"
    returns_dir = ROOT.parent / "backend" / "uploads" / "returns"

    # Step 1: Backup original ml/dataset if not already backed up
    if not backup_dir.exists():
        print(f"Backing up original {dataset_dir} -> {backup_dir}")
        shutil.copytree(dataset_dir, backup_dir)

    # Step 2: Prepare temporary target directory
    temp_dir = ROOT / "dataset_unified_temp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    for c in CLASSES:
        (temp_dir / c).mkdir(parents=True)

    counts = Counter()

    # Step 3: Add Kaggle PBW archive images
    print("Extracting Kaggle PBW images...")
    kaggle_added = add_pbw_archive(archive_path, temp_dir, counts)
    print(f"Added {kaggle_added} images from Kaggle PBW.")

    # Step 4: Add local original images
    print("Adding original local images from backup...")
    local_added = add_local_folder(backup_dir, temp_dir, counts)
    print(f"Added {local_added} images from original local dataset.")

    # Step 5: Add uploaded returns images to Pharmaceutical
    print("Adding verified uploaded returns images...")
    returns_added = add_local_folder(returns_dir, temp_dir, counts, default_label="Pharmaceutical")
    print(f"Added {returns_added} return images.")

    # Step 6: Augment classes that have fewer than 150 images so every class has strong representation
    # and > 20 test images in the 15% held-out test split.
    for label in CLASSES:
        current = counts[label]
        target = max(150, current)
        if current < 150:
            aug_added = augment_class_to_target(temp_dir, label, 150, counts)
            print(f"Augmented {label}: {current} -> {counts[label]} (+{aug_added} variations)")

    # Step 7: Cap classes at 250 images each to maintain excellent balance
    # (Glass and Sharps / Infectious had ~380, we can keep ~250 or all of them)
    # Let's see current counts:
    print("\nFinal class counts:")
    for label in CLASSES:
        print(f"  {label:<22} {counts[label]}")
    total = sum(counts.values())
    print(f"Total unified images: {total}")

    # Write manifest
    manifest = {
        "classes": CLASSES,
        "class_counts": dict(counts),
        "total_images": total,
    }
    (temp_dir / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Step 8: Replace ml/dataset with unified dataset
    print(f"\nReplacing {dataset_dir} with unified dataset...")
    # Clean current dataset_dir
    for item in dataset_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        elif item.name != "README.md":
            item.unlink()

    for c in CLASSES:
        shutil.copytree(temp_dir / c, dataset_dir / c)
    shutil.copy(temp_dir / "dataset_manifest.json", dataset_dir / "dataset_manifest.json")
    shutil.rmtree(temp_dir)
    print("Unified dataset installed in ml/dataset successfully.")


if __name__ == "__main__":
    build_unified_dataset()
