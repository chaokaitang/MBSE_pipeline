# semantic_pipeline/splitter/heuristic_split.py
from dataclasses import dataclass
from typing import List
import re


@dataclass(frozen=True)
class Candidate:
    text: str
    order: int
    source: str


# a） b） c) / 1） / （1）
_ENUM_PATTERN = re.compile(
    r"(?m)^\s*(?:[a-zA-Z]\s*[）\)]|\d+\s*[）\)]|[（(]\d+[）)])\s*"
)

_FIGURE_PATTERN = re.compile(r"^\s*(图|表)\s*\d+")

_TABLE_PATTERN = re.compile(r"^\s*\|(.+\|)+\s*$", re.MULTILINE)


def _split_by_enum(text: str) -> List[str]:
    matches = list(_ENUM_PATTERN.finditer(text))
    if len(matches) <= 1:
        return [text]

    blocks = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        part = text[start:end].strip()
        if part:
            blocks.append(part)

    return blocks if blocks else [text]


def _split_by_semicolon(text: str) -> List[str]:
    if "；" not in text or len(text) < 40:
        return [text]

    parts = [p.strip() for p in text.split("；") if p.strip()]
    if len(parts) <= 1:
        return [text]

    merged = []
    for p in parts:
        if merged and len(p) < 12:
            merged[-1] += "；" + p
        else:
            merged.append(p)

    return merged if merged else [text]


def _is_table(text: str) -> bool:
    """
    检测文本是否为表格格式（使用 | 作为列分隔符）
    """
    lines = text.strip().split("\n")
    
    # 表格标记：以 [表格] 开头
    if lines and "[表格]" in lines[0]:
        return True
    
    # 表格特征：多行且至少80%的行包含 | 符号
    if len(lines) < 2:
        return False
    
    table_lines = [line for line in lines if "|" in line]
    return len(table_lines) >= 2 and len(table_lines) >= len(lines) * 0.8


def heuristic_split(paragraph_text: str) -> List[Candidate]:
    """
    对单个段落进行规则触发切分
    """
    base = paragraph_text.strip()
    if not base:
        return []

    # 图/表注，原样返回，交给后续过滤
    if _FIGURE_PATTERN.match(base):
        return [Candidate(text=base, order=1, source="figure")]
    
    # 表格检测 - 如果整个段落被标记为表格或包含 | 符号的多行
    if _is_table(base):
        return [Candidate(text=base, order=1, source="table")]
    
    # 单行表格数据检测 - 包含 | 符号且不是标准段落
    if "|" in base and not ";" in base and base.count("|") >= 1:
        return [Candidate(text=base, order=1, source="table")]

    enum_blocks = _split_by_enum(base)

    results: List[Candidate] = []
    order = 1

    for eb in enum_blocks:
        semi_blocks = _split_by_semicolon(eb)

        if len(enum_blocks) > 1:
            src = "enum+semi" if len(semi_blocks) > 1 else "enum"
        else:
            src = "semi" if len(semi_blocks) > 1 else "para"

        for sb in semi_blocks:
            results.append(Candidate(text=sb, order=order, source=src))
            order += 1

    return results
