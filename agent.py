import re
import json
from typing import Optional
from client import LLMClient
from tools import ToolRegistry
from prompt import build_system_prompt

class ReActAgent:
    """从零实现的 ReAct Agent"""
    
    def __init__(self, tools: ToolRegistry, model: str = "gpt-4o-mini"):
        self.tools = tools
        self.llm = LLMClient(model=model)
        self.system_prompt = build_system_prompt(tools.get_tools())
        self.step_count = 0
        self.max_steps = 10
        
    def run(self, query: str) -> str:
        """运行 Agent"""
        self.step_count = 0
        self.llm.reset()
        self.llm.add_message("system", self.system_prompt)
        self.llm.add_message("user", query)
        
        print(f"\n🤖 用户: {query}\n")
        
        while self.step_count < self.max_steps:
            self.step_count += 1
            print(f"{'='*50}")
            print(f"🔄 步骤 {self.step_count}")
            
            # 调用 LLM
            response = self.llm.get_response()
            print(f"💭 思考: {response[:200]}...")
            
            # 检查是否包含最终答案
            final_answer_match = re.search(r'Final Answer:\s*(.*)', response, re.DOTALL)
            if final_answer_match:
                final_answer = final_answer_match.group(1).strip()
                print(f"✅ 最终答案: {final_answer}")
                return final_answer
            
            # 解析工具调用（re.DOTALL 让 . 匹配换行，支持多行 JSON 参数）
            action_match = re.search(
                r'Action:\s*(\w+)\s*\nAction Input:\s*(\{.*\})',
                response,
                re.DOTALL
            )
            if action_match:
                tool_name = action_match.group(1)
                tool_input = action_match.group(2).strip()
                
                # 解析参数
                try:
                    params = json.loads(tool_input)
                except json.JSONDecodeError:
                    # ❌ 不要猜测 {"value": tool_input}——工具可能没有 value 参数，
                    # 猜测会导致"参数不匹配"错误。正确做法是要求模型重新输出。
                    print("⚠️ Action Input 不是合法 JSON，要求模型重试")
                    self.llm.add_message("assistant", response)
                    self.llm.add_message(
                        "user",
                        "你上一条 Action Input 不是合法的 JSON 对象，"
                        "请重新按格式输出（Action Input 必须是 {...} 的 JSON）。"
                    )
                    continue
                
                print(f"🛠️ 调用工具: {tool_name}({params})")
                
                # 执行工具
                result = self.tools.execute(tool_name, params)
                print(f"📊 工具结果: {result[:200]}...")
                
                # ⚠️ 关键协议细节：本示例是"文本协议"（Thought/Action/...），
                # 工具结果必须作为 role="user" 消息回传。
                # 不要用 role="tool"！那是 OpenAI 原生 Function Calling 的协议消息，
                # 必须携带 tool_call_id 且前面有对应的 assistant tool_calls，
                # 直接使用会报 400 错误。
                self.llm.add_message("assistant", response)
                self.llm.add_message("user", f"Observation: {result}")
            else:
                # 既没有最终答案也没有工具调用
                print("⚠️ 无法解析响应，尝试其他方式...")
                self.llm.add_message("user", "请重新思考，并明确说明你的最终答案。")
        
        return "❌ 达到最大步骤限制，任务未能完成"