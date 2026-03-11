# semantic_pipeline/semantic_block/builder.py
from typing import List

from semantic_block.models import Section, CandidateBlock
from splitter.paragraph_split import paragraph_split
from splitter.heuristic_split import heuristic_split


def build_candidates(section: Section) -> List[CandidateBlock]:
    """
    Step 1：Section → CandidateBlock[]
    """
    if not section.content.strip():
        return []

    para_chunks = paragraph_split(section.content)

    candidates: List[CandidateBlock] = []
    global_order = 1

    for para in para_chunks:
        parts = heuristic_split(para.text)

        for p in parts:
            text = p.text.strip()
            if not text:
                continue

            candidates.append(
                CandidateBlock(
                    section_id=section.section_id,
                    title=section.title,
                    path=section.path,
                    order=global_order,
                    text=text,
                    source=p.source
                )
            )
            global_order += 1

    return candidates
