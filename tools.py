from typing import Dict, Any, Callable
import json

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, dict] = {}
    
    def register(self, name: str, description: str, schema: dict, func: Callable):
        """注册一个工具"""
        self._tools[name] = func
        self._schemas[name] = {
            "name": name,
            "description": description,
            "parameters": schema
        }
        
    def get_tools(self) -> list:
        """获取所有工具的格式（用于system prompt）"""
        return self._schemas
    
    def execute(self, tool_name: str, params: dict) -> str:
        """执行工具调用"""
        if tool_name not in self._tools:
            return f"错误：工具 {tool_name} 不存在"
        try:
            result = self._tools[tool_name](**params)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return f"工具执行错误：{str(e)}"
        
#预置工具示例
def create_default_tools() -> ToolRegistry:
    """创建默认工具集"""
    registry = ToolRegistry()
    
    #计算器工具
    import ast
    import operator
    
    _SAFE_OPS = {
        ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv
    }
    
    def _safe_eval(expression: str):
        def eval_node(node):
            if isinstance(node, ast.Expression):
                return eval_node(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
                return _SAFE_OPS[type(node.op)](eval_node(node.left), eval_node(node.right))
            raise ValueError(f"不支持的表达式：{type(node).__name__}")
        
        return eval_node(ast.parse(expression, mode="eval"))
    
    registry.register(
        name="calculator",
        description="执行数学计算，支持加减乘除、括号等",
        schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如‘2+3*4’"
                }
            },
            "required": ["expression"]
        },
        func=_safe_eval
    )
    
    #日期工具
    from datetime import datetime
    registry.register(
        name="get_current_date",
        description="获取当前的日期和时间",
        schema={},
        func=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    #天气工具（模拟）
    registry.register(
        name="get_weather",
        description="查询指定城市的天气信息",
        schema={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称"
                }
            },
            "required": ["city"]
        },
        func=lambda city: f"{city}今日天气：晴，温度 25度"
    )
    
    return registry