"""公共层：大模型客户端 —— 全项目唯一读取密钥的入口。"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # 自动向上查找项目根目录的 .env（OPENAI_API_KEY / OPENAI_BASE_URL）


class LLM:
    """统一大模型客户端：不在别处 new OpenAI()，便于统一管理密钥与预算。"""

    def __init__(self, model=None, temperature=0.7):
        self.c = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
        self.model, self.temperature, self.tokens = model or "deepseek-chat", temperature, 0

    def chat(self, messages, temperature=None) -> str:
        """发一次对话并返回文本；顺带累计 token 供预算熔断。"""
        r = self.c.chat.completions.create(model=self.model, messages=messages,
                                          temperature=self.temperature if temperature is None else temperature)
        self.tokens += getattr(r.usage, "total_tokens", 0)
        return r.choices[0].message.content or ""
