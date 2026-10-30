"""Split Markdown pages into sections (one per `##` heading), and long sections into parts.

Every chunk keeps a stable `section_id` such as `freshness#common-causes-of-a-failure`,
which the evaluation set uses to say which section answers a question.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

MAX_WORDS = 220          # all-MiniLM-L6-v2 reads ~256 tokens; keep chunks under that
SKIP_FILES = {"README.md"}


@dataclass(frozen=True)
class Chunk:
    chunk_id: str        # unique: section_id, plus "~2", "~3" for parts of a long section
    section_id: str      # "<page>#<heading-slug>"
    source: str          # file name, e.g. "freshness.md"
    title: str           # page title (the "# " heading)
    heading: str         # section heading (the "## " heading)
    content: str         # section body

    @property
    def text(self) -> str:
        """What gets embedded and shown: page title and heading give the body its context."""
        return f"{self.title}: {self.heading}\n\n{self.content}"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def _split_long(body: str, max_words: int) -> list[str]:
    """Split on paragraphs, carrying the previous paragraph over for context."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    parts: list[list[str]] = [[]]
    for para in paragraphs:
        current = parts[-1]
        if current and sum(len(p.split()) for p in current) + len(para.split()) > max_words:
            parts.append([current[-1], para])  # one paragraph of overlap
        else:
            current.append(para)
    return ["\n\n".join(p) for p in parts]


def chunk_markdown(source: str, markdown: str, max_words: int = MAX_WORDS) -> list[Chunk]:
    stem = source.removesuffix(".md")
    title_match = re.search(r"^# (.+)$", markdown, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else stem.replace("-", " ").title()

    # Split on level-2 headings, but not on "## " inside fenced code blocks.
    sections: list[tuple[str, list[str]]] = [("Overview", [])]
    in_code = False
    for line in markdown.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif not in_code and line.startswith("# ") and line[2:].strip() == title:
            continue
        else:
            sections[-1][1].append(line)

    chunks: list[Chunk] = []
    seen: dict[str, int] = {}
    for heading, lines in sections:
        body = "\n".join(lines).strip()
        if not body:
            continue
        slug = slugify(heading)
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"
        section_id = f"{stem}#{slug}"
        parts = _split_long(body, max_words) if len(body.split()) > max_words else [body]
        for i, part in enumerate(parts, start=1):
            chunk_id = section_id if len(parts) == 1 else f"{section_id}~{i}"
            chunks.append(Chunk(chunk_id, section_id, source, title, heading, part))
    return chunks


def load_docs(docs_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(docs_dir.glob("*.md")):
        if path.name in SKIP_FILES:
            continue
        chunks.extend(chunk_markdown(path.name, path.read_text(encoding="utf-8")))
    if not chunks:
        raise FileNotFoundError(f"No Markdown pages found in {docs_dir}")
    return chunks
