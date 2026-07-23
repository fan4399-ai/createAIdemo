"""封装现有 Createaidemo Crew，提供带实时进度事件的报告生成能力。

设计要点：
- 复用 `createaidemo.crew.Createaidemo`，不修改其既有逻辑。
- 通过 Crew 的 `task_callback` 钩子把「研究 / 撰写 / 编辑」各阶段事件
  推入线程安全的 `queue.Queue`，供 FastAPI 的 SSE 端点消费。
- `kickoff()` 为同步阻塞调用，由上层用 `asyncio.to_thread` 包裹，
  事件队列跨线程传递进度。
"""
import json
import queue
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# 将 src 布局的包加入导入路径，使 `import createaidemo` 可用
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from createaidemo.crew import Createaidemo  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_FILE = PROJECT_ROOT / "knowledge" / "user_preference.txt"

DEFAULT_TOPIC = "AI人工智能agent"

# 三个阶段的顺序与中文标签，用于进度时间线
STAGE_ORDER = ["research", "writing", "editing"]
STAGE_LABELS = {"research": "研究", "writing": "撰写", "editing": "编辑"}

# CrewAI TaskOutput.name（由 @task 方法名决定）到阶段的映射
TASK_TO_STAGE = {
    "research_task": "research",
    "writing_task": "writing",
    "editing_task": "editing",
}


class _CancelSignal(Exception):
    """在 step_callback 中抛出，用于协作式中断 CrewAI 的 kickoff。"""


class CrewRunner:
    """一次报告生成的运行体，拥有独立的 session 与事件队列。"""

    def __init__(self, topic: str = DEFAULT_TOPIC, user_preference: str | None = None):
        self.session_id = uuid.uuid4().hex
        self.topic = topic
        self.user_preference = user_preference
        # 线程安全的事件队列（跨线程由 asyncio.to_thread 消费）
        self.events: "queue.Queue[dict]" = queue.Queue()
        self.final_markdown: str | None = None
        self.error: str | None = None
        self.finished_at: float | None = None  # 生成完成（成功或失败）的时间戳
        self.cancelled: bool = False  # 是否已被请求取消
        self._stage_index = 0

    # ---------- 事件推送 ----------
    def _emit(self, event: dict) -> None:
        self.events.put(event)

    # ---------- 取消 ----------
    def cancel(self) -> None:
        """请求取消本次生成；真正的终止发生在下一个 step 边界。"""
        self.cancelled = True

    def _check_cancel(self, step_output=None) -> None:
        """作为 Crew 的 step_callback：若已请求取消则抛出信号中断 kickoff。"""
        if self.cancelled:
            raise _CancelSignal()

    def _on_task(self, task_output) -> None:
        """CrewAI 每个 Task 完成后回调，发射阶段完成事件与日志片段。"""
        name = getattr(task_output, "name", None)
        stage = TASK_TO_STAGE.get(name) if name else None
        if stage is None:
            # 兜底：按执行顺序推断
            stage = (
                STAGE_ORDER[self._stage_index]
                if self._stage_index < len(STAGE_ORDER)
                else None
            )

        if stage:
            label = STAGE_LABELS.get(stage, stage)
            self._emit(
                {
                    "type": "stage",
                    "stage": stage,
                    "status": "done",
                    "message": f"{label}阶段完成",
                }
            )
            self._stage_index += 1
            if self._stage_index < len(STAGE_ORDER):
                nxt = STAGE_ORDER[self._stage_index]
                self._emit(
                    {
                        "type": "stage",
                        "stage": nxt,
                        "status": "running",
                        "message": f"{STAGE_LABELS.get(nxt, nxt)}阶段进行中…",
                    }
                )

        raw = getattr(task_output, "raw", "") or ""
        snippet = " ".join(raw.split())[:160]
        self._emit(
            {
                "type": "log",
                "stage": stage,
                "message": f"[{STAGE_LABELS.get(stage, stage or '?')}] {snippet}",
            }
        )

    # ---------- 主流程 ----------
    def _run(self) -> None:
        try:
            # 优先使用前端传入的偏好；未传则回退到 knowledge 文件
            if self.user_preference is not None:
                user_pref = self.user_preference.strip()
            else:
                try:
                    user_pref = KNOWLEDGE_FILE.read_text(encoding="utf-8").strip()
                except FileNotFoundError:
                    user_pref = "未提供用户偏好。"

            inputs = {
                "topic": self.topic,
                "user_preference": user_pref,
                "current_year": str(datetime.now().year),
            }

            # 初始阶段：研究进行中
            self._emit(
                {
                    "type": "stage",
                    "stage": "research",
                    "status": "running",
                    "message": "研究阶段进行中…",
                }
            )
            self._emit({"type": "log", "message": "已加载用户偏好，正在启动 Crew…"})

            crew_instance = Createaidemo()
            c = crew_instance.crew()
            c.task_callback = self._on_task
            # 协作式取消：每个 step 后检查取消标志，命中即抛异常中断 kickoff
            c.step_callback = self._check_cancel

            result = c.kickoff(inputs=inputs)
            if self.cancelled:
                self._emit({"type": "cancelled", "message": "已取消生成"})
                return
            markdown = result.raw if hasattr(result, "raw") else str(result)
            self.final_markdown = markdown

            self._emit(
                {
                    "type": "done",
                    "stage": "editing",
                    "status": "done",
                    "message": "报告生成完成",
                    "markdown": markdown,
                }
            )
        except _CancelSignal:
            # 由 step_callback 抛出，已在 cancel() 中置位；收尾即可
            self._emit({"type": "cancelled", "message": "已取消生成"})
            return
        except Exception as e:  # noqa: BLE001
            if self.cancelled:
                self._emit({"type": "cancelled", "message": "已取消生成"})
                return
            self.error = str(e)
            self._emit({"type": "error", "message": f"生成失败：{e}"})
        finally:
            self.finished_at = time.time()

    # ---------- 用户画像（供前端 Hero 展示） ----------
    @staticmethod
    def load_profile() -> dict:
        """解析 knowledge/user_preference.txt 中的用户画像。"""
        profile = {
            "name": "",
            "career": "",
            "expected_salary": "",
            "interest": "",
            "location": "",
            "raw": "",
        }
        try:
            text = KNOWLEDGE_FILE.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return profile
        profile["raw"] = text
        mapping = {
            "用户姓名": "name",
            "用户职业": "career",
            "用户期望薪资": "expected_salary",
            "用户兴趣": "interest",
            "用户所在地": "location",
        }
        for line in text.splitlines():
            line = line.strip()
            # 兼容全角（：）与半角（:）冒号，避免画像静默失效
            sep = "：" if "：" in line else (":" if ":" in line else None)
            if not line or sep is None:
                continue
            key, _, value = line.partition(sep)
            field = mapping.get(key.strip())
            if field:
                profile[field] = value.strip()
        return profile
