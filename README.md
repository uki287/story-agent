# story-agent

从零手写的 **ReAct 智能体教学示例**，不依赖 LangChain，用「文本协议」（Thought / Action / Action Input）驱动大模型。

包含两个可运行的项目：

| 项目 | 入口 | 说明 |
|---|---|---|
| 短篇小说生成智能体 | `Story_agent/story_main.py` | 输入「主题 + 要求」，自动产出短篇小说（含双审核门、记忆层、质量门） |
| ReAct 基础示例 | `main.py` | 教学用的最小 ReAct 循环与反思式变体 |

后端通过 OpenAI 兼容协议接入，默认使用 DeepSeek（模型名 `deepseek-chat`）。

---

## 快速开始

### 1. 配置密钥

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

编辑 `.env` 填入真实密钥：

```ini
OPENAI_API_KEY=sk-你的密钥
OPENAI_BASE_URL=https://api.deepseek.com/v1
```

> `.env` 已被 `.gitignore` 排除，不会误提交。密钥若曾被提交过，务必在 GitHub 后台**吊销并重建**，改文件是不够的。

### 2. 安装依赖

```bash
pip install openai python-dotenv
```

### 3. 运行

```bash
# 短篇小说智能体
cd Story_agent
python story_main.py

# 基础 ReAct 示例
python main.py
```

运行 `story_main.py` 会依次询问：主题、补充要求、是否开启自动批准模式。

---

## 短篇小说智能体架构

```
交互层story_main.py      采集主题 / 要求 / 交互模式
   ↓
解析层    story_spec.py      自然语言 → StorySpec（题材/字数/风格/受众/基调）
   ↓
编排层    story_agent.py     ReAct 循环 + 双审核门（只决策，不生成内容）
   ↓
技能层    skills/            6 个技能，各占一个文件
   ↓
产出层    _assemble()        标题 + 正文 + 元数据
   ↕
记忆层    story_context.py   跨技能共享工作台，保证长文一致性
   ↕
公共层    story_llm.py       全项目唯一读取密钥的入口 + token 预算
```

### 六个技能

| 技能 | 职责 | 写入的键 |
|---|---|---|
| `outline` | 生成大纲：`brief` 摘要卡 / `detail` 详细大纲 | `outline_brief` / `outline_detail` |
| `search` | 检索背景知识与细节素材（教学版用模型知识充当检索） | `materials` |
| `character` | 设计人物卡片：身份 / 性格 / 动机 / 成长弧光 | `characters` |
| `style` | 制定风格指南：人称 / 句式 / 节奏 / 用词 | `style` |
| `draft` | 撰写或修订正文 | `draft` |
| `eval` | 五维各 20 分打分，输出结构化评估 | `eval` / `issues` |

### 三个关键设计

**1. Agent 只决策，不生成内容**
`StoryAgent` 仅负责路由技能、判定收敛、控制步数与预算。所有创作文本都出自技能层，这让编排逻辑可以被完整推理。

**2. 双审核门（人在环HITL）**

- **大纲门**：两段式。先出约 150 字摘要卡 → 用户验收 → 通过后才展开详细大纲。用户的修改意见写入 `outline_locked` 作为硬约束，后续每次生成都注入，防止「改了又忘」。最多 3 轮。
- **终稿门**：质量评估后审批。不达标或用户提意见则回到循环修订，并**复检**评分；连续两轮正文与评分均无变化则判定「修不动了」并停止，避免空转消耗 token。

**3. 失败不崩，转成文本让模型自纠**
技能异常被捕获后转成字符串回填给模型（`技能 xxx 不存在，可用技能：…`）。参数幻觉、JSON 解析失败都是常态，系统必须让模型自己纠回来。

### 终止保护

三重机制防止「评估 → 重写 → 再评估」无限循环烧钱：

- `max_steps=12` 步数硬上限
- `token_budget=60000` token 预算熔断
- 模型输出 `Action: finish` 主动收尾

---

## 目录结构

```
.
├── .env.example            环境变量模板（复制为 .env 使用）
├── main.py                 基础 ReAct 示例入口
├── agent.py                ReAct 循环实现
├── agent_test.py           原生 Function Calling 版本
├── agent_reflexion.py      反思式编码智能体
├── client.py / prompt.py / tools.py
└── Story_agent/            短篇小说生成智能体
    ├── story_main.py           入口
    ├── story_agent.py          ReAct 循环 + 双审核门
    ├── story_llm.py            统一大模型客户端（唯一读密钥处）
    ├── story_spec.py           需求解析 → StorySpec
    ├── story_context.py        记忆层共享工作台
    ├── story_prompt.py         系统提示词模板
    ├── skills/                 技能包（一技能一文件）
    │   ├── base.py             技能基类
    │   ├── registry.py         注册表与执行入口
    │   ├── outline.py search.py character.py
    │   └── style.py draft.py eval.py
    └── 短篇小说智能体_框架设计与分析.html    设计讲义（9 章）
```

---

## 说明

- `SearchSkill` 是**教学简化实现**，用模型内部知识充当检索。生产环境应替换为真实检索 API。
- 代码不含单元测试，设计讲义第 6 章列出了建议的测试策略。
- 密钥只应在 `story_llm.py` 中读取，其他模块不直接接触密钥。

### 常见问题：推送报`error setting certificate file`

报错形如：

```
fatal: unable to access 'https://github.com/...': error setting certificate file:
.../mingw64/etc/ssl/certs/ca-bundle.crt
```

这是本机 Git 安装缺少证书目录导致的，与网络或账号无关。可任选一种处理：

```bash
# 方案一：单次推送临时跳过校验
GIT_SSL_NO_VERIFY=true git push

# 方案二：全局关闭该校验（不推荐，仅限临时排障）
git config --global http.sslVerify false

# 方案三（推荐）：补装 Git for Windows 官方完整版，
#   或在Git 安装目录下找到 ca-bundle.crt 并放到 mingw64/etc/ssl/certs/
```

长期建议用方案三恢复证书校验。