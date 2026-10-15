"""正文技能：依据大纲/人物/风格/素材撰写或修订正文，并写入记忆。"""
from .base import Skill


class DraftSkill(Skill):
    """撰写或修订小说正文。"""
    name, desc = "draft", "撰写或修订小说正文"
    schema = {"type": "object", "properties": {"instruction": {"type": "string"}}, "required": []}

    def run(self, ctx, instruction=""):
        p = (f"撰写小说正文，约{ctx.spec.length}字，仅输出正文。\n规格：{ctx.spec.text()}\n"
             f"详细大纲：{ctx.get('outline_detail')}\n人物：{ctx.get('characters')}\n风格指南：{ctx.get('style')}\n"
             f"素材：{ctx.get('materials')}\n上轮问题：{ctx.get('issues')}\n补充要求：{instruction}")
        ctx.set("draft", r := self.ask(p, 0.85)); return r
