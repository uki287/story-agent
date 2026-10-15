"""1.3 agent 循环：观察 → 思考 → 行动 → 观察（原生 Function Calling 手写版，不用框架）"""
import ast, json, operator, os
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
# 模型名与接口地址统一由 .env 提供（MODEL / OPENAI_BASE_URL），代码不写死服务商
MODEL = os.getenv("MODEL")
if not MODEL:
    raise ValueError("缺少环境变量 MODEL，请复制 .env.example 为 .env 并填入真实值")
MAX_STEPS, MAX_TOKENS = 8, 8000

# ── 工具实现层 ────────────────────────────────────────────────────────────────
# 安全计算：白名单 AST 求值，不用 eval()；只放行 + - * / 与一元负号
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.USub: operator.neg}

def _calc(node):
    if isinstance(node, ast.Expression):
        return _calc(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.left), _calc(node.right))
    raise ValueError(f"不支持的表达式：{type(node).__name__}")

def calculator(expression: str) -> dict:
    """计算数学表达式"""
    try:
        return {"ok": True, "result": _calc(ast.parse(expression, mode="eval"))}
    except Exception as e:
        return {"ok": False, "error": f"表达式无效：{e}"}   # 参数幻觉在这里被拦下并回传

def now() -> dict:
    """获取当前日期和时间"""
    return {"ok": True, "result": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

def weather(city: str) -> dict:
    """查询指定城市天气（演示用假数据）"""
    return {"ok": True, "result": f"{city}：晴，25℃"}

# ── 原生 Function Calling 的工具声明（喂给 API 的 tools 参数）────────────────
def _fs(name, desc, props, required=None):
    """把参数声明拼成 OpenAI 要求的 function calling schema"""
    p = {"type": "object", "properties": props}
    if required:
        p["required"] = required
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": p}}

SCHEMAS = [
    _fs("calculator", "计算数学表达式", {"expression": {"type": "string", "description": "如 (325+125)*123"}}, ["expression"]),
    _fs("now", "获取当前日期和时间", {}),
    _fs("weather", "查询城市天气", {"city": {"type": "string", "description": "城市名"}}, ["city"]),
]
REGISTRY = {"calculator": calculator, "now": now, "weather": weather}

# ── 循环本体 ──────────────────────────────────────────────────────────────────
def run(client, query: str) -> str:
    """跑完一轮完整循环：观察→思考→行动→观察，直到终止条件触发"""
    msgs = [{"role": "system", "content": "你可以调用工具解决问题。必须依据 tool 返回的观测结果作答，禁止编造。"},
            {"role": "user", "content": query}]
    # seen=调用指纹去重 | used=token 预算 | trace=追踪日志 | answer=最终答案
    seen, used, trace, answer = set(), 0, [], None
    for step in range(1, MAX_STEPS + 1):
        if used > MAX_TOKENS:                                   # 终止条件①：token 预算耗尽
            trace.append(f"token 预算耗尽（{used}）"); break
        # ── 观察 + 思考：交出全部历史，由模型自己决定要不要行动 ──
        rsp = client.chat.completions.create(model=MODEL, messages=msgs, tools=SCHEMAS, temperature=0)
        msg = rsp.choices[0].message
        used += (rsp.usage.total_tokens if rsp.usage else 0)   # 累计 token 用于预算控制；usage 可能为 None
        msgs.append(msg.model_dump(exclude_none=True))         # 助手的思考 + tool_calls 都要入历史
        calls = msg.tool_calls or []
        print(f"[step {step}] tokens={used} 工具调用={[c.function.name for c in calls] or '无'}")
        # ── 终止条件②：模型不再要求调工具 = 交卷 ──
        if not calls:
            if not any(m["role"] == "tool" for m in msgs):      # 防「未查工具就收尾」
                msgs.append({"role": "user", "content": "请先调用工具获取事实依据，再作答。"})
                trace.append("第1步就想收尾 → 已顶回追问"); continue
            trace.append("模型给出最终答案"); answer = msg.content; break
        # ── 行动：执行工具，结果用 role=tool + tool_call_id 原生协议回填 ──
        for c in calls:
            fp = (c.function.name, c.function.arguments)        # 指纹 = 工具名 + 参数
            if fp in seen:                                      # 防死循环：同样的调用只放行一次
                out = json.dumps({"ok": False, "error": "重复调用已拦截，请换思路或直接作答"}, ensure_ascii=False)
                trace.append(f"拦截重复调用：{c.function.name}"); print(f"   ↳ {fp} → 重复，已拦截")
            else:
                seen.add(fp)
                try:
                    out = json.dumps(REGISTRY[c.function.name](**json.loads(c.function.arguments or "{}")), ensure_ascii=False)
                except Exception as e:
                    out = json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)  # 工具名/参数幻觉
                print(f"   ↳ {fp} → {out}")
            msgs.append({"role": "tool", "tool_call_id": c.id, "content": out})   # 必须带 id，否则 400
    if answer is None:                                          # 步数或预算耗尽 → 强制收尾，不留空白
        msgs.append({"role": "user", "content": "预算已耗尽，请只根据已有观测数据给出最终答案，不要再调用工具。"})
        answer = client.chat.completions.create(model=MODEL, messages=msgs, temperature=0).choices[0].message.content
        trace.append(f"截停后强制收尾（token={used}）")
    print("--- 追踪日志 ---\n" + "\n".join(f"  {i+1}. {t}" for i, t in enumerate(trace)))
    return answer

if __name__ == "__main__":
    c = OpenAI(base_url=os.getenv("OPENAI_BASE_URL"), api_key=os.getenv("OPENAI_API_KEY"))
    for q in ["广州今天的天气怎么样", "帮我计算（325 + 125） *123 的结果", "今天是几号？广州的天气怎么样"]:
        print(f"\n用户：{q}"); print(f"回答：{run(c, q)}")
