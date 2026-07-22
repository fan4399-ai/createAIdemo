import random
import threading
import time
from crewai.tools import BaseTool
from ddgs import DDGS

# 模块级缓存：query -> (timestamp, formatted_result)，避免重复搜索与重复 sleep
_cache: dict[str, tuple[float, str]] = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 3600  # 缓存有效期（秒）：1 小时

# 单次搜索最大结果数
_MAX_RESULTS = 5
# 重试次数
_MAX_RETRIES = 3


class DDGSearchTool(BaseTool):
    name: str = "DuckDuckGo 搜索工具"
    description: str = "使用 DuckDuckGo 搜索网络信息（完全免费，无需 API Key）"

    def _run(self, query: str) -> str:
        query = (query or "").strip()
        if not query:
            return "未提供搜索关键词。"

        # 命中缓存则直接返回，省去网络请求与延迟
        with _cache_lock:
            hit = _cache.get(query)
            if hit and (time.time() - hit[0]) < _CACHE_TTL:
                return hit[1]

        last_err = ""
        for attempt in range(_MAX_RETRIES):
            try:
                # 首次仅短延迟；仅在重试时加长，整体提速并降低被限流概率
                delay = 0.3 if attempt == 0 else random.uniform(1.5, 3.0)
                time.sleep(delay)
                with DDGS() as ddgs:
                    # timeout 防止网络卡住时无限阻塞生成线程（在 to_thread 中运行）
                    results = list(ddgs.text(query, max_results=_MAX_RESULTS, timeout=10))

                if results:
                    output = "\n".join(
                        f"• **{r['title']}**\n  {r['body']}\n  [来源: {r.get('href', '链接')}]"
                        for r in results
                    )
                    with _cache_lock:
                        _cache[query] = (time.time(), output)
                    return output

                # 有返回但为空：重试一次（可能是临时空结果）
                if attempt < _MAX_RETRIES - 1:
                    continue
                return "未找到相关权威信息，请尝试更换关键词。"
            except Exception as e:  # noqa: BLE001
                last_err = str(e)
                # 重试前稍作等待，避免立即被限流
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(random.uniform(1.0, 2.0))

        # 全部失败：返回友好提示，让后续 Agent 基于已有知识撰写，而非产出空文本
        return f"搜索暂时不可用（{last_err}），报告将基于已有知识撰写。"
