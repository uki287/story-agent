"""技能注册表：注册技能、向模型暴露 schema、执行技能调用。"""
from .outline import OutlineSkill
from .search import SearchSkill
from .character import CharacterSkill
from .style import StyleSkill
from .draft import DraftSkill
from .eval import EvalSkill

# 技能清单：Agent 启动时按此顺序全部注册
ALL_SKILLS = [OutlineSkill, SearchSkill, CharacterSkill, StyleSkill, DraftSkill, EvalSkill]


class SkillRegistry:
    """技能注册表：注册技能、向模型暴露 schema、执行技能调用。"""
    def __init__(self, llm): self.llm, self._s = llm, {}

    def add(self, cls): self._s[cls.name] = cls(self.llm)

    def specs(self):
        """导出给模型看的技能清单。"""
        return [{"name": k, "description": v.desc, "parameters": v.schema} for k, v in self._s.items()]

    def call(self, name, ctx, args=None):
        """执行一次技能调用；异常不抛出，转成文本让模型自纠。"""
        if name not in self._s: return f"技能 {name} 不存在，可用技能：{list(self._s)}"
        try: return self._s[name].run(ctx, **(args or {}))
        except Exception as e: return f"技能执行出错：{e}"
