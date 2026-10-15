"""素材技能：检索背景知识与细节。教学示例用模型知识充当知识库，生产环境换成真实检索 API 即可。"""
from .base import Skill


class SearchSkill(Skill):
    """检索创作所需的背景知识与细节素材。"""
    name, desc = "search", "检索创作所需的背景知识与细节素材"
    schema = {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}

    def run(self, ctx, query=""):
        r = self.ask(f"围绕检索需求给出3~5条可直接用于写作的素材（素材点+细节）。\n需求：{query}\n规格：{ctx.spec.text()}", 0.6)
        ctx.set("materials", (ctx.get("materials") + "\n" + r).strip()); return r
