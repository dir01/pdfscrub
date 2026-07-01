# pdfscrub

Search for and redact sensitive text from PDF files.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- [ocrmypdf](https://ocrmypdf.readthedocs.io/) (optional — needed only for scanned/image PDFs)

## Install

```bash
uv sync
```

## Usage

### Terms file

Create a file with one term per line. Blank lines and lines starting with `#` are ignored:

```
# names
John Doe
John
Doe

# contact
john@example.com
+1 555 123 4567
```

Pass it with `-f` (can be repeated to combine multiple files):

```bash
uv run pdfscrub find -f terms.txt file.pdf
uv run pdfscrub scrub -f terms.txt file.pdf
uv run pdfscrub scrub -f names.txt -f emails.txt file.pdf
```

Inline terms via `-t` and `-f` can be mixed freely:

```bash
uv run pdfscrub scrub -t "extra term" -f terms.txt file.pdf
```

### Search

```bash
uv run pdfscrub find -t "John Doe" -t "john@example.com" file.pdf
uv run pdfscrub find -f terms.txt file.pdf
```

Supports multiple files and shell wildcards:

```bash
uv run pdfscrub find -f terms.txt ./data/*.pdf
```

Also scans raw PDF byte stream and metadata (catches hidden streams):

```bash
uv run pdfscrub find -f terms.txt --raw ./data/*.pdf
```

Exits with code `1` if any term is found, `0` if clean — safe to use in scripts.

### Redact

```bash
uv run pdfscrub scrub -t "John Doe" file.pdf
uv run pdfscrub scrub -f terms.txt file.pdf
```

Supports multiple files and shell wildcards. Each input is saved as `<stem>.redacted.pdf` next to the original:

```bash
uv run pdfscrub scrub -f terms.txt ./data/*.pdf
```

After redacting, automatically re-runs the search to verify the terms are gone.

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `-f, --terms-file PATH` | — | File of terms, one per line. Can be repeated. |
| `-t, --inline-terms TERM` | — | Single term to search/redact. Can be repeated. |
| `-o, --output-dir PATH` | same dir as input | Directory for redacted files |
| `--color black\|white` | `black` | Redaction box fill color |
| `--jitter CHARS` | `1.0` | Randomly widen/narrow each redaction box by up to this many character-widths, so box size doesn't reveal the original text length. Set to `0` to disable. |
| `--keep-metadata` | off | Skip scrubbing metadata fields |
| `--no-verify` | off | Skip post-scrub verification search |

### Scanned PDFs (no text layer)

If a page is a scanned image with no OCR text layer, `pdfscrub` will warn you:

```
WARNING: page(s) 2, 4 appear to be scanned images with no text layer.
Text search cannot find content on these pages — run ocrmypdf first if you need to search them.
```

Run OCR first, then scrub:

```bash
ocrmypdf input.pdf ocr.pdf
uv run pdfscrub scrub -f terms.txt ocr.pdf
```

## Make targets

```bash
make install                              # uv sync
make test                                 # run pytest
make find PDF=file.pdf TERMS="John Doe"
make scrub PDF=file.pdf TERMS="John Doe"
```

## What gets redacted

- Visible text matching the given terms (replaced with a filled rectangle)
- PDF metadata fields (author, title, creator, etc.) containing the terms
- The PDF is saved with garbage collection and stream re-compression to avoid incremental-update leftovers

What is **not** automatically handled:

- Text embedded in scanned images (use `ocrmypdf` first)
- Embedded attachments (`pdfdetach -list file.pdf` to inspect)
