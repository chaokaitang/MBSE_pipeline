# semantic_pipeline/semantic_block/models.py
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Section:
    section_id: str
    title: str
    path: List[str]
    content: str


@dataclass(frozen=True)
class CandidateBlock:
    """
    Step 1 的最终产物
    """
    section_id: str
    title: str
    path: List[str]
    order: int          # 在 section 内的顺序（从 1 开始）
    text: str
    source: str         # para / enum / semi / enum+semi / figure / table
