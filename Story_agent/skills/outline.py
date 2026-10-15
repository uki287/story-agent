"""大纲技能：brief 出摘要卡（约150字，供快速验收）；detail 展开详细大纲。"""
from .base import Skill


class OutlineSkill(Skill):
    """生成故事大纲：mode=brief 摘要卡，mode=detail 详细大纲。"""
    name, desc = "outline", "生成故事大纲：mode=brief 摘要卡，mode=detail 详细大纲"
    schema = {"type": "object", "properties": {"mode": {"type": "string", "enum": ["brief", "detail"]}}, "required": ["mode"]}

    def run(self, ctx, mode="brief"):
        s, lock = ctx.spec.text(), ctx.get("outline_locked")
        if mode == "brief":
            p = f"写一份故事大纲摘要卡（约150字）：一句话立意 + 3~5条主线 + 主要人物 + 结局走向。\n规格：{s}\n硬约束：{lock}"
            ctx.set("outline_brief", r := self.ask(p, 0.8)); return r
        p = f"依据摘要卡展开详细大纲（分章，每章给出场景/冲突/情绪走向）。\n规格：{s}\n摘要卡：{ctx.get('outline_brief')}\n硬约束：{lock}"
        ctx.set("outline_detail", r := self.ask(p, 0.7)); return r
