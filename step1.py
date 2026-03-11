# semantic_pipeline/step1.py
"""
Step 1: CandidateBlock → SemanticBlock
对每个候选块调用 LLM 进行语义分析与拆分
"""
import json
import os
from typing import List, Dict, Any
from llm.client import create_client


# ================================
# 配置
# ================================
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "qwen2.5-7b-step1"

INPUT_FILE = "output/paragraph_blocks.json"
OUTPUT_FILE = "output/semantic_blocks.json"


def load_candidate_blocks(file_path: str) -> List[Dict[str, Any]]:
    """加载 Step 0 生成的候选块"""
    with open(file_path, "r", encoding="utf-8") as f:
        blocks = json.load(f)
    return blocks


def build_prompt(candidate: Dict[str, Any]) -> str:
    """
    构造 LLM 输入 prompt
    
    输入：一个 CandidateBlock
    输出：完整的 candidate JSON 字符串
    """
    return json.dumps(candidate, ensure_ascii=False, indent=2)


def process_candidate(
    client, 
    candidate: Dict[str, Any], 
    index: int, 
    total: int
) -> List[Dict[str, Any]]:
    """
    处理单个候选块
    
    返回：SemanticBlock 列表（可能是 1 个或多个）
    """
    print(f"\n[{index}/{total}] Processing section_id={candidate['section_id']}, order={candidate['order']}")
    print(f"  source={candidate['source']}, text_len={len(candidate['text'])}")
    
    # 构造 prompt
    prompt = build_prompt(candidate)
    
    # 调用 LLM（非流式，获取完整响应）
    try:
        response = client.chat(prompt=prompt, stream=False)
        content = client.extract_content(response)
        
        # 解析 JSON
        parsed = client.parse_json_response(content)
        
        # 规范化：如果是单个对象，包装成列表
        if isinstance(parsed, dict):
            parsed = [parsed]
        
        # 为每个 SemanticBlock 补充元数据
        semantic_blocks = []
        for i, block in enumerate(parsed):
            semantic_block = {
                # 继承原始元数据
                "section_id": candidate["section_id"],
                "title": candidate["title"],
                "path": candidate["path"],
                "original_order": candidate["order"],
                "original_source": candidate["source"],
                
                # LLM 输出的语义信息
                "block_type": block.get("block_type", "Other"),
                "content": block.get("content", ""),
                "confidence": block.get("confidence", 0.0),
                
                # 拆分序号（如果一个 candidate 拆成多个）
                "split_index": i + 1,
                "split_count": len(parsed)
            }
            semantic_blocks.append(semantic_block)
        
        print(f"  -> {len(semantic_blocks)} block(s) generated")
        return semantic_blocks
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        # 出错时返回一个兜底 block
        return [{
            "section_id": candidate["section_id"],
            "title": candidate["title"],
            "path": candidate["path"],
            "original_order": candidate["order"],
            "original_source": candidate["source"],
            "block_type": "Other",
            "content": candidate["text"],
            "confidence": 0.0,
            "split_index": 1,
            "split_count": 1,
            "error": str(e)
        }]


def main():
    """主流程：Step 1"""
    
    print("=" * 60)
    print("Step 1: CandidateBlock → SemanticBlock (LLM 语义分析)")
    print("=" * 60)
    
    # 1. 加载候选块
    print(f"\n[1/4] 加载输入文件: {INPUT_FILE}")
    candidates = load_candidate_blocks(INPUT_FILE)
    print(f"  共 {len(candidates)} 个候选块")
    
    # 1.5. 过滤掉 figure 和 table（图表不作为输入）
    print(f"\n[1.5/4] 过滤图表类型 (figure, table)")
    before_filter = len(candidates)
    candidates = [c for c in candidates if c.get("source") not in ("figure", "table")]
    after_filter = len(candidates)
    print(f"  过滤前: {before_filter} 个块")
    print(f"  过滤后: {after_filter} 个块")
    print(f"  已去除: {before_filter - after_filter} 个图表块")
    
    # 2. 创建 LLM 客户端
    print(f"\n[2/4] 初始化 LLM 客户端")
    print(f"  URL: {OLLAMA_URL}")
    print(f"  Model: {MODEL_NAME}")
    client = create_client(base_url=OLLAMA_URL, model=MODEL_NAME)
    
    # 3. 逐个处理
    print(f"\n[3/4] 开始处理候选块")
    all_semantic_blocks = []
    
    for i, candidate in enumerate(candidates, start=1):
        blocks = process_candidate(client, candidate, i, len(candidates))
        all_semantic_blocks.extend(blocks)
    
    # 4. 保存输出
    print(f"\n[4/4] 保存输出文件: {OUTPUT_FILE}")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_semantic_blocks, f, ensure_ascii=False, indent=2)
    
    print(f"  共生成 {len(all_semantic_blocks)} 个语义块")
    
    # 统计
    print("\n" + "=" * 60)
    print("统计信息")
    print("=" * 60)
    print(f"输入候选块数: {len(candidates)}")
    print(f"输出语义块数: {len(all_semantic_blocks)}")
    print(f"拆分率: {len(all_semantic_blocks) / len(candidates):.2f}x")
    
    # block_type 分布
    type_counts = {}
    for block in all_semantic_blocks:
        bt = block.get("block_type", "Unknown")
        type_counts[bt] = type_counts.get(bt, 0) + 1
    
    print("\nblock_type 分布:")
    for bt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {bt}: {count}")
    
    print("\n✓ Step 1 完成")


if __name__ == "__main__":
    main()
