import sys
import click
from .search import search_pdf, search_raw_bytes, search_metadata
from .redact import redact_pdf


@click.group()
def cli():
    """pdfscrub — search and redact sensitive text from PDF files."""


@cli.command("find")
@click.argument("pdf", type=click.Path(exists=True))
@click.argument("terms", nargs=-1, required=True)
@click.option("--raw", is_flag=True, help="Also scan raw PDF byte stream (catches hidden streams and metadata).")
@click.option("--case-sensitive", "-c", is_flag=True, help="Case-sensitive matching.")
def find_cmd(pdf, terms, raw, case_sensitive):
    """Search for TERMS in PDF and report where they appear."""
    terms = list(terms)
    found_anything = False

    # Visible text
    results = search_pdf(pdf, terms, case_sensitive=case_sensitive)
    if results:
        found_anything = True
        click.echo(click.style("Visible text matches:", fg="yellow", bold=True))
        for page_num, hits in sorted(results.items()):
            for term, rect in hits:
                click.echo(f"  page {page_num}: {click.style(repr(term), fg='red')}  @ {rect}")
    else:
        click.echo("No visible text matches found.")

    # Metadata
    meta_hits = search_metadata(pdf, terms, case_sensitive=case_sensitive)
    if meta_hits:
        found_anything = True
        click.echo(click.style("\nMetadata matches:", fg="yellow", bold=True))
        for field, value in meta_hits.items():
            click.echo(f"  {field}: {click.style(value, fg='red')}")
    else:
        click.echo("No metadata matches found.")

    # Raw byte stream
    if raw:
        raw_hits = search_raw_bytes(pdf, terms, case_sensitive=case_sensitive)
        if raw_hits:
            found_anything = True
            click.echo(click.style(f"\nRaw stream matches ({len(raw_hits)} lines):", fg="yellow", bold=True))
            for line in raw_hits[:50]:
                click.echo(f"  {line.strip()}")
            if len(raw_hits) > 50:
                click.echo(f"  ... and {len(raw_hits) - 50} more lines")
        else:
            click.echo("No raw stream matches found.")

    sys.exit(1 if found_anything else 0)


@cli.command("scrub")
@click.argument("pdf", type=click.Path(exists=True))
@click.argument("terms", nargs=-1, required=True)
@click.option("--output", "-o", default=None, help="Output path (default: <input>.redacted.pdf).")
@click.option("--color", default="black", type=click.Choice(["black", "white"]), help="Redaction fill color.")
@click.option("--keep-metadata", is_flag=True, help="Do not scrub metadata fields.")
@click.option("--verify", is_flag=True, default=True, help="Run find after scrubbing to verify clean (default: on).")
@click.option("--no-verify", is_flag=True, help="Skip post-scrub verification.")
def scrub_cmd(pdf, terms, output, color, keep_metadata, verify, no_verify):
    """Redact TERMS from PDF and save to OUTPUT."""
    terms = list(terms)
    if output is None:
        output = pdf.rsplit(".", 1)[0] + ".redacted.pdf"

    fill = (0.0, 0.0, 0.0) if color == "black" else (1.0, 1.0, 1.0)

    click.echo(f"Redacting {len(terms)} term(s) from {click.style(pdf, bold=True)} ...")
    counts = redact_pdf(pdf, output, terms, fill_color=fill, scrub_metadata=not keep_metadata)

    if counts:
        total = sum(counts.values())
        click.echo(click.style(f"  Redacted {total} occurrence(s) across {len(counts)} page(s):", fg="green"))
        for page_num, n in sorted(counts.items()):
            click.echo(f"    page {page_num}: {n} hit(s)")
    else:
        click.echo(click.style("  No visible text matches found — file saved unchanged.", fg="yellow"))

    click.echo(f"Saved to {click.style(output, bold=True)}")

    if not no_verify:
        click.echo("\nVerifying redacted file ...")
        results = search_pdf(output, terms)
        meta_hits = search_metadata(output, terms)
        if results or meta_hits:
            click.echo(click.style("WARNING: terms still found in redacted file!", fg="red", bold=True))
            for page_num, hits in sorted(results.items()):
                for term, rect in hits:
                    click.echo(f"  page {page_num}: {repr(term)} @ {rect}")
            for field, value in meta_hits.items():
                click.echo(f"  metadata {field}: {value}")
            sys.exit(1)
        else:
            click.echo(click.style("  Verification passed — terms not found in output.", fg="green"))
