#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Convert section-level JSONL chunks into RAGFlow-friendly evidence Markdown.

Input JSONL line example:
{
  "section_id": "9.4.1",
  "title": "副翼控制功能概述",
  "path": ["系统运行描述", "副翼控制", "副翼控制功能概述"],
  "content": "......"
}

Outputs:
1) One combined Markdown file: ragflow_evidence/evidence_all.md
2) Or one Markdown per chunk: ragflow_evidence/chunks/<chunk_id_sanitized>.md

ChunkID strategy (stable):
chunk_id = f"{doc_id}:{section_id}"
If you later add sub-chunks, extend to f"{doc_id}:{section_id}:p003" etc.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def safe_str(x: Any) -> str:
    return x if isinstance(x, str) else ""


def safe_list_str(x: Any) -> list[str]:
    if isinstance(x, list):
        return [safe_str(i) for i in x if isinstance(i, str)]
    return []


def sanitize_filename(name: str, max_len: int = 120) -> str:
    # Windows-friendly filename sanitize
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > max_len:
        name = name[:max_len].rstrip()
    return name or "untitled"


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    yield obj
                else:
                    print(f"[WARN] Line {idx}: not a JSON object, skipped.")
            except json.JSONDecodeError as e:
                print(f"[WARN] Line {idx}: JSON decode error: {e}. Skipped.")


def build_chunk_id(doc_id: str, section_id: str) -> str:
    # Stable, deterministic
    doc_id = safe_str(doc_id).strip() or "DOC"
    section_id = safe_str(section_id).strip() or "UNKNOWN"
    return f"{doc_id}:{section_id}"


def render_markdown(
    doc_id: str,
    section_id: str,
    title: str,
    path_list: list[str],
    chunk_id: str,
    content: str,
) -> str:
    # Make it friendly for both embedding and human debugging
    path_str = " > ".join([p for p in path_list if p]) if path_list else ""
    title_line = title.strip() if title.strip() else (path_list[-1].strip() if path_list else section_id)

    md = []
    md.append(f"# {title_line}")
    md.append("")
    md.append(f"- Doc: {doc_id}")
    md.append(f"- Section: {section_id}")
    if path_str:
        md.append(f"- Path: {path_str}")
    md.append(f"- ChunkID: {chunk_id}")
    md.append("")
    md.append("正文：")
    md.append("")
    md.append(content.rstrip() if isinstance(content, str) else "")
    md.append("")
    return "\n".join(md)


def main() -> None:
    parser = argparse.ArgumentParser(description="JSONL -> RAGFlow evidence Markdown converter")
    parser.add_argument("--in", dest="in_path", default="data/full.jsonl", help="Input JSONL path")
    parser.add_argument("--out", dest="out_dir", default="ragflow_evidence", help="Output directory")
    parser.add_argument("--doc-id", dest="doc_id", default=None, help="Doc ID to embed into ChunkID (e.g., A320_v1)")
    parser.add_argument(
        "--mode",
        dest="mode",
        choices=["single", "multi", "both"],
        default="both",
        help="Output mode: single file / multi files / both",
    )
    args = parser.parse_args()

    in_path = Path(args.in_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_path.exists():
        raise FileNotFoundError(f"Input JSONL not found: {in_path}")

    # Default doc_id: use filename stem if not provided
    doc_id = args.doc_id or in_path.stem

    combined_md_parts: list[str] = []
    multi_dir = out_dir / "chunks"
    if args.mode in ("multi", "both"):
        multi_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for rec in iter_jsonl(in_path):
        section_id = safe_str(rec.get("section_id", "")).strip()
        title = safe_str(rec.get("title", "")).strip()
        path_list = safe_list_str(rec.get("path", []))
        content = safe_str(rec.get("content", ""))

        chunk_id = build_chunk_id(doc_id, section_id)

        md = render_markdown(
            doc_id=doc_id,
            section_id=section_id or "UNKNOWN",
            title=title,
            path_list=path_list,
            chunk_id=chunk_id,
            content=content,
        )

        # single file
        if args.mode in ("single", "both"):
            combined_md_parts.append(md)
            combined_md_parts.append("\n---\n")

        # multi files
        if args.mode in ("multi", "both"):
            # filename includes section_id + title for readability; still stable via chunk_id
            base = f"{chunk_id}__{title or (path_list[-1] if path_list else '')}"
            fname = sanitize_filename(base) + ".md"
            (multi_dir / fname).write_text(md, encoding="utf-8")

        count += 1

    if args.mode in ("single", "both"):
        combined_path = out_dir / "原文证据.md"
        # Remove trailing separator
        if combined_md_parts and combined_md_parts[-1].strip() == "---":
            combined_md_parts = combined_md_parts[:-1]
        combined_path.write_text("\n".join(combined_md_parts).strip() + "\n", encoding="utf-8")

    print(f"[OK] Converted {count} chunks.")
    print(f"[OUT] {out_dir.resolve()}")
    if args.mode in ("single", "both"):
        print(f"[OUT] single: {(out_dir / 'evidence_all.md').resolve()}")
    if args.mode in ("multi", "both"):
        print(f"[OUT] multi : {(out_dir / 'chunks').resolve()}")


if __name__ == "__main__":
    main()