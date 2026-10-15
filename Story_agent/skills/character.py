"""人物技能：设计角色卡片（身份/性格/动机/成长弧光）。"""
from .base import Skill


class CharacterSkill(Skill):
    """设计人物卡片（身份、性格、动机、成长弧光）。"""
    name, desc = "character", "设计人物卡片（身份、性格、动机、成长弧光）"
    schema = {"type": "object", "properties": {}, "required": []}   # 无参数技能：显式声明空对象，避免模型困惑

    def run(self, ctx):
        r = self.ask(f"设计人物卡片（主角+配角）。\n规格：{ctx.spec.text()}\n大纲：{ctx.get('outline_detail') or ctx.get('outline_brief')}", 0.7)
        ctx.set("characters", r); return r
