"""Dataset cleaning pass.

Run before training. Removes files that would crash the loader or poison
the split: unreadable images, duplicates (by content hash), and images
below a minimum resolution.

    python -m ml.preprocessing.clean --apply
"""

import argparse
import hashlib
from collections import defaultdict
from pathlib import Path

from PIL import Image

VALID_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MIN_SIDE = 64


def scan(dataset_dir: Path):
    broken, small, duplicates = [], [], []
    seen = defaultdict(list)

    for path in sorted(dataset_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in VALID_SUFFIXES:
            continue
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                width, height = image.size
        except Exception:  # noqa: BLE001
            broken.append(path)
            continue

        if min(width, height) < MIN_SIDE:
            small.append(path)
            continue

        digest = hashlib.md5(path.read_bytes()).hexdigest()
        seen[digest].append(path)

    for paths in seen.values():
        duplicates.extend(paths[1:])

    return broken, small, duplicates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="ml/dataset")
    parser.add_argument("--apply", action="store_true",
                        help="Delete the flagged files (default is a dry run).")
    args = parser.parse_args()

    broken, small, duplicates = scan(Path(args.dataset))
    print(f"Unreadable: {len(broken)}")
    print(f"Too small (<{MIN_SIDE}px): {len(small)}")
    print(f"Duplicates: {len(duplicates)}")

    if not args.apply:
        print("\nDry run. Re-run with --apply to delete these files.")
        return

    for path in broken + small + duplicates:
        path.unlink()
    print(f"\nDeleted {len(broken) + len(small) + len(duplicates)} files.")


if __name__ == "__main__":
    main()
