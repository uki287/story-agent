SYSTEM_PROMPT_TEMPLATE = """你是一个智能助手，可以通过调用工具来帮助用户完成任务。

可用的工具：{tools}

当你需要使用工具时，请按照以下的格式进行回复：
Thought: [你的思考过程]
Action: [工具名称]
Action Input: [工具参数，必须是合法的 JSON 对象, 如{{"key": "value"}}]

当你知道最终答案时，请这样回复：
Thought: [你的思考过程]
Final Answer: [你的最终答案]

重要规则：
1.每次只能调用一个工具
2.Action Input 必须是合法的 JSON 对象(如{{"expression": "2+3"}})
3.观察工具的返回结果后再决定下一步
4.最多执行10个步骤
5.如果工具调用失败，尝试其他方式
"""

def build_system_prompt(tools: list) -> str:
    import json
    """构建System Prompt"""
    tools_json = json.dumps(tools, indent=2, ensure_ascii=False)
    return SYSTEM_PROMPT_TEMPLATE.format(tools=tools_json)