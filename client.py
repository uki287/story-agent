import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

#支持多种后端
class LLMClient:
    def __init__(self, model: str = "deepseek-flash"):
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        api_key = os.getenv("OPENAI_API_KEY")
        
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
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