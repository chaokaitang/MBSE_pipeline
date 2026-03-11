import requests
import json
from dataclasses import dataclass
from typing import List, Optional

# =========================================================
# 1. SemanticBlock 数据结构（最小）
# =========================================================

@dataclass
class SemanticBlock:
    section_id: str
    block_id: str
    order: int
    block_type: str
    confidence: float
    content: str
    summary: Optional[str]
    tags: List[str]


# =========================================================
# 2. OllamaClient（最小可用）
# =========================================================

class OllamaClient:
    def __init__(
        self,
        model: str = "qwen2.5-7b-step1",
        base_url: str = "http://localhost:11434"
    ):
        self.model = model
        self.url = f"{base_url}/api/chat"

    def generate(self, prompt: str) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 200
            }
        }

        resp = requests.post(self.url, json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json()



# =========================================================
# 3. Prompt（Step 4 专用，最小但足够）
# =========================================================

BLOCK_CLASSIFY_PROMPT = """
<<<TEXT>>>
"""


def build_prompt(text: str) -> str:
    return BLOCK_CLASSIFY_PROMPT.replace("<<<TEXT>>>", text)


# =========================================================
# 4. Step 4：语义子块构建（最小实现）
# =========================================================

def split_by_paragraph(content: str) -> List[str]:
    return [p.strip() for p in content.split("\n") if p.strip()]


def build_semantic_blocks(section: dict, llm: OllamaClient) -> List[SemanticBlock]:
    blocks = []
    paragraphs = split_by_paragraph(section["content"])

    for idx, para in enumerate(paragraphs):
        prompt = build_prompt(para)
        raw = llm.generate(prompt)

        try:
            result = json.loads(raw["response"])
        except Exception as e:
            print("\n[JSON PARSE ERROR]")
            print(raw["response"])
            continue

        if not result.get("is_single_semantic", False):
            continue

        block = SemanticBlock(
            section_id=section["section_id"],
            block_id=f"{section['section_id']}-{idx}",
            order=idx,
            block_type=result.get("block_type"),
            confidence=result.get("confidence", 0.0),
            content=para,
            summary=result.get("summary"),
            tags=result.get("tags", []),
        )
        blocks.append(block)

    return blocks


# =========================================================
# 5. 最小 Test（用你给的 8.2 文本）
# =========================================================

SECTION_8_2_MIN = {
    "section_id": "8.2",
    "content": """
为满足主飞控系统安全性要求，主飞控系统设计采用以下安全性设计特征。
主飞控系统架构采用3个FCM和4个ACE，控制所有操纵面的作动器。
主飞控系统在飞行员指令到作动器输出的链路上设置多级监控和表决面。
FCM硬件采用指令-监控架构，指令和监控通道硬件设计非相似。
ACE硬件采用分区、隔离和非相似设计，避免共模失效。
"""
}


def run_test():
    llm = OllamaClient(model="qwen3-4b-instruct-seg")

    blocks = build_semantic_blocks(SECTION_8_2_MIN, llm)

    print("\n====== Step 4 Minimal Test Result ======\n")

    for b in blocks:
        print("-" * 60)
        print(f"Block ID   : {b.block_id}")
        print(f"Type       : {b.block_type}")
        print(f"Confidence : {b.confidence}")
        print(f"Tags       : {b.tags}")
        print(f"Summary    : {b.summary}")
        print(f"Content    : {b.content}")

    print(f"\nTotal blocks: {len(blocks)}")


if __name__ == "__main__":
    run_test()
