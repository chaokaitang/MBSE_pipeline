# semantic_pipeline/llm/client.py
import json
import requests
from typing import Optional, Dict, Any, List, Union


class OllamaClient:
    """Ollama API 客户端封装"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5-7b-step1"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.chat_endpoint = f"{self.base_url}/api/chat"
    
    def chat(
        self, 
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], str]:
        """
        调用 Ollama chat API
        
        Args:
            prompt: 用户输入
            system: 系统提示（可选，模型已有默认 SYSTEM）
            temperature: 温度参数（可选，覆盖模型默认值）
            stream: 是否流式输出
            
        Returns:
            非流式：返回完整响应字典
            流式：返回完整文本内容
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": stream
        }
        
        # 如果指定了 system（覆盖模型默认）
        if system:
            payload["messages"].insert(0, {"role": "system", "content": system})
        
        # 如果指定了 temperature（覆盖模型默认）
        if temperature is not None:
            payload["options"] = {"temperature": temperature}
        
        try:
            response = requests.post(
                self.chat_endpoint,
                json=payload,
                stream=stream,
                timeout=120
            )
            response.raise_for_status()
            
            if stream:
                # 流式响应：拼接所有 message.content
                full_text = ""
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            full_text += chunk["message"]["content"]
                return full_text
            else:
                # 非流式响应：返回完整 JSON
                result = response.json()
                return result
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama API 调用失败: {e}")
    
    def extract_content(self, response: Dict[str, Any]) -> str:
        """从响应中提取 assistant 返回的文本内容"""
        if "message" in response and "content" in response["message"]:
            return response["message"]["content"]
        return ""
    
    def parse_json_response(self, content: str) -> Union[Dict, List]:
        """
        解析 LLM 返回的 JSON 内容
        
        支持：
        - 单个对象：{...}
        - 对象数组：[{...}, {...}]
        - 去除可能的 markdown 代码块标记
        """
        # 清理可能的 markdown 代码块
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM 返回内容不是有效 JSON: {e}\n原始内容:\n{content}")


def create_client(base_url: str = "http://localhost:11434", model: str = "qwen2.5-7b-step1") -> OllamaClient:
    """工厂函数：创建 Ollama 客户端"""
    return OllamaClient(base_url=base_url, model=model)
