"""编排层：Agent 核心循环（ReAct）+ 两道人在环审核门。

过程可视化：每步实时打印「思考 → 调用技能 → 结果」，让用户看得见智能体在做什么，
避免长时间空白等待（verbose=False 可整体关闭）。
"""
import json, re
from story_spec import parse_spec
from story_context import StoryContext
from story_prompt import SYSTEM_PROMPT


class StoryAgent:
    """系统唯一大脑：只做决策（路由技能 / 判定收敛 / 控制步数与预算），自己从不生成内容。"""

    def __init__(self, llm, skills, max_steps=12, threshold=75, gate_rounds=3, revise_rounds=3, auto=False, token_budget=60000, verbose=True):
        self.llm, self.skills, self.max_steps = llm, skills, max_steps
        self.threshold, self.rounds, self.auto, self.budget = threshold, gate_rounds, auto, token_budget
        self.revise_rounds = revise_rounds   # 终稿门最多修订几轮（与大纲门的 gate_rounds 分开控制）
        self.verbose = verbose

    def run(self, topic, req=""):
        """主流程：解析需求 → 核心循环 → 终稿审批门 → 交付。"""
        self._log("\n🔎 正在解析需求…")
        spec = parse_spec(self.llm, topic, req)
        self._log(f"📋 规格：题材={spec.genre}｜字数={spec.length}｜风格={spec.style}｜受众={spec.audience}｜基调={spec.tone}")
        ctx = StoryContext(spec)
        msgs = [{"role": "system", "content": SYSTEM_PROMPT.format(skills=json.dumps(self.skills.specs(), ensure_ascii=False), spec=spec.text())},
                {"role": "user", "content": f"请为主题《{spec.topic}》创作一篇短篇小说。"}]
        self._loop(ctx, msgs, self.max_steps, 0.4)
        return self._final_gate(ctx, msgs)

    def _loop(self, ctx, msgs, steps, temp):
        """ReAct 循环：思考 → 技能调用 → 观察回填；含步数上限与预算熔断。"""
        for i in range(1, steps + 1):
            self._log(f"\n──────── 步骤 {i}/{steps} ────────")
            self._log("💭 智能体思考中…")
            raw = self.llm.chat(msgs, temp); msgs.append({"role": "assistant", "content": raw})
            name, args = self._parse(raw)
            if th := self._thought(raw): self._log("🧠 思考：" + th)
            if not name: self._log("✅ 智能体表示已完成，准备交付。"); return          # 模型收尾
            self._log(f"🎯 调用技能：{name} {json.dumps(args, ensure_ascii=False)}")
            self._log("⏳ 技能执行中…")
            obs = self.skills.call(name, ctx, args)
            self._log("📊 结果：" + self._cut(obs))
            if name == "outline" and args.get("mode") == "brief" and not ctx.get("gate1_done"):
                self._outline_gate(ctx); ctx.set("gate1_done", True)
                obs += "｜摘要卡已通过用户验收，请调用 outline(mode=detail) 展开详细大纲。"
            msgs.append({"role": "user", "content": f"Observation: {obs}"})
            if self.llm.tokens > self.budget: self._log("⚠️ 已达 token 预算上限，提前收尾。"); return

    # ---------------- 过程输出 ----------------
    def _log(self, s):
        """统一的过程输出入口，flush 保证实时可见。"""
        if self.verbose: print(s, flush=True)

    @staticmethod
    def _cut(s, n=220):
        """把长文本压成一行并截断，便于在终端阅读。"""
        s = " ".join(str(s).split())
        return s if len(s) <= n else s[:n] + "…"

    @staticmethod
    def _thought(text):
        """从模型输出里抽出 Thought 段落（截断 200 字）。"""
        m = re.search(r"Thought\s*[:：]\s*(.*?)(?:\n\s*(?:Action|Final)\b|$)", text, re.S | re.I)
        return " ".join(m.group(1).split())[:200] if m else ""

    @staticmethod
    def _parse(text):
        """解析模型输出 → (技能名, 参数字典)；无技能名或 finish 即视为收尾。

        加固点：参数一律从「Action 那一行之后」去找第一个 JSON 对象，而不强求它必须
        写成 `Action Input: {...}`。模型常把参数换行另起、或漏掉 Input 一词，若用
        `Action Input:` 这种紧贴写法匹配，参数就会被整段丢弃，技能只能按默认值执行
        （outline 退回 brief、search 的 query 为空），而表面上流程照常跑完，很难排查。
        """
        m = re.search(r"Action\s*[:：]\s*(\w+)", text, re.I)
        if not m or m.group(1).lower() in ("finish", "final"): return None, {}
        a = re.search(r"\{.*\}", text[m.end():], re.S)          # 技能名之后的第一个 JSON 即参数
        if not a: return m.group(1), {}                                        # 确实没给参数：按空参执行
        try: return m.group(1), json.loads(a.group())
        except json.JSONDecodeError: return m.group(1), {}                     # 参数非法：交由技能容错

    def _outline_gate(self, ctx):
        """第一道门（两段式）：摘要卡验收，最多 rounds 轮，超限采用当前版本。"""
        self._log("\n🚪 大纲审批门（第 1 道 · 两段式）")
        for i in range(1, self.rounds + 1):
            self._log(f"\n—— 大纲摘要卡（第 {i} 次）——\n{ctx.get('outline_brief')}")
            if self.auto: self._log("（自动批准模式，直接通过）"); return
            ans = input("通过？(y=通过 / 其他内容=就地修改)：").strip()
            if ans.lower() in ("y", "yes", "通过"): self._log("✅ 摘要卡已通过。"); return
            self._log(f"✍️ 已记录修改意见：{ans}")
            ctx.set("outline_locked", (ctx.get("outline_locked") + "\n用户意见：" + ans).strip())
            self._log("🔁 正在按意见重生成摘要卡…")
            self.skills.call("outline", ctx, {"mode": "brief"})   # 回环重生成摘要卡
        self._log("（已达验收轮数上限，采用当前摘要卡）")

    def _final_gate(self, ctx, msgs):
        """第二道门：终稿审批。质量不达标或用户提意见时，回到循环修订并复检，直到达标或用完轮次。

        为什么要循环修订：原实现修订一轮后直接交付，既没重新评估、也没二次确认，
        等于「改完就当好了」。这里改为「修订 → 重新评估 → 复检」的闭环，并把
        revise_rounds 作为硬上限，防止模型在 draft 与 eval 之间反复打转烧 token。
        """
        for i in range(1, self.revise_rounds + 1):
            ev = ctx.get("eval") or {}
            score, ok = ev.get("score"), bool(ctx.get("draft")) and (ev.get("score") or 0) >= self.threshold
            self._log(f"\n🚪 终稿审批门（第 2 道）\n📊 质量评估：score={score}｜问题={ev.get('issues')}")
            if not ctx.get("draft"):
                self._log("❌ 工作台里没有正文，无法交付。"); break
            if ok: self._log(f"✅ 已达质量阈值 {self.threshold}。"); break
            self._log(f"⚠️ 未达质量阈值 {self.threshold}。" + ("（自动批准模式下仍继续修订）" if self.auto else ""))
            if self.auto:
                ans = "评分未达标，请依据 issues 修订正文"                    # 自动模式：以评估问题为修订意见
            else:
                ans = input("批准交付？(y=批准 / 其他内容=修改意见)：").strip()
                if ans.lower() in ("y", "yes", "批准", ""): self._log("👌 用户决定带问题交付。"); break
            self._log(f"🔁 第 {i}/{self.revise_rounds} 轮修订…")
            msgs.append({"role": "user", "content": f"用户修改意见：{ans}。请必须调用 draft 修订正文，并紧接着调用 eval 重新自查。"})
            before = (ctx.get("draft"), ev.get("score"))
            self._loop(ctx, msgs, 4, 0.5)
            # 修订是否真的生效：模型可能只回一句 finish 就收工，导致本轮白跑、分数纹丝不动。
            # 这里比对修订前后的正文与分数，连续两轮无变化就判定为「修不动了」，提前跳出，
            # 既避免空转烧 token，也避免把同一份稿子反复丢给用户确认。
            if i >= 2 and ((ctx.get("draft"), (ctx.get("eval") or {}).get("score")) == before):
                self._log("⛔ 连续两轮修订后正文与评分均无变化，判定为无法自动改进，停止修订。"); break
        else:
            self._log(f"（修订轮数已用尽 {self.revise_rounds} 轮，采用当前版本）")
        return self._assemble(ctx)

    def _assemble(self, ctx):
        """产出层：组装最终交付物。

        为什么加兜底：若循环因步数/预算上限提前终止、或模型漏调 draft，ctx 里就没有正文。
        原实现会输出一篇空白小说、并把「评估分：None」摆在结尾，用户无法判断是生成失败
        还是本来就空。这里在缺正文与缺评估时都给出明确说明，避免交付物看起来正常实则失败。
        """
        ev, draft = ctx.get("eval") or {}, ctx.get("draft")
        if not draft:
            return f"《{ctx.spec.topic}》\n\n⚠️ 未生成正文：智能体在步数或预算上限内未完成撰写环节，请重试或放宽 max_steps。"
        score = ev.get("score")
        tail = f"风格：{ctx.spec.style}｜目标字数：{ctx.spec.length}｜评估分：{score}" if score is not None \
            else f"风格：{ctx.spec.style}｜目标字数：{ctx.spec.length}｜评估分：未评估"
        return f"《{ctx.spec.topic}》\n\n{draft}\n\n———\n{tail}"
