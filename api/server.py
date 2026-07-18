"""FastAPI 服务：暴露报告生成 / SSE 进度 / 导出 接口。

启动方式（项目根目录）：
    uv run uvicorn api.server:app --reload --port 8000

接口约定：
- POST /api/generate                 -> {"session_id": "..."}，后台启动 Crew
- GET  /api/generate/stream?session= -> SSE 推送进度与最终 Markdown
- GET  /api/profile                  -> 用户画像（用于前端 Hero 展示）
- POST /api/export/word              -> body {"markdown","title"} 返回 .docx
- GET  /api/export/markdown?session= -> 返回 .md 文本下载
"""
import asyncio
import json
import os
import queue
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .crew_runner import CrewRunner

# 项目根目录（api/ 的上一级）
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DIST_DIR = os.path.join(_BASE_DIR, "web", "dist")

app = FastAPI(title="AI Agent 行业报告生成器 API", version="0.1.0")

# 开发期允许前端 dev 端口跨域；生产可收紧为具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# session_id -> CrewRunner（含事件队列与最终 Markdown）
SESSIONS: Dict[str, CrewRunner] = {}
MAX_SESSIONS = 50  # 简单上限，防止内存无限增长


def _sse(event: dict) -> str:
    """把事件字典序列化为一条 SSE data 帧。"""
    data = json.dumps(event, ensure_ascii=False)
    return f"data: {data}\n\n"


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/profile")
async def profile():
    """返回用户画像，供前端展示当前生成所基于的身份信息。"""
    return CrewRunner.load_profile()


@app.post("/api/generate")
async def generate(topic: str | None = None):
    """启动一次报告生成，立即返回 session_id；进度通过 SSE 获取。"""
    # 清理过旧会话，控制内存
    if len(SESSIONS) >= MAX_SESSIONS:
        oldest = next(iter(SESSIONS))
        SESSIONS.pop(oldest, None)

    runner = CrewRunner(topic=topic) if topic else CrewRunner()
    SESSIONS[runner.session_id] = runner
    # 在后台线程运行同步的 CrewAI kickoff，不阻塞事件循环
    asyncio.create_task(asyncio.to_thread(runner._run))
    return {"session_id": runner.session_id}


@app.get("/api/generate/stream")
async def stream(session: str):
    """SSE 端点：持续推送该 session 的阶段/日志/完成事件。"""
    runner = SESSIONS.get(session)
    if not runner:
        raise HTTPException(status_code=404, detail="session not found")

    q: "queue.Queue[dict]" = runner.events

    async def event_gen():
        yield _sse({"type": "connected", "session": session, "message": "已连接进度流"})
        while True:
            try:
                event = await asyncio.to_thread(q.get, timeout=1.0)
            except queue.Empty:
                # 心跳保活，避免代理/浏览器超时断开
                yield ": keepalive\n\n"
                # 兜底：若队列已空但生成已结束（done 事件被漏读），则退出
                if runner.final_markdown is not None or runner.error is not None:
                    break
                continue

            yield _sse(event)
            if event.get("type") in ("done", "error"):
                break

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/export/word")
async def export_word(payload: dict):
    """复用 export_utils.export_to_word 将 Markdown 导出为 .docx。"""
    markdown = payload.get("markdown", "")
    title = payload.get("title", "报告")
    if not markdown:
        raise HTTPException(status_code=400, detail="markdown 为空")

    from createaidemo.export_utils import export_to_word

    docx_bytes = export_to_word(markdown, title)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{title}.docx"'},
    )


@app.get("/api/export/markdown")
async def export_markdown(session: str, title: str = "report"):
    """导出指定 session 的最终 Markdown 为 .md 文件。"""
    runner = SESSIONS.get(session)
    markdown = runner.final_markdown if runner else None
    if not markdown:
        raise HTTPException(status_code=404, detail="未找到该会话的报告内容")
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{title}.md"'},
    )


@app.get("/favicon.ico")
async def favicon():
    """避免浏览器请求 favicon 时产生 404 噪声。"""
    return Response(status_code=204)


# ---- 托管前端构建产物（可选）----
# 若已执行 `cd web && npm run build`，则 / 直接返回页面，无需单独跑 dev server。
# 注意：必须在所有 /api 路由之后挂载，API 路由优先匹配。
if os.path.isdir(_DIST_DIR):
    @app.get("/")
    async def index():
        return Response(
            content=open(os.path.join(_DIST_DIR, "index.html"), encoding="utf-8").read(),
            media_type="text/html; charset=utf-8",
        )

    # 挂载静态资源（js/css/图片等）；html=True 让未知路径回退到 index.html
    app.mount("/", StaticFiles(directory=_DIST_DIR, html=True), name="static")
