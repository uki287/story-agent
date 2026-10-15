"""入口：采集用户输入并启动短篇小说智能体。"""
from story_llm import LLM
from skills import SkillRegistry, ALL_SKILLS
from story_agent import StoryAgent

if __name__ == "__main__":
    llm = LLM()
    reg = SkillRegistry(llm)
    for cls in ALL_SKILLS: reg.add(cls)                 # 注册六个技能
    topic = input("主题：").strip() or "一只想飞的猫"
    req = input("要求（可留空）：").strip()
    auto = input("自动批准模式？(y/N)：").strip().lower() == "y"
    print("\n" + "=" * 60 + "\n" + StoryAgent(llm, reg, auto=auto).run(topic, req))
