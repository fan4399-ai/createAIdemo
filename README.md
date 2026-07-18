# AI Agent 行业报告生成器

基于 **CrewAI** 多智能体协作 + **FastAPI** 后端 + **Vue 3** 前端的可视化行业报告生成器。
输入一个行业主题，由「研究员 → 撰稿人 → 编辑」三个 Agent 依次协作，实时流式输出生成进度，最终产出一份 Markdown 行业报告，并支持一键导出 **Word (.docx)** 与 **Markdown (.md)**。

## ✨ 功能特性

- **多 Agent 协作**：研究员（联网检索）、撰稿人（成文）、编辑（润色定稿）串行流水线。
- **实时进度流**：通过 SSE（Server-Sent Events）把各阶段日志推送到前端「实时进度」面板。
- **用户画像驱动**：读取 `knowledge/user_preference.txt` 中的用户画像，让报告更贴合使用者背景。
- **可滚动报告窗口**：右侧报告区为固定高度、可滚动的渲染窗口，长报告不撑乱页面。
- **导出抽屉**：点击「导出报告」从右侧滑出抽屉，提供 Word / Markdown 两种导出方式，并带终端风格预览。
- **单进程托管**：构建前端后，FastAPI 直接托管 `web/dist`，只跑一个 uvicorn 即可同时访问页面与接口。

## 🧱 技术栈

| 层 | 技术 |
|----|------|
| 智能体框架 | [CrewAI](https://github.com/crewAIInc/crewAI) 1.11.0 |
| 大模型 | 通过 `crewai.LLM` 接入 OpenAI 兼容接口（默认 DeepSeek） |
| 后端 | FastAPI + Uvicorn + SSE |
| 前端 | Vue 3 + Vite + TypeScript + markdown-it |
| 导出 | python-docx（Word）、原生 Markdown |
| 向量/记忆 | lancedb（可选知识库） |

## 📁 目录结构

```
createaidemo/
├── api/                      # FastAPI 后端
│   ├── server.py            # 路由：生成 / SSE 进度 / 导出 / 托管前端
│   └── crew_runner.py       # Crew 运行封装（线程 + 事件队列）
├── src/createaidemo/        # CrewAI 智能体定义
│   ├── crew.py             # Researcher / Writer / Editor 三 Agent 流水线
│   ├── config/             # agents.yaml / tasks.yaml
│   ├── tools/              # 自定义工具（搜索、记忆等）
│   └── export_utils.py     # Markdown -> Word 导出
├── web/                     # Vue 3 前端
│   ├── src/                # App.vue / components / api.ts / styles
│   └── dist/               # 构建产物（由后端托管，已被 .gitignore 忽略）
├── knowledge/               # 用户画像等参考资料
├── pyproject.toml          # Python 依赖
└── .env                    # 密钥与模型配置（已被 .gitignore 忽略）
```

## 🔧 环境要求

- Python `>=3.10, <3.14`
- Node.js `>=18`（前端构建）
- 一个 OpenAI 兼容的大模型 API Key（默认使用 DeepSeek）

## 🚀 安装与配置

### 1. 后端依赖

推荐使用 `uv`（项目已用 `uv.lock` 锁定版本）：

```bash
# 安装 uv（如未安装）
pip install uv

# 在项目根目录安装全部依赖（含 ddgs、python-dotenv 等）
uv sync
```

> 本项目已自带 `crewai_env/` 虚拟环境。若依赖有变动，执行 `uv sync` 即可同步；日常运行直接用现有环境即可。

### 2. 配置 `.env`

在项目根目录创建 `.env` 文件（**不要提交到 git**），内容示例：

```ini
# 大模型（OpenAI 兼容接口，默认 DeepSeek）
OPENAI_API_KEY=你的_api_key
OPENAI_API_BASE=https://api.deepseek.com/v1
OPENAI_MODEL_NAME=deepseek-chat
```

### 3. 前端依赖

```bash
cd web
npm install
```

## ▶️ 运行

### 方式一：单进程（推荐）

1. 先构建前端：

   ```bash
   cd web && npm run build && cd ..
   ```

2. 启动后端（它会自动托管 `web/dist`，页面与接口同在 8000 端口）：

   ```bash
   crewai_env/Scripts/python.exe -m uvicorn api.server:app --port 8000
   # 或使用 uv：
   uv run uvicorn api.server:app --port 8000
   ```

3. 浏览器打开 `http://localhost:8000/`

### 方式二：前后端分离（开发热更新）

- 终端 A（后端）：`uv run uvicorn api.server:app --port 8000`
- 终端 B（前端）：`cd web && npm run dev`（默认 5173，已配置 `/api` 代理到 8000）

访问 `http://localhost:5173/`。

## 🔌 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/health` | 健康检查 |
| GET  | `/api/profile` | 返回用户画像（前端 Hero 展示） |
| POST | `/api/generate?topic=行业` | 启动一次生成，立即返回 `session_id` |
| GET  | `/api/generate/stream?session=xxx` | SSE 实时推送进度与最终 Markdown |
| POST | `/api/export/word` | body `{"markdown","title"}`，返回 `.docx` 下载 |
| GET  | `/api/export/markdown?session=xxx` | 返回 `.md` 下载 |

## 📦 导出说明

- **Word**：后端用 `python-docx` 把 Markdown 转换为 `.docx`，保留标题、段落、列表结构。
- **Markdown**：直接下载原始 `.md` 文本。
- 两种导出均在前端「导出报告」滑出抽屉中触发。

## 📝 使用流程

1. 打开页面，查看基于用户画像的欢迎信息。
2. 在主题输入框填写想研究的行业（如「人工智能医疗」），点击「开始生成报告」；留空则使用默认主题。
3. 左侧「实时进度」面板会流式显示各 Agent 的工作日志。
4. 右侧报告窗口渲染最终 Markdown 报告，超出高度可滚动查看。
5. 点击右上角「导出报告」，选择 Word 或 Markdown 下载。

## 📄 许可证

本项目仅供学习演示使用。
