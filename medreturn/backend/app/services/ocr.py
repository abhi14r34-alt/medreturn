"""Best-effort OCR and text matching for printed item names and expiry dates.

OCR is optional. When Tesseract is not installed or unreadable, callers receive an
empty result and image-based classification takes over seamlessly.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

from PIL import Image, ImageOps


@dataclass
class OcrResult:
    text: str = ""
    expiry_date: str | None = None
    available: bool = False


_EXPIRY_PATTERNS = (
    re.compile(
        r"\b(?:EXP(?:IRY)?|EXP\.?|B\.?NO\.?|USE BEFORE|BEST BEFORE)\s*[:\-]?\s*([A-Za-z]{3,9}[\s\-.]\d{2,4}|\d{1,2}[\/\-.]\d{2,4}|\d{2,4}[\/\-.]\d{1,2})",
        re.I,
    ),
    re.compile(r"\b(\d{1,2}[\/\-.]\d{2,4})\b"),
    re.compile(r"\b([A-Z]{3,4}\s*\d{2,4})\b", re.I),
)

def extract_expiry(text: str) -> str | None:
    if not text:
        return None
    for pattern in _EXPIRY_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def read_image(data: bytes) -> OcrResult:
    try:
        import pytesseract

        image = Image.open(io.BytesIO(data)).convert("RGB")
        image = ImageOps.exif_transpose(image)
        image.thumbnail((1600, 1600))
        image = ImageOps.autocontrast(ImageOps.grayscale(image))
        text = pytesseract.image_to_string(image, config="--psm 6").strip()
        return OcrResult(text=text[:2000], expiry_date=extract_expiry(text), available=True)
    except Exception:
        return OcrResult(text="", expiry_date=None, available=False)


def extract_item_name(text: str) -> str | None:
    """Return a useful printed product/item line without forcing a category.

    This intentionally does not keep a brand-name or packaging keyword list.
    The OCR text is evidence for an operator, while the trained model's own
    labels remain the visual classification result.
    """
    if not text:
        return None

    ignored = re.compile(r"\b(?:exp|expiry|mfg|batch|lot|mrp|price|use before|best before)\b", re.I)
    candidates = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" -:|,.")
        letters = sum(char.isalpha() for char in line)
        if letters < 3 or ignored.search(line):
            continue
        # Product lines usually contain words and perhaps a strength such as
        # "650 mg". Keep them short enough for logs and email notifications.
        candidates.append(line[:120])

    return max(candidates, key=lambda value: sum(char.isalpha() for char in value), default=None)
