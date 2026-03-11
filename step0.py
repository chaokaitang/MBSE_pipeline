# semantic_pipeline/demo.py
import json
import os
from io_utils import load_sections
from semantic_block.builder import build_candidates


if __name__ == "__main__":
    # sections = load_sections("../data/section_chunks.jsonl")
    sections = load_sections("data/full.jsonl")
    
    output_data = []

    for sec in sections:
        print(f"\n=== Section {sec.section_id} | {sec.title} ===")

        cands = build_candidates(sec)
        if not cands:
            print("(no candidates)")
            continue

        for c in cands:
            print(f"[{c.order:02d}] ({c.source}) {c.text}")
            
            # 保存到输出数据
            output_data.append({
                "section_id": c.section_id,
                "title": c.title,
                "path": c.path,
                "order": c.order,
                "text": c.text,
                "source": c.source
            })
    
    # 创建输出目录并保存为 JSON 文件
    os.makedirs("output", exist_ok=True)
    with open("output/paragraph_blocks.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
