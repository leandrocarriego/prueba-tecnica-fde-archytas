#!/usr/bin/env python
"""Build the package that goes to the client.

The client never receives the repository. They receive what they are meant to
read and sign: the brief, each feature's `spec.md`, and the business-level
diagrams — as PDF, plus every diagram as a standalone SVG so it can be zoomed
without pixelating.

**What is client-facing is an allowlist, not everything that is not excluded.**
`plan.md`, `tasks.md`, `research.md`, `data-model.md`, `contracts/`,
`checklists/` and `quickstart.md` are internal: they carry stack decisions,
endpoints and file paths. Shipping one of them by accident is the failure this
script is written to prevent, so anything not named here is left out — a file
added tomorrow is excluded by default, not included by default.

Everything runs on tools the project already has: `markdown-it-py` (via rich),
Playwright's Chromium for the PDF, and mermaid-cli for the diagrams.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from markdown_it import MarkdownIt
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "docs" / "specs"
ARCHIVE = SPECS / "archive"
BRIEF = ROOT / "docs" / "PROJECT_BRIEF.md"
OUT = ROOT / "dist" / "cliente"

# The only documents a client ever receives. Adding to this list is a decision
# about what the client is asked to read, not a convenience.
CLIENT_FACING_DOCS = ("spec.md",)

# `sequence-*.mmd` are internal, technical and in English (DIAGRAMS.md): they
# describe endpoints, not business flows, and never reach the client.
CLIENT_FACING_DIAGRAMS = ("flujo-", "estados-")

STYLESHEET = """
@page { size: A4; margin: 20mm 18mm 22mm 18mm; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 10.5pt; line-height: 1.55; color: #1a1a1a; margin: 0;
}
h1 { font-size: 21pt; margin: 0 0 .2em; letter-spacing: -.01em; }
h2 { font-size: 14pt; margin: 1.6em 0 .5em; padding-bottom: .25em;
     border-bottom: 1px solid #d8d8d8; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin: 1.2em 0 .4em; page-break-after: avoid; }
h2, h3, h4 { page-break-inside: avoid; }
p, li { orphans: 3; widows: 3; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 9.5pt;
        page-break-inside: avoid; }
th, td { border: 1px solid #d8d8d8; padding: .45em .6em; text-align: left; vertical-align: top; }
th { background: #f4f4f5; font-weight: 600; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .9em;
       background: #f4f4f5; padding: .1em .35em; border-radius: 3px; }
pre { background: #f4f4f5; padding: .8em 1em; border-radius: 5px; overflow-x: auto;
      page-break-inside: avoid; }
pre code { background: none; padding: 0; }
blockquote { margin: 1em 0; padding: .1em 1em; border-left: 3px solid #c9c9c9; color: #444; }
hr { border: none; border-top: 1px solid #d8d8d8; margin: 2em 0; }
a { color: #1a1a1a; text-decoration: underline; }

.portada { page-break-after: always; padding-top: 28vh; }
.portada .cliente { font-size: 12pt; color: #555; margin-bottom: 2.5em; }
.portada .titulo { font-size: 27pt; font-weight: 650; line-height: 1.15; margin-bottom: .4em; }
.portada .sub { font-size: 12pt; color: #555; }
.portada .pie { margin-top: 3.5em; font-size: 9.5pt; color: #777; }

.chapa { display: inline-block; margin-top: 2em; padding: .3em .9em; border-radius: 999px;
         font-size: 9.5pt; font-weight: 600; letter-spacing: .01em; }
.chapa.entregada { background: #e6f4ea; color: #1e6b32; border: 1px solid #b7dfc4; }
.chapa.en-curso  { background: #fdf3e0; color: #8a5a06; border: 1px solid #f0d9a8; }
.chapa.borrador  { background: #f1f1f2; color: #55565a; border: 1px solid #d5d5d8; }

.aviso { margin-top: 1.4em; padding: .8em 1em; border-radius: 5px; font-size: 10pt;
         line-height: 1.5; max-width: 46em; }
.aviso.entregada { background: #f3faf5; border-left: 3px solid #2f7d32; }
.aviso.en-curso  { background: #fdf8ef; border-left: 3px solid #b7791f; }
.aviso.borrador  { background: #f6f6f7; border-left: 3px solid #8a8a8e; }

/* En el documento único cada sección arranca en hoja nueva. */
.documento { page-break-before: always; }
.documento > h1:first-child { margin-top: 0; }

.indice { page-break-after: always; }
.indice h2 { border-bottom: 1px solid #d8d8d8; }
.indice ol { list-style: none; padding: 0; margin: 1.5em 0 0; }
.indice li { display: flex; align-items: baseline; gap: .8em; padding: .55em 0;
             border-bottom: 1px solid #eee; }
.indice .nombre { flex: 1; }
.indice .num { color: #999; font-size: 9pt; min-width: 3.2em; }

.separador { page-break-before: always; padding-top: 30vh; text-align: center; }
.separador .titulo { font-size: 19pt; font-weight: 650; margin-bottom: .6em; }
.separador p { color: #555; max-width: 30em; margin: 0 auto; }

.diagrama { page-break-before: always; }
.diagrama h2 { border: none; }
.diagrama svg {
  /* A4 útil = 297mm - 42mm de márgenes. Reservamos el encabezado y la nota:
     sin este tope, un diagrama alto se parte en dos páginas. */
  max-width: 100%; max-height: 205mm; width: auto; height: auto;
  display: block; margin: 1.5em auto;
}
.nota { font-size: 9pt; color: #777; margin-top: .3em; }

li.tarea { list-style: none; margin-left: -1.2em; }
li.tarea::before { content: "☐"; margin-right: .5em; color: #666; }
li.tarea.hecha::before { content: "☑"; color: #2f7d32; }
"""


@dataclass(frozen=True)
class State:
    """How far along a feature is, as the client should read it."""

    label: str
    css: str
    notice: str


# A delivered feature is not the same as an approved one, and neither is the
# same as a draft. Sending all three with the same cover invites the client to
# read a draft as a commitment, or a delivered feature as pending work.
DELIVERED = State(
    "Implementada",
    "entregada",
    "Funcionalidad <strong>entregada</strong>. Este documento describe lo que se acordó en su "
    "momento, no necesariamente cómo funciona el sistema hoy.",
)
IN_PROGRESS = State(
    "En desarrollo",
    "en-curso",
    "Alcance <strong>aprobado</strong>. La funcionalidad está en construcción: lo que sigue "
    "describe lo que se va a construir, no lo que ya se puede usar.",
)
DRAFT = State(
    "Borrador",
    "borrador",
    "Documento <strong>en revisión, todavía sin aprobar</strong>. Su alcance puede cambiar y no "
    "constituye un compromiso.",
)


@dataclass
class Diagram:
    """One `.mmd` and the SVG rendered from it."""

    source: Path
    svg: str = ""
    title: str = ""
    # mermaid renders the frontmatter title inside the SVG. When it does, the
    # section must not print it again above the drawing.
    title_in_svg: bool = False

    @property
    def name(self) -> str:
        return self.source.stem


@dataclass
class Document:
    """One client-facing document and the diagrams that go with it."""

    title: str
    markdown: Path
    slug: str
    state: State | None = None
    approved_on: str = ""
    subdir: str = ""
    diagrams: list[Diagram] = field(default_factory=list)


def document_title(markdown: Path, fallback: str) -> str:
    """Return the document's own `# ` heading, or the folder name if it has none.

    The cover of a document the client signs should carry its title, not the
    slug of a directory.
    """
    for line in markdown.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def read_state(markdown: Path, archived: bool) -> tuple[State, str]:
    """Return the feature's state and, if it has one, its approval date.

    Location wins over text: a spec in `archive/` was delivered, whatever its
    header still says. Inside the active tree the header decides, and anything
    that is not explicitly approved is treated as a draft — the safe direction
    to be wrong in, since it under-promises rather than over-promises.
    """
    text = markdown.read_text(encoding="utf-8")
    date = ""
    if match := re.search(r"^\s*[*_]*Fecha de aprobación[*_]*:\s*(.+?)\s*$", text, re.M):
        date = match.group(1).strip("*_ ")

    if archived:
        return DELIVERED, date

    header = re.search(r"^\s*[*_]*Estado[*_]*:\s*(.+?)\s*$", text, re.M)
    declared = header.group(1).strip("*_ ").lower() if header else ""
    return (IN_PROGRESS if declared.startswith("aprobad") else DRAFT), date


def badge_html(document: Document, *, with_date: bool = True) -> str:
    """The state pill. Same markup on a cover, an index row or a section head."""
    if not document.state:
        return ""
    date = (
        f" · aprobada el {html.escape(document.approved_on)}"
        if with_date and document.approved_on
        else ""
    )
    return (
        f'<span class="chapa {document.state.css}">{html.escape(document.state.label)}{date}</span>'
    )


def strip_author_notes(markdown: str) -> str:
    """Drop HTML comments before rendering.

    The templates use `<!-- ... -->` to guide whoever writes the document. The
    renderer runs with `html=False`, which escapes rather than hides them, so
    without this a note to the author would print verbatim in the PDF the
    client signs.
    """
    return re.sub(r"<!--.*?-->", "", markdown, flags=re.S)


def as_task_list(rendered: str) -> str:
    """Turn `- [ ]` items into real checkboxes.

    CommonMark has no task lists, so acceptance criteria — which every spec
    writes as a checklist — would otherwise print a literal "[ ]".
    """
    rendered = re.sub(r"<li>\s*\[[xX]\]\s*", '<li class="tarea hecha">', rendered)
    rendered = re.sub(r"<li>\s*\[ \]\s*", '<li class="tarea">', rendered)
    return rendered


def fail(message: str) -> None:
    print(f"export-client: {message}", file=sys.stderr)
    raise SystemExit(1)


def mmdc_command() -> list[str]:
    """Resolve mermaid-cli the same way the diagram scripts do."""
    if env := os.environ.get("MMDC"):
        return [env]
    if found := shutil.which("mmdc"):
        return [found]
    return ["npx", "-y", "@mermaid-js/mermaid-cli"]


def render_svg(diagram: Diagram, puppeteer_config: Path) -> None:
    """Render one `.mmd` to SVG. Vector, so the client can zoom without limit."""
    out = diagram.source.with_suffix(".svg")
    command = [
        *mmdc_command(),
        "-i",
        str(diagram.source),
        "-o",
        str(out),
        "-b",
        "white",
        "-p",
        str(puppeteer_config),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not out.exists():
        fail(f"no pude renderizar {diagram.source.name}:\n{result.stderr.strip()}")

    diagram.svg = out.read_text(encoding="utf-8")
    match = re.search(r"^title:\s*(.+)$", diagram.source.read_text(encoding="utf-8"), re.M)
    if match:
        diagram.title = match.group(1).strip()
        diagram.title_in_svg = True
    else:
        diagram.title = diagram.name.replace("-", " ").capitalize()
    out.unlink()


def strip_svg_size(svg: str) -> str:
    """Drop the fixed width so the diagram scales to the page.

    mermaid-cli emits an explicit `width`/`style="max-width"`, which in print
    either overflows the margin or leaves the page half empty.
    """
    svg = re.sub(r'\swidth="[^"]*"', "", svg, count=1)
    svg = re.sub(r'\sheight="[^"]*"', "", svg, count=1)
    svg = re.sub(r'style="[^"]*max-width:[^"]*"', "", svg, count=1)
    return svg


def collect_diagrams(feature_dir: Path) -> list[Diagram]:
    """Return the client-facing diagrams of a feature, in reading order."""
    folder = feature_dir / "diagrams"
    if not folder.is_dir():
        return []
    found = [
        Diagram(source=path)
        for path in sorted(folder.glob("*.mmd"))
        if path.name.startswith(CLIENT_FACING_DIAGRAMS)
    ]
    # The end-to-end flow opens the section; the rest follow alphabetically.
    found.sort(key=lambda d: (not d.name.startswith("flujo-general"), d.name))
    return found


def discover(only: str | None) -> list[Document]:
    """Return every document that is meant to reach the client."""
    documents: list[Document] = []

    if BRIEF.exists() and not only:
        documents.append(
            Document(
                title=document_title(BRIEF, "Definición del proyecto"),
                markdown=BRIEF,
                slug="brief",
            )
        )

    for archived, tree, subdir in ((False, SPECS, ""), (True, ARCHIVE, "entregadas")):
        if not tree.is_dir():
            continue
        for feature in sorted(p for p in tree.iterdir() if p.is_dir() and p.name != "archive"):
            if only and feature.name != only:
                continue
            for name in CLIENT_FACING_DOCS:
                source = feature / name
                if not source.exists():
                    continue
                state, approved_on = read_state(source, archived)
                documents.append(
                    Document(
                        title=document_title(source, feature.name),
                        markdown=source,
                        slug=feature.name,
                        state=state,
                        approved_on=approved_on,
                        subdir=subdir,
                        diagrams=collect_diagrams(feature),
                    )
                )
    return documents


def diagram_section(diagram: Diagram) -> str:
    """One diagram on its own page, naming the SVG that accompanies it."""
    heading = "" if diagram.title_in_svg else f"<h2>{html.escape(diagram.title)}</h2>"
    return (
        '<section class="diagrama">'
        f"{heading}"
        f"{strip_svg_size(diagram.svg)}"
        f'<p class="nota">El archivo <code>{html.escape(diagram.name)}.svg</code> '
        "acompaña a este PDF: se abre en cualquier navegador y permite ampliar "
        "sin que se pixele.</p>"
        "</section>"
    )


def build_html(document: Document, body: str) -> str:
    """Wrap the rendered Markdown in a cover page and the diagram section."""
    diagrams = "".join(diagram_section(d) for d in document.diagrams)

    badge = notice = ""
    if document.state:
        badge = f"<div>{badge_html(document)}</div>"
        notice = f'<div class="aviso {document.state.css}">{document.state.notice}</div>'

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>{html.escape(document.title)}</title><style>{STYLESHEET}</style></head><body>
<div class="portada">
  <div class="cliente">Ferretería Industrial Cordillera SRL</div>
  <div class="titulo">{html.escape(document.title)}</div>
  <div class="sub">Plataforma Cordillera · {html.escape(document.slug)}</div>
  {badge}
  {notice}
  <div class="pie">Documento para revisión y aprobación del cliente.<br>
  Generado desde <code>{html.escape(str(document.markdown.relative_to(ROOT)))}</code>.</div>
</div>
{as_task_list(body)}
{diagrams}
</body></html>"""


def with_state_after_title(body: str, block: str) -> str:
    """Insert the state block right below the document's own title.

    Above it, the reader meets a badge before knowing what it qualifies.
    """
    head, sep, tail = body.partition("</h1>")
    return f"{head}{sep}{block}{tail}" if sep else f"{block}{body}"


def build_combined_html(documents: list[Document], rendered: dict[Path, str]) -> str:
    """One document with everything, in the order the client should meet it.

    Delivered features go last, behind a divider. They are history, they only
    accumulate, and a client opening the package wants to see what is being
    built now — not to scroll past two years of finished work to reach it.
    """
    pending = [d for d in documents if d.state is not DELIVERED]
    delivered = [d for d in documents if d.state is DELIVERED]

    def index_rows(items: list[Document], start: int) -> str:
        return "".join(
            f'<li><span class="num">{position:02d}</span>'
            f'<span class="nombre">{html.escape(document.title)}</span>'
            f"{badge_html(document, with_date=False)}</li>"
            for position, document in enumerate(items, start=start)
        )

    def sections(items: list[Document]) -> str:
        out = ""
        for document in items:
            notice = (
                f'<div class="aviso {document.state.css}">{document.state.notice}</div>'
                if document.state
                else ""
            )
            diagrams = "".join(diagram_section(d) for d in document.diagrams)
            body = with_state_after_title(
                as_task_list(rendered[document.markdown]),
                badge_html(document) + notice,
            )
            out += f'<section class="documento">{body}{diagrams}</section>'
        return out

    divider = ""
    if delivered:
        cuantas = (
            "La especificación que sigue corresponde"
            if len(delivered) == 1
            else f"Las {len(delivered)} especificaciones que siguen corresponden"
        )
        divider = (
            '<section class="separador"><div class="titulo">Funcionalidad ya entregada</div>'
            f"<p>{cuantas} a funcionalidad ya implementada y en uso. Se incluyen como "
            "referencia de lo que se acordó en su momento; no describen trabajo "
            "pendiente.</p></section>"
        )

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>Plataforma Cordillera</title><style>{STYLESHEET}</style></head><body>
<div class="portada">
  <div class="cliente">Ferretería Industrial Cordillera SRL</div>
  <div class="titulo">Plataforma Cordillera</div>
  <div class="sub">Documentación del proyecto</div>
  <div class="pie">Estado del proyecto y alcance acordado.<br>
  Cada especificación se firma por separado, en su propio documento.</div>
</div>
<section class="indice"><h2>Contenido</h2>
  <ol>{index_rows(pending, 1)}{index_rows(delivered, len(pending) + 1)}</ol>
</section>
{sections(pending)}
{divider}
{sections(delivered)}
</body></html>"""


def footer(label: str) -> str:
    """The running footer: what this is on the left, the page number on the right."""
    return (
        '<div style="width:100%;font-size:8pt;color:#888;padding:0 18mm;'
        'font-family:-apple-system,sans-serif;display:flex;justify-content:space-between;">'
        f"<span>{html.escape(label)}</span>"
        '<span class="pageNumber"></span></div>'
    )


def export(documents: list[Document], puppeteer_config: Path) -> list[Path]:
    """Produce both deliverables.

    One PDF per spec, because that is the unit the client signs: a signature
    belongs to a self-contained document, not to page 47 of a dossier. And one
    combined PDF, because someone opening the package wants to see the state of
    the project in a single file.
    """
    md = MarkdownIt("commonmark", {"html": False}).enable("table").enable("strikethrough")
    written: list[Path] = []
    rendered: dict[Path, str] = {}

    def to_pdf(path: Path, label: str) -> None:
        page.pdf(
            path=str(path),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=footer(label),
        )
        written.append(path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        for document in documents:
            for diagram in document.diagrams:
                render_svg(diagram, puppeteer_config)

            rendered[document.markdown] = md.render(
                strip_author_notes(document.markdown.read_text(encoding="utf-8"))
            )

            target = (
                OUT / document.subdir / document.slug if document.subdir else OUT / document.slug
            )
            target.mkdir(parents=True, exist_ok=True)

            page.set_content(
                build_html(document, rendered[document.markdown]), wait_until="networkidle"
            )
            state = f" — {document.state.label}" if document.state else ""
            to_pdf(target / f"{document.markdown.stem}.pdf", f"{document.title}{state}")

            if document.diagrams:
                svg_dir = target / "diagramas"
                svg_dir.mkdir(exist_ok=True)
                for diagram in document.diagrams:
                    path = svg_dir / f"{diagram.name}.svg"
                    path.write_text(diagram.svg, encoding="utf-8")
                    written.append(path)

        if len(documents) > 1:
            OUT.mkdir(parents=True, exist_ok=True)
            page.set_content(build_combined_html(documents, rendered), wait_until="networkidle")
            to_pdf(OUT / "Plataforma-Cordillera.pdf", "Plataforma Cordillera")

        browser.close()
    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exporta a PDF la documentación cara al cliente, con sus diagramas en SVG."
    )
    parser.add_argument(
        "feature",
        nargs="?",
        help="Acotar a una feature (por ejemplo 001-portal-extraction). Por defecto, todas.",
    )
    args = parser.parse_args()

    documents = discover(args.feature)
    if not documents:
        target = args.feature or "docs/"
        fail(f"no encontré documentación cara al cliente en {target}")

    written = export(documents, ROOT / "scripts" / "diagrams" / "puppeteer-config.json")

    print(f"export-client: {len(documents)} documento(s) → dist/cliente/")
    for path in written:
        print(f"  {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
