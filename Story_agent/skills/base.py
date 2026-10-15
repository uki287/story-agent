"""技能基类：所有技能继承它，统一 run 接口。"""


class Skill:
    """name/desc/schema 暴露给模型；run 是唯一执行入口。"""
    name, desc, schema = "", "", {}

    def __init__(self, llm): self.llm = llm

    def ask(self, prompt, t=0.7):
        """技能内部统一的一次大模型调用。"""
        return self.llm.chat([{"role": "user", "content": prompt}], temperature=t)

    def run(self, ctx, **kw): raise NotImplementedError
