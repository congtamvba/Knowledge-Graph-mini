from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

import pandas as pd
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
DEFAULT_METADATA_PATH = WORKSPACE_ROOT / "kb+hops" / "metadata.csv"
DEFAULT_CONTENT_PATH = WORKSPACE_ROOT / "kb+hops" / "content.csv"
DEFAULT_RELATIONSHIPS_PATH = WORKSPACE_ROOT / "kb+hops" / "relationships.csv"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_normalized.csv"

METADATA_COLUMNS = {
    "id",
    "title",
    "so_ky_hieu",
    "ngay_ban_hanh",
    "loai_van_ban",
    "ngay_co_hieu_luc",
    "nguon_thu_thap",
    "co_quan_ban_hanh",
    "tinh_trang_hieu_luc",
}
CONTENT_COLUMNS = {"id", "content_html"}
RELATIONSHIP_COLUMNS = {
    "doc_id",
    "other_doc_id",
    "relationship",
    "relationship_type",
}

CHAPTER_PATTERN = re.compile(r"^CHƯƠNG\s+[IVXLCDM\d]+(?:\b|[.:-])", re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^MỤC\s+\d+[A-Z]?(?:\b|[.:-])", re.IGNORECASE)
ARTICLE_PATTERN = re.compile(r"^ĐIỀU\s+\d+[A-Z]?(?:\b|[.:-])", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"[\t\f\v ]+")
BLANK_LINES_PATTERN = re.compile(r"\n{3,}")

OUTPUT_COLUMNS = [
    "chunk_id",
    "document_id",
    "text",
    "source_file",
    "title",
    "document_number",
    "document_type",
    "chapter",
    "section",
    "article",
    "effective_date",
    "issue_date",
    "status",
    "issuing_authority",
    "source_url",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a normalized, citation-ready corpus from the source CSV files."
    )
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--content", type=Path, default=DEFAULT_CONTENT_PATH)
    parser.add_argument("--relationships", type=Path, default=DEFAULT_RELATIONSHIPS_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--max-chars",
        type=int,
        default=2000,
        help="Soft maximum chunk length. Structural boundaries take priority.",
    )
    return parser.parse_args()


def read_csv(path: Path, required_columns: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Source file not found: {path}")

    frame = pd.read_csv(path, dtype=str, encoding="utf-8")
    missing_columns = required_columns - set(frame.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"{path.name} is missing required columns: {missing}")
    return frame.fillna("")


def normalize_text(value: str) -> str:
    lines = []
    for raw_line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = WHITESPACE_PATTERN.sub(" ", raw_line).strip()
        if line:
            lines.append(line)
    return BLANK_LINES_PATTERN.sub("\n\n", "\n".join(lines)).strip()


def extract_blocks(content_html: str) -> list[str]:
    soup = BeautifulSoup(content_html, "lxml")
    blocks = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
        if tag.name == "li" and tag.find(["p", "li"]):
            continue
        text = normalize_text(tag.get_text(" ", strip=True))
        if text and (not blocks or text != blocks[-1]):
            blocks.append(text)

    if not blocks:
        fallback = normalize_text(soup.get_text("\n", strip=True))
        if fallback:
            blocks.append(fallback)
    return blocks


def split_long_block(block: str, max_chars: int) -> list[str]:
    if len(block) <= max_chars:
        return [block]

    parts = []
    current_words: list[str] = []
    current_length = 0
    for word in block.split():
        added_length = len(word) + (1 if current_words else 0)
        if current_words and current_length + added_length > max_chars:
            parts.append(" ".join(current_words))
            current_words = [word]
            current_length = len(word)
        else:
            current_words.append(word)
            current_length += added_length
    if current_words:
        parts.append(" ".join(current_words))
    return parts


def heading_value(pattern: re.Pattern[str], block: str) -> str:
    return block if pattern.match(block) else ""


def chunk_blocks(blocks: Iterable[str], max_chars: int) -> list[dict[str, str]]:
    if max_chars < 200:
        raise ValueError("--max-chars must be at least 200")

    chunks: list[dict[str, str]] = []
    current_blocks: list[str] = []
    current_length = 0
    current_context = {"chapter": "", "section": "", "article": ""}
    chunk_context = current_context.copy()

    def flush() -> None:
        nonlocal current_blocks, current_length, chunk_context
        text = normalize_text("\n".join(current_blocks))
        if text:
            chunks.append({"text": text, **chunk_context})
        current_blocks = []
        current_length = 0
        chunk_context = current_context.copy()

    for original_block in blocks:
        chapter = heading_value(CHAPTER_PATTERN, original_block)
        section = heading_value(SECTION_PATTERN, original_block)
        article = heading_value(ARTICLE_PATTERN, original_block)

        if (chapter or section or article) and current_blocks:
            flush()

        if chapter:
            current_context = {"chapter": chapter, "section": "", "article": ""}
        elif section:
            current_context["section"] = section
            current_context["article"] = ""
        elif article:
            current_context["article"] = article
        chunk_context = current_context.copy()

        for block in split_long_block(original_block, max_chars):
            added_length = len(block) + (1 if current_blocks else 0)
            if current_blocks and current_length + added_length > max_chars:
                flush()
            if not current_blocks:
                chunk_context = current_context.copy()
            current_blocks.append(block)
            current_length += len(block) + (1 if len(current_blocks) > 1 else 0)

    flush()
    return chunks


def validate_source_links(
    metadata: pd.DataFrame,
    content: pd.DataFrame,
    relationships: pd.DataFrame,
) -> None:
    metadata_ids = set(metadata["id"])
    content_ids = set(content["id"])
    if metadata_ids != content_ids:
        raise ValueError("metadata.id and content.id do not contain the same documents")

    relationship_ids = set(relationships["doc_id"]) | set(relationships["other_doc_id"])
    orphan_ids = relationship_ids - metadata_ids
    if orphan_ids:
        raise ValueError(f"relationships.csv contains orphan document IDs: {sorted(orphan_ids)}")


def build_corpus(
    metadata: pd.DataFrame,
    content: pd.DataFrame,
    max_chars: int,
    source_file: str,
) -> pd.DataFrame:
    metadata_by_id = metadata.set_index("id", verify_integrity=True)
    if content["id"].duplicated().any():
        raise ValueError("content.csv contains duplicate document IDs")

    records = []
    for content_row in content.itertuples(index=False):
        document_id = content_row.id
        metadata_row = metadata_by_id.loc[document_id]
        chunks = chunk_blocks(extract_blocks(content_row.content_html), max_chars)
        if not chunks:
            raise ValueError(f"Document {document_id} has no retrievable text")

        for chunk_number, chunk in enumerate(chunks, start=1):
            records.append(
                {
                    "chunk_id": f"{document_id}-chunk-{chunk_number:04d}",
                    "document_id": document_id,
                    "text": chunk["text"],
                    "source_file": source_file,
                    "title": metadata_row["title"],
                    "document_number": metadata_row["so_ky_hieu"],
                    "document_type": metadata_row["loai_van_ban"],
                    "chapter": chunk["chapter"],
                    "section": chunk["section"],
                    "article": chunk["article"],
                    "effective_date": metadata_row["ngay_co_hieu_luc"],
                    "issue_date": metadata_row["ngay_ban_hanh"],
                    "status": metadata_row["tinh_trang_hieu_luc"],
                    "issuing_authority": metadata_row["co_quan_ban_hanh"],
                    "source_url": metadata_row["nguon_thu_thap"],
                }
            )
    return pd.DataFrame.from_records(records, columns=OUTPUT_COLUMNS)


def validate_output(corpus: pd.DataFrame, expected_document_count: int) -> None:
    if corpus.empty:
        raise ValueError("Normalized corpus is empty")
    if corpus["chunk_id"].duplicated().any():
        duplicates = corpus.loc[corpus["chunk_id"].duplicated(), "chunk_id"].tolist()
        raise ValueError(f"Duplicate chunk IDs: {duplicates[:5]}")
    if corpus["text"].str.strip().eq("").any():
        raise ValueError("Normalized corpus contains empty chunk text")
    if corpus["document_id"].nunique() != expected_document_count:
        raise ValueError("Normalized corpus does not contain every source document")


def print_summary(corpus: pd.DataFrame) -> None:
    missing_text = int(corpus["text"].str.strip().eq("").sum())
    duplicate_rows = int(corpus.duplicated().sum())
    duplicate_chunk_ids = int(corpus["chunk_id"].duplicated().sum())
    duplicate_texts = int(corpus["text"].duplicated().sum())
    print(f"Total chunks: {len(corpus)}")
    print(f"Documents: {corpus['document_id'].nunique()}")
    print(f"Chunks missing text: {missing_text}")
    print(f"Duplicate rows: {duplicate_rows}")
    print(f"Duplicate chunk IDs: {duplicate_chunk_ids}")
    print(f"Duplicate texts: {duplicate_texts}")
    print("Sample records:")
    sample_columns = ["chunk_id", "document_id", "text", "title", "article"]
    for record in corpus[sample_columns].head(3).to_dict(orient="records"):
        record["text"] = record["text"][:240]
        print(record)


def main() -> None:
    args = parse_args()
    metadata = read_csv(args.metadata.resolve(), METADATA_COLUMNS)
    content = read_csv(args.content.resolve(), CONTENT_COLUMNS)
    relationships = read_csv(args.relationships.resolve(), RELATIONSHIP_COLUMNS)
    validate_source_links(metadata, content, relationships)

    corpus = build_corpus(
        metadata,
        content,
        args.max_chars,
        source_file=args.content.name,
    )
    validate_output(corpus, expected_document_count=len(content))

    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    corpus.to_csv(output_path, index=False, encoding="utf-8")
    print(f"Output: {output_path}")
    print_summary(corpus)


if __name__ == "__main__":
    main()