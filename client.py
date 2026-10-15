import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

#支持多种后端
class LLMClient:
    """OpenAI 兼容客户端。

    模型名与接口地址都从环境变量读取（MODEL / OPENAI_BASE_URL），不在代码里写死任何
    具体服务商，避免把个人配置带进仓库。三个变量缺一时直接抛错说明原因，
    好过静默用一个可能无权限或已下线的模型去请求、然后收到难以理解的报错。
    """
    def __init__(self, model: str = None):
        base_url = os.getenv("OPENAI_BASE_URL")
        api_key = os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("MODEL")
        for name, val in (("OPENAI_BASE_URL", base_url), ("OPENAI_API_KEY", api_key), ("MODEL", self.model)):
            if not val:
                raise ValueError(f"缺少环境变量 {name}，请复制 .env.example 为 .env 并填入真实值")

        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.messages = []  # 统一用复数
        
    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        
    def get_response(self, system_prompt: str = None) -> str:
        """发送请求并返回响应"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.messages)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # 参数名改为 messages
            temperature=0.3  #降低随机性
        )
        
        return response.choices[0].message.content
    
    def reset(self):
        """重置对话历史"""
        self.messages = []