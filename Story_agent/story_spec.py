"""解析层：把自然语言需求翻译成结构化创作规格 StorySpec。"""
import json, re
from dataclasses import dataclass, field, asdict


@dataclass
class StorySpec:
    """创作规格：需求在整个流程中的唯一真相来源。"""
    topic: str = ""; genre: str = "童话"; length: int = 1200
    style: str = "温暖治愈"; audience: str = "青少年"; tone: str = "轻松"
    must_have: list = field(default_factory=list); avoid: list = field(default_factory=list)

    def text(self) -> str: return json.dumps(asdict(self), ensure_ascii=False, indent=2)


_PROMPT = """把用户需求解析为 JSON，只输出 JSON，不要解释：
{{"topic":"","genre":"","length":1200,"style":"","audience":"","tone":"","must_have":[],"avoid":[]}}
主题：{topic}
补充要求：{req}"""


def parse_spec(llm, topic: str, req: str = "") -> StorySpec:
    """自然语言 → StorySpec；解析失败用原始主题兜底，保证流程不中断。"""
    raw = llm.chat([{"role": "user", "content": _PROMPT.format(topic=topic, req=req)}], temperature=0.0)
    m = re.search(r"\{.*\}", raw, re.S)
    try: d = json.loads(m.group()) if m else {}
    except json.JSONDecodeError: d = {}
    d["topic"] = d.get("topic") or topic
    n = re.search(r"\d+", str(d.get("length", 1200))); d["length"] = int(n.group()) if n else 1200
    return StorySpec(**{k: v for k, v in d.items() if k in StorySpec.__dataclass_fields__})
