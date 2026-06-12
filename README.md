# 行业研究助手 — 基于 CrewAI 的多 Agent 协作系统

> 输入一个行业名称，4 个 AI Agent 自动协作：**联网搜索 → 分析洞察 → 撰写报告 → 审核修订**。
> 一键生成 Word / PDF / Markdown 专业行业研究报告。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![CrewAI](https://img.shields.io/badge/CrewAI-1.14+-green.svg)](https://crewai.com/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-purple.svg)](https://deepseek.com/)
[![Bocha](https://img.shields.io/badge/Search-博查-orange.svg)](https://bochaai.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 演示

```bash
$ python main.py "具身智能机器人" --format docx

[1/5] 初始化 Agent 团队...
   Researcher : 行业研究员
   Analyst    : 行业分析师
   Writer     : 报告撰写专家
   Reviewer   : 首席编辑（质量守门员）

[4/5] 开始执行研究 Pipeline...
   Researcher 调用 web_search 16+ 次，搜索互联网实时信息
   搜索来源: Omdia · 麦肯锡 · 东吴证券 · 政府工作报告 · 远瞻慧库
   Analyst 提炼 4 大趋势、识别 5 个机会与 3 个风险
   Writer 撰写 9 章完整报告
   Reviewer 发现数据引用不一致问题并修订

[5/5] 保存报告...
   ✅ DOCX: output/具身智能机器人_20260612_212707.docx  (44.5 KB)
   ✅ MD:   output/具身智能机器人_20260612_212707.md
   🧠 记忆已存储（可随时搜索历史报告）
```

---

## 架构

```
用户输入: "AI芯片"
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│                     CrewAI 编排引擎                           │
│                                                              │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌──────────┐  │
│  │ Researcher │──▶│  Analyst  │──▶│   Writer  │──▶│ Reviewer │  │
│  │  行业研究员 │   │ 行业分析师 │   │报告撰写专家│   │ 质量守门员│  │
│  │            │   │           │   │           │   │          │  │
│  │ 调用博查搜索 │   │ MECE分析  │   │ 9章报告   │   │5维20项审核│  │
│  └─────┬──────┘   └─────┬─────┘   └─────┬─────┘   └────┬─────┘  │
│        │ context         │ context       │ context       │        │
│        ▼                 ▼               ▼               ▼        │
│   互联网实时信息 ────▶ 结构化分析 ────▶ Markdown报告 ──▶ 修订版  │
│                                                              │
│                          ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  导出: Markdown · Word (.docx) · HTML · PDF          │   │
│  │  记忆: ChromaDB 向量存储 · 语义搜索 · 历史回溯        │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 特性

### Agent 协作
- **4 Agent 流水线**：Researcher → Analyst → Writer → Reviewer，各司其职
- **ReAct 循环**：Agent 自主决策何时搜索、搜索什么、是否需要再次搜索
- **Context 自动传递**：CrewAI `context` 机制，Task 间数据自动流转，无需手动拼接

### 联网搜索
- **博查搜索引擎**：国产搜索 API，中文搜索质量优异
- **免费额度**：注册即送 1000 次免费搜索，无需海外信用卡
- **实时信息**：Agent 可搜索互联网获取最新行业数据、政策文件、企业动态
- **降级策略**：未配置搜索 Key 时自动切换为知识库模式，系统不中断

### 报告导出
- **Markdown** (.md) — 原始格式，适合在线预览和版本管理
- **Word** (.docx) — ★ 推荐，适合提交、打印、编辑
- **HTML** (.html) — 浏览器打开，可直接打印为 PDF
- **PDF** (.pdf) — 适合正式交付，不可修改
- **一键全格式**：`--format all` 同时生成以上所有格式
- **GUI 弹窗**：双击运行后弹出可视化格式选择框

### 记忆持久化
- **ChromaDB 向量存储**：每次研究报告自动存入向量数据库
- **语义搜索**：`python main.py --history "市场规模"` 搜索所有历史报告
- **历史列表**：`python main.py --list` 列出所有过往研究
- **智能去重**：新研究前自动检索是否有相似历史报告可参考

### 质量审核
- **5 维度评分**：逻辑一致性 | 信息完整性 | 数据准确性 | 表达质量 | 格式规范
- **20 项清单**：逐项检查，每项 1-5 分，给出总评和交付建议
- **自动修订**：发现的所有问题均在最终报告中修正

---

## 项目结构

```
industry-research-crew/
├── main.py                       # 入口：一键运行 + CLI + GUI
├── README.md                     # 项目文档
├── requirements.txt              # 依赖清单
├── .gitignore                    # Git 忽略规则（保护 API Key）
├── .env.example                  # 配置模板（不含真实 Key）
│
├── config/
│   └── settings.py               # LLM 实例 · 路径常量 · 3级env回退
│
├── agents/                       # 4 个 AI Agent
│   ├── researcher.py             # 行业研究员 — 联网搜索 + 资料搜集
│   ├── analyst.py                # 行业分析师 — 趋势/竞争/机会/风险
│   ├── writer.py                 # 报告撰写专家 — 9 章 Markdown 报告
│   └── reviewer.py               # 首席编辑 — 5 维 20 项审核
│
├── tasks/                        # 4 个 Task（context 链）
│   ├── research_task.py          # Pipeline 起点，无 context
│   ├── analysis_task.py          # context=[research_task]
│   ├── writing_task.py           # context=[analysis_task]
│   └── review_task.py            # context=[writing_task]
│
├── tools/                        # Agent 工具
│   ├── search_tool.py            # Tavily 搜索工具（备选）
│   └── bocha_search_tool.py      # 博查搜索工具（★ 默认）
│
├── utils/                        # 工具模块
│   ├── exporter.py               # 报告导出：MD → DOCX / HTML / PDF
│   └── memory.py                 # ChromaDB 记忆库：存储 + 语义搜索
│
├── tests/                        # 测试套件
│   ├── test_researcher.py        # Researcher Agent 单元测试
│   ├── test_search_tool.py       # 搜索工具集成测试
│   ├── test_reviewer.py          # Reviewer 审核能力测试（6/6）
│   └── test_pipeline.py          # 完整 4 级 Pipeline 测试
│
└── output/                       # 报告产出
    ├── AI芯片_*.md               # Markdown 原稿
    ├── 具身智能机器人_*.docx     # Word 文档
    └── chroma_db/                # 向量数据库
```

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/zq15884603727zq-bit/industry-research-crew.git
cd industry-research-crew
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

```bash
# 复制配置模板
copy .env.example .env        # Windows
cp .env.example .env          # Mac / Linux
```

编辑 `.env`，填入你的 API Key：

```env
# 必填 — DeepSeek（注册即送额度）
DEEPSEEK_API_KEY=sk-你的key

# 推荐 — 博查搜索（微信扫码，免费1000次）
# 不填也能运行，Agent 会自动降级为知识库模式
BOCHA_API_KEY=sk-你的key
```

> **获取 Key 只需 2 分钟：**
> - DeepSeek：[platform.deepseek.com](https://platform.deepseek.com) → 注册 → API Key
> - 博查：[bochaai.com](https://bochaai.com) → 微信扫码 → API Key 管理 → 创建 → 领取免费资源包

### 4. 运行

```bash
# 基础研究
python main.py "AI芯片"

# 导出 Word 文档（★ 推荐）
python main.py "新能源汽车" -f docx

# 一键生成所有格式
python main.py "光伏产业" -f all

# 搜索历史报告
python main.py --history "市场规模"

# 列出所有历史
python main.py --list

# 双击 main.py 也行 → 输入主题 → GUI 弹窗选格式
```

---

## 完整 CLI 参考

```
python main.py [topic] [选项]

位置参数:
  topic                    研究主题

选项:
  -t, --topic TOPIC        研究主题（命名参数形式）
  -f, --format FORMAT      导出格式: md | docx | html | pdf | all（默认 md）
  -o, --output PATH        自定义输出文件路径
  -q, --quiet              减少详细日志输出
  --history QUERY          搜索历史报告（不执行新研究）
  --list                   列出所有历史报告
  -h, --help               显示帮助
```

---

## 工作原理

### Agent 协作流程

| 阶段 | Agent | 任务 | 工具 | 输出 |
|------|-------|------|------|------|
| 1 | Researcher | 搜索行业最新资料 | 博查 web_search | 结构化研究简报 |
| 2 | Analyst | 提炼趋势、竞争、机会、风险 | — | 结构化分析报告 |
| 3 | Writer | 撰写完整 Markdown 报告 | — | 9 章专业报告 |
| 4 | Reviewer | 逐项审核并修订 | — | 审核意见 + 修订版 |

### Context 传递机制

```python
# CrewAI 的 context 参数实现 Task 间数据自动流转
analysis_task = Task(..., context=[research_task])  # ← 接收研究资料
writing_task  = Task(..., context=[analysis_task])  # ← 接收分析报告
review_task   = Task(..., context=[writing_task])   # ← 接收报告初稿
```

### ReAct 循环（Tool Use）

```
Agent 推理: "我需要 具身智能 行业最新动态"
    → 输出 Action: web_search("具身智能 市场规模 2025")
    
CrewAI 拦截 → 调用博查 API → 返回 5 条真实搜索结果

Agent 观察结果: "Omdia 报告显示市场规模..."
    → 继续推理或再次搜索（实测 16+ 次真实搜索）
```

---

## 测试

```bash
python tests/test_researcher.py     # Researcher Agent 单元测试
python tests/test_search_tool.py    # 搜索工具集成测试
python tests/test_reviewer.py       # Reviewer 审核能力测试（6/6 错误命中）
python tests/test_pipeline.py       # 完整 4 级 Pipeline 测试
```

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| Agent 框架 | CrewAI 1.14+ | 多 Agent 编排 |
| LLM | DeepSeek Chat | 高性价比中文模型 |
| 搜索引擎 | **博查 (Bocha)** | 国产搜索 API，中文搜索优异，微信注册 |
| 向量数据库 | ChromaDB | 报告记忆持久化 + 语义搜索 |
| 文档生成 | python-docx / fpdf2 | Word + PDF 导出 |
| GUI | tkinter | Python 内置，格式选择弹窗 |
| 配置管理 | python-dotenv | 环境变量管理 |
| 数据验证 | Pydantic | 类型安全 |

---

## 设计亮点

| 设计点 | 说明 |
|--------|------|
| **工厂函数模式** | 所有 Agent 和 Task 通过工厂函数创建，支持动态参数注入 |
| **降级策略 × 2** | 搜索工具未配置 → 知识库模式；ChromaDB 嵌入失败 → 仅存元数据 |
| **3 级 env 回退** | export → find_dotenv → \_\_file\_\_，兼容命令行管道和双击运行 |
| **GUI + CLI 双模式** | 双击弹窗可视化操作，命令行支持完整参数 |
| **关注点分离** | Agent / Task / Tool / Utils 各司其职，高内聚低耦合 |
| **可测试性** | 每个模块有独立测试，Pipeline 有端到端测试，Reviewer 有植入错误测试 |

---

## 报告结构

生成的报告包含 9 个章节：

1. **封面** — 标题、日期、研究机构
2. **执行摘要** — 300 字核心发现
3. **行业概况** — 市场规模、增长驱动、发展阶段
4. **竞争格局** — 头部企业对比、市场份额、竞争态势
5. **技术分析** — 技术路线、创新热点、演进方向
6. **政策环境** — 监管框架、政策影响
7. **趋势与展望** — 1-3 年关键趋势预测
8. **机会与风险** — 投资/进入建议、风险矩阵
9. **附录** — 数据来源汇总、研究方法说明

---

## 实际搜索效果

以「具身智能机器人」为例，Agent 通过博查搜索到的真实来源包括：

| 来源 | 内容 |
|------|------|
| Omdia | 《通用具身机器人市场雷达报告》2026.1 |
| 麦肯锡 | 人形机器人行业报告 2026.5 |
| 东吴证券 | 《具身智能落地的关键》深度报告 |
| 国务院 | 2025 年《政府工作报告》（首次写入"具身智能"） |
| 远瞻慧库 | 《具身智能产业发展现状与趋势调研报告(2025)》 |
| 观研报告网 | 《中国机器人行业发展趋势分析与投资前景预测报告(2026-2033)》 |

---

## License

MIT
