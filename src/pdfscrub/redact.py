import random
import re

import fitz

from .search import term_variants


def redact_pdf(
    input_path: str,
    output_path: str,
    terms: list[str],
    fill_color: tuple[float, float, float] = (0.0, 0.0, 0.0),
    scrub_metadata: bool = True,
    jitter: float = 1.0,
) -> dict[int, int]:
    """
    Redact all occurrences of each term from the PDF and save to output_path.
    Returns a dict mapping 1-based page numbers to the number of redactions made.

    jitter: max random width adjustment in character-widths (default 1.0).
            Each redaction box is widened or narrowed by a random amount in
            [-jitter * char_width, +jitter * char_width] so box size doesn't
            reveal the exact length of the redacted text. Set to 0 to disable.
    """
    doc = fitz.open(input_path)
    redaction_counts: dict[int, int] = {}

    for page in doc:
        count = 0
        for term in terms:
            quads = page.search_for(term, quads=True)
            for quad in quads:
                rect = _jitter_rect(quad.rect, term, jitter)
                page.add_redact_annot(rect, fill=fill_color)
                count += 1

        if count:
            page.apply_redactions(
                images=fitz.PDF_REDACT_IMAGE_PIXELS,
                graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
                text=fitz.PDF_REDACT_TEXT_REMOVE,
            )
            redaction_counts[page.number + 1] = count

    if scrub_metadata:
        _scrub_metadata(doc, terms)

    doc.save(output_path, garbage=4, deflate=True, clean=True)
    doc.close()

    return redaction_counts


def _jitter_rect(rect: fitz.Rect, term: str, jitter: float) -> fitz.Rect:
    if jitter == 0 or not term:
        return rect
    char_width = rect.width / len(term)
    max_delta = jitter * char_width
    delta = random.uniform(-max_delta, max_delta)
    # Shift the right edge; leave the left edge fixed so the box always
    # covers the original text regardless of direction.
    new_x1 = max(rect.x0 + char_width, rect.x1 + delta)
    return fitz.Rect(rect.x0, rect.y0, new_x1, rect.y1)


def _scrub_metadata(doc: fitz.Document, terms: list[str]) -> None:
    meta = doc.metadata or {}
    cleaned = {}
    for field, value in meta.items():
        if not value:
            cleaned[field] = value
            continue
        new_value = value
        for term in terms:
            for variant in term_variants(term):
                new_value = re.sub(
                    re.escape(variant), "[REDACTED]", new_value, flags=re.IGNORECASE
                )
        cleaned[field] = new_value
    doc.set_metadata(cleaned)
