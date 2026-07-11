"""
Generate an ER diagram of the Saaransh ORM models.

Tries to render via (in priority order):

  1. `graphviz` Python package + system `dot` binary
       -> backend/docs/erd.png  (and .dot source)
  2. Mermaid `erDiagram` text
       -> backend/docs/erd.mmd  (renders on GitHub, in the wiki, in any
                                Mermaid Live Editor)

Run with:
    python -m scripts.generate_erd
"""
from __future__ import annotations

import sys
from pathlib import Path

# --- ensure the project root is on sys.path --------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.session import Base  # noqa: E402
from backend import models  # noqa: E402, F401  (register models on Base.metadata)
from backend.config.logging import configure_logging, get_logger  # noqa: E402

log = get_logger(__name__)

OUT_DIR = PROJECT_ROOT / "backend" / "docs"


# ---- helpers ---------------------------------------------------------------
def _truncate(label: str, n: int = 24) -> str:
    return label if len(label) <= n else label[: n - 1] + "…"


def _safe_comment(name: str) -> str:
    """Mermaid doesn't allow some chars in identifiers — sanitise them."""
    return name.replace(" ", "_").replace("-", "_")


def _format_pk_fk(table) -> list[str]:
    lines = []
    for col in table.columns:
        flags = []
        if col.primary_key:
            flags.append("PK")
        if col.foreign_keys:
            flags.append("FK")
        flag_str = f" [{','.join(flags)}]" if flags else ""
        line = f"      {_safe_comment(col.name)} {col.type!s}{flag_str}"
        if col.nullable:
            line += " \"nullable\""
        lines.append(line)
    return lines


# ---- graphviz path (preferred) ---------------------------------------------
def _try_graphviz() -> Path | None:
    try:
        import graphviz  # type: ignore
    except ImportError:
        log.info("graphviz python package not installed; skipping PNG render")
        return None

    # Check for the `dot` binary
    from shutil import which
    if which("dot") is None:
        log.info("`dot` binary not on PATH; skipping PNG render")
        return None

    dot = graphviz.Digraph("saaransh_erd", format="png")
    dot.attr(rankdir="LR", splines="true", overlap="false")
    dot.attr("node", shape="record", style="filled", fillcolor="#f6f8fa",
             fontname="Helvetica", fontsize="10")
    dot.attr("edge", color="#586069", arrowsize="0.6")

    for name in sorted(Base.metadata.tables):
        table = Base.metadata.tables[name]
        label = "|".join(
            ["<head> " + name] + [c.name + " : " + str(c.type) for c in table.columns]
        )
        dot.node(name, label=label)

    for name, table in Base.metadata.tables.items():
        for fk in table.foreign_keys:
            tgt = fk.column.table.name
            dot.edge(name, tgt, label=_truncate(fk.parent.name + " -> " + fk.column.name))

    out_path = OUT_DIR / "erd"
    dot.render(str(out_path), cleanup=True)
    return OUT_DIR / "erd.png"


# ---- mermaid path (always works) -------------------------------------------
def _write_mermaid() -> Path:
    lines = ["```mermaid", "erDiagram"]
    for name in sorted(Base.metadata.tables):
        table = Base.metadata.tables[name]
        lines.append(f"    {_safe_comment(name)} {{")
        for line in _format_pk_fk(table):
            lines.append(line)
        lines.append("    }")
        lines.append("")

    for name, table in Base.metadata.tables.items():
        for fk in table.foreign_keys:
            tgt = _safe_comment(fk.column.table.name)
            src = _safe_comment(name)
            ident = _truncate(
                fk.parent.name + "_" + (fk.column.name or ""), n=40
            )
            lines.append(f'    {src} ||--o| {tgt} : "{ident}"')
    lines.append("```")
    out = OUT_DIR / "erd.mmd"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# ---- main ------------------------------------------------------------------
def main() -> int:
    configure_logging()
    log.info("Generating ER diagram from %d declared models", len(Base.metadata.tables))

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    png = _try_graphviz()
    if png and png.exists():
        log.info("Wrote PNG: %s", png)
    else:
        log.info("Skipped PNG render (graphviz/dot not available)")

    mmd = _write_mermaid()
    log.info("Wrote Mermaid: %s", mmd)
    log.info("Open the .mmd file in https://mermaid.live to view.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
