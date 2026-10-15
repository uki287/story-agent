"""风格技能：制定风格指南（人称/句式/节奏/用词/禁忌）。"""
from .base import Skill


class StyleSkill(Skill):
    """制定语言风格指南（人称、句式、节奏、用词）。"""
    name, desc = "style", "制定语言风格指南（人称、句式、节奏、用词）"
    schema = {"type": "object", "properties": {"reference": {"type": "string"}}, "required": []}

    def run(self, ctx, reference=""):
        r = self.ask(f"为这篇小说制定风格指南（人称视角/句式长短/节奏/偏爱词汇/禁忌表达）。\n规格：{ctx.spec.text()}\n参照：{reference or '无'}", 0.6)
        ctx.set("style", r); return r
