import os
import json
import sys
import subprocess
import tempfile
import numpy as np
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 配置一律来自环境变量，代码不写死任何服务商；缺配置就立刻报错，避免用错误的
# 地址或无权限的模型去请求后收到难以定位的报错。变量名沿用 MODEL 以与其他模块一致。
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
LLM_MODEL = os.getenv("MODEL")
for _name, _val in (("OPENAI_API_KEY", api_key), ("OPENAI_BASE_URL", base_url), ("MODEL", LLM_MODEL)):
    if not _val:
        raise ValueError(f"缺少环境变量 {_name}，请复制 .env.example 为 .env 并填入真实值")

client = OpenAI(api_key=api_key, base_url=base_url)

TASKS = [
    # ===== 原有基础任务（稳定通过）=====
    {
        "id": "task1",
        "spec": "写一个函数 add(a, b)，返回两数之和。",
        "test": """
def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
"""
    },
    {
        "id": "task2",
        "spec": "写一个函数 is_even(n)，如果 n 是偶数返回 True，否则 False。",
        "test": """
def test_is_even():
    assert is_even(2) == True
    assert is_even(3) == False
    assert is_even(0) == True
"""
    },
    {
        "id": "task3",
        "spec": "写一个函数 reverse_string(s)，返回字符串反转。",
        "test": """
def test_reverse():
    assert reverse_string("abc") == "cba"
    assert reverse_string("") == ""
"""
    },

    # ===== 新增陷阱任务（易触发反思）=====
    {
        "id": "task4_fact",
        "spec": "写一个函数 factorial(n)，返回 n 的阶乘。假设 n >= 0。",
        "test": """
def test_fact():
    assert factorial(0) == 1
    assert factorial(5) == 120
    assert factorial(1) == 1
"""
    },
    {
        "id": "task5_palindrome",
        "spec": "写一个函数 is_palindrome(s)，判断字符串是否为回文（忽略非字母数字及大小写，但测试仅用纯小写字母）。",
        "test": """
def test_pal():
    assert is_palindrome("aba") == True
    assert is_palindrome("ab") == False
    assert is_palindrome("a") == True
    assert is_palindrome("aa") == True
"""
    },
    {
        "id": "task6_prime",
        "spec": "写一个函数 is_prime(n)，如果 n 是质数返回 True，否则 False。注意边界（1不是质数，2是质数）。",
        "test": """
def test_prime():
    assert is_prime(2) == True
    assert is_prime(1) == False
    assert is_prime(9) == False
    assert is_prime(97) == True
    assert is_prime(0) == False
"""
    },
    {
        "id": "task7_count_vowels",
        "spec": "写一个函数 count_vowels(s)，返回字符串中元音字母(a,e,i,o,u)的数量（小写即可）。",
        "test": """
def test_vowels():
    assert count_vowels("hello") == 2
    assert count_vowels("xyz") == 0
    assert count_vowels("aeiou") == 5
"""
    },
    {
        "id": "task8_max_of_three",
        "spec": "写一个函数 max_of_three(a, b, c)，返回三个数中的最大值。",
        "test": """
def test_max():
    assert max_of_three(1, 2, 3) == 3
    assert max_of_three(5, 2, 4) == 5
    assert max_of_three(-1, -2, -3) == -1
"""
    },
    {
        "id": "task9_remove_duplicates",
        "spec": "写一个函数 remove_duplicates(lst)，返回去重后的列表，且保持原有顺序。",
        "test": """
def test_dup():
    assert remove_duplicates([1, 2, 2, 3, 1]) == [1, 2, 3]
    assert remove_duplicates([]) == []
    assert remove_duplicates([5, 5, 5]) == [5]
"""
    },
    {
        "id": "task10_fib",
        "spec": "写一个函数 fib(n)，返回第 n 个斐波那契数（n从0开始，fib(0)=0, fib(1)=1）。",
        "test": """
def test_fib():
    assert fib(0) == 0
    assert fib(1) == 1
    assert fib(5) == 5
    assert fib(10) == 55
"""
    },
    {
        "id": "task11_capitalize_words",
        "spec": "写一个函数 capitalize_words(s)，将字符串中每个单词首字母大写，其余小写。",
        "test": """
def test_cap():
    assert capitalize_words("hello world") == "Hello World"
    assert capitalize_words("a") == "A"
    assert capitalize_words("") == ""
"""
    },
    {
        "id": "task12_sum_evens",
        "spec": "写一个函数 sum_evens(n)，返回从 0 到 n（包含）之间所有偶数的和。",
        "test": """
def test_sum_evens():
    assert sum_evens(5) == 6  # 0+2+4
    assert sum_evens(0) == 0
    assert sum_evens(2) == 2
"""
    },
    {
        "id": "task13_longest_word",
        "spec": "写一个函数 longest_word(s)，返回字符串中最长的单词（假设空格分隔，只返回第一个最长）。",
        "test": """
def test_longest():
    assert longest_word("I love programming") == "programming"
    assert longest_word("a bb ccc") == "ccc"
    assert longest_word("same same") == "same"
"""
    }
]

