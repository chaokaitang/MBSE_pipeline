# semantic_pipeline/splitter/paragraph_split.py
from dataclasses import dataclass
from typing import List
import re


@dataclass(frozen=True)
class ParaChunk:
    text: str
    order: int


_PARAGRAPH_SPLIT = re.compile(r"\n{1,}")  # 一个或多个换行


def paragraph_split(section_content: str) -> List[ParaChunk]:
    """
    基于换行的段落初切
    - 不判断语义
    - 保证顺序稳定
    """
    if not section_content or not section_content.strip():
        return []

    text = section_content.replace("\r\n", "\n").replace("\r", "\n").strip()

    parts = [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]

    chunks: List[ParaChunk] = []
    for idx, part in enumerate(parts, start=1):
        part = re.sub(r"[ \t]+", " ", part).strip()
        chunks.append(ParaChunk(text=part, order=idx))

    return chunks
