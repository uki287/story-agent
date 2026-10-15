"""评估技能：五维各20分打分，返回结构化 JSON，并把问题清单写入记忆。"""
import json, re
from .base import Skill


class EvalSkill(Skill):
    """评估成稿质量（五维各20分）并列出问题。"""
    name, desc = "eval", "评估成稿质量（五维各20分）并列出问题"
    schema = {"type": "object", "properties": {}, "required": []}   # 无参数技能：显式声明空对象，避免模型困惑

    def run(self, ctx):
        p = ('评估下面这篇短篇小说，只输出 JSON：'
             '{"score":0,"scores":{"主题":0,"结构":0,"人物":0,"语言":0,"情感":0},"issues":[],"suggestions":[]}\n'
             f"规格：{ctx.spec.text()}\n正文：{ctx.get('draft')}")
        raw = self.ask(p, 0.0)
        m = re.search(r"\{.*\}", raw, re.S)
        try: d = json.loads(m.group()) if m else {}
        except json.JSONDecodeError: d = {}
        ctx.set("eval", d); ctx.set("issues", "\n".join(d.get("issues", [])))
        return json.dumps(d, ensure_ascii=False)
