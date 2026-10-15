"""公共层：大模型客户端 —— 全项目唯一读取密钥的入口。"""
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 只认本文件同目录下的 .env，与项目根目录那份配置彻底隔离。
# 为什么必须显式给路径：load_dotenv() 无参调用会从当前文件所在目录逐级向上查找，
# 找不到就借用根目录的 .env。短篇小说智能体要能单独拷走运行、也能独立换服务商，
# 借用根配置会让人误以为改根目录就能生效，实际两份配置互相干扰且难以排查。
_ENV = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV)


class LLM:
    """统一大模型客户端：不在别处 new OpenAI()，便于统一管理密钥与预算。

    模型名优先级：构造参数 > 环境变量 MODEL。代码里不写死任何具体服务商，
    三个变量（BASE_URL / API_KEY / MODEL）缺一时直接抛错说明原因 —— 静默用一个
    可能无权限或已下线的模型去请求，报错会很难定位。

    换服务商时只需改 .env 里的三个值，本文件无需改动：
    凡是兼容 OpenAI Chat Completions 协议的服务都能直接接入。
    """

    def __init__(self, model=None, temperature=0.7):
        base_url, api_key = os.getenv("OPENAI_BASE_URL"), os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("MODEL")
        for name, val in (("OPENAI_BASE_URL", base_url), ("OPENAI_API_KEY", api_key), ("MODEL", self.model)):
            if not val:
                raise ValueError(f"缺少环境变量 {name}，请复制同目录的 .env.example 为 .env 并填入真实值")
        self.c = OpenAI(api_key=api_key, base_url=base_url)
        self.temperature, self.tokens = temperature, 0

    def chat(self, messages, temperature=None) -> str:
        """发一次对话并返回文本；顺带累计 token 供预算熔断。"""
        r = self.c.chat.completions.create(model=self.model, messages=messages,
                                          temperature=self.temperature if temperature is None else temperature)
        self.tokens += getattr(r.usage, "total_tokens", 0)
        return r.choices[0].message.content or ""
