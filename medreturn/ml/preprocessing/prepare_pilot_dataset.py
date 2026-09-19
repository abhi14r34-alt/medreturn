"""Prepare a reproducible pilot dataset from the public PBW archive.

PBW has item labels, rather than clinical disposal labels. This utility maps
those published item folders to MedReturn's existing broad labels, writes the
exact mapping to a manifest and skips Roboflow ``.rf.`` augmented siblings to
avoid train/test leakage.

Run from the repository root:
    ..\\backend\\.venv\\Scripts\\python -m ml.preprocessing.prepare_pilot_dataset
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from PIL import Image, UnidentifiedImageError

from ml.config import ROOT


CLASSES = [
    "General",
    "Glass and Sharps",
    "Infectious",
    "Pharmaceutical",
    "Plastic Recyclable",
]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

# Source folders are item-level labels. Sharp objects retain the existing
# combined route, while personal protective equipment is a contamination proxy.
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
        return True
    except (UnidentifiedImageError, OSError, ValueError):
        return False


def add_image(output: Path, label: str, payload: bytes, suffix: str, counts: Counter) -> bool:
    if not is_valid_image(payload):
        return False
    target = output / label / f"{hashlib.sha256(payload).hexdigest()}{suffix.lower()}"
    if target.exists():
        return False
    target.write_bytes(payload)
    counts[label] += 1
    return True


def add_pbw_archive(archive: Path, output: Path, counts: Counter) -> tuple[int, Counter]:
    """Add source originals, or one variant per original when required.

    Some PBW folders ship their photographs only as Roboflow variants.  For
    those folders we select one stable variant for every pre-``.rf.`` basename
    rather than dropping the class entirely or letting sibling variants leak
    into different train/validation/test partitions.
    """
    added = 0
    source_counts: Counter = Counter()
    with zipfile.ZipFile(archive) as source:
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
                if add_image(output, label, source.read(entry), path.suffix, counts):
                    added += 1
                    source_counts[source_folder] += 1
    return added, source_counts


def add_local_images(
    local_dataset: Path,
    output: Path,
    counts: Counter,
    excluded_labels: set[str] | None = None,
) -> int:
    """Copy reviewed local examples to the derived dataset without editing them."""
    added = 0
    excluded_labels = excluded_labels or set()
    for label in CLASSES:
        if label in excluded_labels:
            continue
        folder = local_dataset / label
        if not folder.is_dir():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                added += add_image(output, label, path.read_bytes(), path.suffix, counts)
    return added


def prepare(
    archive: Path,
    local_dataset: Path,
    output: Path,
    excluded_local_labels: set[str] | None = None,
) -> dict:
    if not archive.is_file():
        raise FileNotFoundError(f"PBW archive not found: {archive}")
    if output.exists():
        raise FileExistsError(
            f"Refusing to overwrite prepared dataset: {output}. "
            "Choose a new path or remove it manually after review."
        )

    for label in CLASSES:
        (output / label).mkdir(parents=True, exist_ok=False)
    counts: Counter = Counter()
    try:
        public_added, source_counts = add_pbw_archive(archive, output, counts)
        local_added = add_local_images(
            local_dataset,
            output,
            counts,
            excluded_labels=excluded_local_labels,
        )
        missing = [label for label in CLASSES if not counts[label]]
        if missing:
            raise RuntimeError(f"Prepared dataset would be missing: {', '.join(missing)}")
    except Exception:
        shutil.rmtree(output)
        raise

    manifest = {
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Prototype training only; retain demo mode and human verification.",
        "public_source": {
            "title": "Pharmaceutical and Biomedical Waste (PBW)",
            "url": "https://www.kaggle.com/datasets/engineeringubu/pharmaceutical-and-biomedical-waste",
            "license": "CC BY-NC-SA 4.0",
            "archive": str(archive),
            "original_images_added": public_added,
            "source_folder_counts": dict(sorted(source_counts.items())),
            "mapping": [
                {"source_keywords": list(words), "target_label": label}
                for words, label in PBW_MAPPING
            ],
            "excluded": "Roboflow .rf. augmented copies, to prevent split leakage.",
        },
        "local_source": {
            "path": str(local_dataset),
            "images_added": local_added,
            "excluded_labels": sorted(excluded_local_labels or set()),
            "note": "Existing local images were copied; originals are untouched.",
        },
        "class_counts": {label: counts[label] for label in CLASSES},
        "total_images": sum(counts.values()),
    }
    (output / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path,
                        default=ROOT / "sources" / "pharmaceutical-and-biomedical-waste.zip")
    parser.add_argument("--local-dataset", type=Path, default=ROOT / "dataset")
    parser.add_argument("--output", type=Path, default=ROOT / "dataset_pilot_pbw")
    parser.add_argument(
        "--exclude-local-label",
        action="append",
        choices=CLASSES,
        default=[],
        help="Do not copy a local label into the prepared dataset. Repeat as needed.",
    )
    args = parser.parse_args()
    try:
        manifest = prepare(
            args.archive,
            args.local_dataset,
            args.output,
            excluded_local_labels=set(args.exclude_local_label),
        )
    except (FileNotFoundError, FileExistsError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"Dataset preparation failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    print(f"Prepared {manifest['total_images']} images -> {args.output}")
    for label, count in manifest["class_counts"].items():
        print(f"  {label:<22} {count}")
    print(f"Manifest -> {args.output / 'dataset_manifest.json'}")


if __name__ == "__main__":
    main()
