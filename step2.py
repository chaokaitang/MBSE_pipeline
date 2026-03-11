# semantic_pipeline/step2.py
"""
Step 2: Object Candidate Extraction
"""
from typing import Dict, Any, List
import json
import os

from llm.client import create_client


# 默认 LLM 配置（可按需覆盖）
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "qwen2.5-7b-step2"
INPUT_FILE = "output/semantic_blocks.json"
OUTPUT_FILE = "output/candidate_blocks.json"


def llm_call(input_json: Dict[str, Any], client=None) -> Dict[str, Any]:
    """
    Placeholder LLM call. Replace with real implementation.
    Must return a dict with keys: components, interfaces, functions, logic_rules.
    """
    # 创建或使用传入的客户端（使用默认配置）
    if client is None:
        client = create_client(base_url=OLLAMA_URL, model=MODEL_NAME)

    # 将整个 input_json 原封不动地序列化为 prompt
    prompt = json.dumps(input_json, ensure_ascii=False)

    # 调用模型（非流式）
    resp = client.chat(prompt=prompt, stream=False)
    content = client.extract_content(resp)

    # 解析 LLM 返回的 JSON（可能是对象或数组）
    parsed = client.parse_json_response(content)

    # 验证返回结构并确保字段存在
    result: Dict[str, Any] = {}
    
    # 提取 system_tag（新增字段）
    result["system_tag"] = parsed.get("system_tag", "未分类") if isinstance(parsed, dict) else "未分类"
    if not isinstance(result["system_tag"], str):
        result["system_tag"] = "未分类"
    
    # 提取四个列表字段
    result["components"] = parsed.get("components", []) if isinstance(parsed, dict) else []
    result["interfaces"] = parsed.get("interfaces", []) if isinstance(parsed, dict) else []
    result["functions"] = parsed.get("functions", []) if isinstance(parsed, dict) else []
    result["logic_rules"] = parsed.get("logic_rules", []) if isinstance(parsed, dict) else []

    # 强制类型为 list（如果 LLM 返回非 list，保留原样但包装为空列表）
    for k in ["components", "interfaces", "functions", "logic_rules"]:
        if not isinstance(result.get(k), list):
            result[k] = []

    return result




def run_step2(block_json: Dict[str, Any], client=None) -> Dict[str, Any]:
    """
    输入单个 SemanticBlock JSON，调用 LLM 抽取对象候选并补齐外层元信息。
    """
    # 兼容：如果 run_step2 被单独调用且没有 client，则内部创建
    llm_result = llm_call(block_json, client=client)

    output = {
        "section_id": block_json.get("section_id", ""),
        "title": block_json.get("title", ""),
        "path": block_json.get("path", []),
        "content": block_json.get("content", ""),
        "system_tag": llm_result.get("system_tag", "未分类"),
        "components": llm_result.get("components", []),
        "interfaces": llm_result.get("interfaces", []),
        "functions": llm_result.get("functions", []),
        "logic_rules": llm_result.get("logic_rules", []),
    }

    return output


def load_semantic_blocks(file_path: str) -> List[Dict[str, Any]]:
    """加载 Step1 生成的 semantic blocks 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def process_block(client, block: Dict[str, Any], index: int, total: int) -> Dict[str, Any]:
    """处理单个 semantic block：调用 llm 并补齐元信息，返回单个输出对象"""
    print(f"\n[{index}/{total}] Processing section_id={block.get('section_id')}")
    try:
        result = run_step2(block, client=client)
        print("  -> OK")
        return result
    except Exception as e:
        print(f"  [ERROR] {e}")
        # 在出错时返回一个空结构，保证字段存在
        return {
            "section_id": block.get("section_id", ""),
            "title": block.get("title", "") ,
            "path": block.get("path", []),
            "content": block.get("content", ""),
            "system_tag": "未分类",
            "components": [],
            "interfaces": [],
            "functions": [],
            "logic_rules": [],
            "error": str(e),
        }


def main():


    print("=" * 60)
    print("Step 2: SemanticBlock → Object Candidates (LLM)")
    print("=" * 60)

    # 1. 加载输入
    print(f"\n[1/5] 加载输入文件: {INPUT_FILE}")
    blocks = load_semantic_blocks(INPUT_FILE)
    print(f"  共 {len(blocks)} 个 semantic blocks")

    # 2. 过滤掉 block_type 为 "Other" 的废话块
    print(f"\n[2/5] 过滤 Other 类型块（废话去除）")
    before_filter = len(blocks)
    blocks = [b for b in blocks if b.get("block_type") != "Other"]
    after_filter = len(blocks)
    print(f"  过滤前: {before_filter} 个块")
    print(f"  过滤后: {after_filter} 个块")
    print(f"  已去除: {before_filter - after_filter} 个 Other 块")

    # 3. 创建 LLM 客户端
    print(f"\n[3/5] 初始化 LLM 客户端")
    print(f"  URL: {OLLAMA_URL}")
    print(f"  Model: {MODEL_NAME}")
    client = create_client(base_url=OLLAMA_URL, model=MODEL_NAME)

    # 4. 逐个处理
    print(f"\n[4/5] 开始处理 blocks")
    outputs = []
    for i, b in enumerate(blocks, start=1):
        out = process_block(client, b, i, len(blocks))
        outputs.append(out)

    # 5. 保存输出
    print(f"\n[5/5] 保存输出文件: {OUTPUT_FILE}")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(outputs, f, ensure_ascii=False, indent=2)

    print(f"  共生成 {len(outputs)} 个对象候选文件条目")


if __name__ == "__main__":
    main()


