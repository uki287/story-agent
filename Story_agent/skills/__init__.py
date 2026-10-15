"""技能包：六个技能各占一个文件，统一放在本文件夹，便于单独阅读与测试。

用法：
    from skills import SkillRegistry, ALL_SKILLS
"""
from .base import Skill
from .outline import OutlineSkill
from .search import SearchSkill
from .character import CharacterSkill
from .style import StyleSkill
from .draft import DraftSkill
from .eval import EvalSkill
from .registry import SkillRegistry, ALL_SKILLS
