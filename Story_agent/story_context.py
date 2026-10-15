"""记忆层：跨技能共享的创作工作台，保证长文一致。"""


class StoryContext:
    """所有技能读写同一份工作台。

    常用键：outline_brief（摘要卡）、outline_detail（详细大纲）、outline_locked（用户确认的硬约束）、
    materials、characters、style、draft、eval、issues。
    """

    def __init__(self, spec): self.spec, self.m = spec, {}
    def set(self, k, v): self.m[k] = v
    def get(self, k, d=""): return self.m.get(k, d)