class CoderAgent:
    # ✅ 修复1：补充构造函数
    def __init__(self, use_reflection=True):
        self.use_reflection = use_reflection
        self.episodic_memory = []  # 情景记忆

    def _llm(self, prompt, messages=None):
        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        elif isinstance(prompt, str):
            messages = messages + [{"role": "user", "content": prompt}]
        r = client.chat.completions.create(
            model=LLM_MODEL, messages=messages, temperature=0.2
        )
        return r.choices[0].message.content

    def generate_initial(self, spec):
        return self._llm(f"根据规格写出python函数(只输出代码，不要解释)：\n{spec}")

    def reflect(self, spec, code, test_out):
        mem = "\n".join(
            [f"历史尝试:\n{c}\n失败:\n{o}" for c, o, _ in self.episodic_memory[-3:]]
        )
        prompt = f"""你是一个自我改进的编码者。根据规格、当前代码、测试失败，输出简短反思(错误原因+修正方向)，不要重复全量代码。
                    规格：{spec}
                    当前代码：
                    {code}
                    测试输出：
                    {test_out}
                    {mem}
                    反思："""
        return self._llm(prompt)

    def refine(self, spec, code, test_out):
        refl = self.reflect(spec, code, test_out)
        self.episodic_memory.append((code, test_out, refl))
        if not self.use_reflection:
            # ✅ 修复2：盲目重试也要 return
            prompt = f"重写Python函数(只输出函数，不要解释)：\n{spec}"
            return self._llm(prompt), None
        # 带反思重试
        prompt = f"""根据规格、历史尝试与反思，重写完整函数代码(只输出代码，无解释):
                    规格：{spec}
                    上次代码：
                    {code}
                    失败输出：
                    {test_out}
                    反思：{refl}
                    历史记忆：{self.episodic_memory[-3:]}"""
        return self._llm(prompt), refl  # ✅ 修复3：函数末尾兜底返回

    def run_test(self, code, test_code):
        full = code + "\n" + test_code
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(full)
            path = f.name
        try:
            # ✅ 修复4：capture_ouyput -> capture_output
            res = subprocess.run([sys.executable, path],
                                 capture_output=True, text=True, timeout=10)
            return res.returncode == 0, res.stdout + res.stderr
        except Exception as e:
            return False, str(e)
        finally:
            os.unlink(path)

    def solve(self, spec, test, max_steps=3):
        code = self.generate_initial(spec)
        tokens = 0
        for step in range(max_steps):
            ok, out = self.run_test(code, test)
            tokens += len(code.split()) + len(out.split())
            if ok:
                return True, code, step + 1, tokens
            if self.use_reflection:
                code, _ = self.refine(spec, code, out)
            else:
                code = self._llm(f"重写(盲目，只输出代码)：\n{spec}")
        return False, code, max_steps, tokens


def evaluate():
    seeds = [42, 123, 999]
    results = []
    for task in TASKS:
        for seed in seeds:
            np.random.seed(seed)
            agent_r = CoderAgent(use_reflection=True)
            ok_r, _, steps_r, tok_r = agent_r.solve(task["spec"], task["test"])
            agent_b = CoderAgent(use_reflection=False)
            ok_b, _, steps_b, tok_b = agent_b.solve(task["spec"], task["test"])

            results.append({
                "task": task["id"], "seed": seed,
                "reflection_pass": ok_r, "blind_pass": ok_b,
                "reflection_steps": steps_r, "blind_steps": steps_b,
                "reflection_tokens": tok_r, "blind_tokens": tok_b  # ✅ 修复5：tikens -> tokens
            })
            print(f"{task['id']} seed={seed} | 反思: {'OK' if ok_r else 'FAIL'}({steps_r}步) | "
                  f"盲目: {'OK' if ok_b else 'FAIL'}({steps_b}步)")

    total = len(results)
    pass1_r = sum(1 for r in results if r["reflection_steps"] == 1 and r["reflection_pass"])
    pass3_r = sum(1 for r in results if r["reflection_pass"])
    pass1_b = sum(1 for r in results if r["blind_steps"] == 1 and r["blind_pass"])
    pass3_b = sum(1 for r in results if r["blind_pass"])

    print("\n=== 评估汇总 ===")
    print(f"反思: pass@1={pass1_r/total:.2f}, pass^3={pass3_r/total:.2f}")
    print(f"盲目: pass@1={pass1_b/total:.2f}, pass^3={pass3_b/total:.2f}")
    print(f"平均Token(反思)={np.mean([r['reflection_tokens'] for r in results]):.0f}, "
          f"盲目={np.mean([r['blind_tokens'] for r in results]):.0f}")

    with open("eval_results.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    evaluate()