import time
import random
from crewai.tools import BaseTool
from ddgs import DDGS


class DDGSearchTool(BaseTool):
    name: str = "DuckDuckGo 搜索工具"
    description: str = "使用 DuckDuckGo 搜索网络信息（完全免费，无需 API Key）"

    def _run(self, query: str) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 随机延迟，避免被限流
                time.sleep(random.uniform(1, 3))
                with DDGS() as ddgs:
                    # 获取最多 5 条结果
                    results = list(ddgs.text(query, max_results=5))
                    if not results:
                        # 如果第一次没结果，尝试英文关键词
                        if attempt == 0:
                            continue
                        return "未找到相关信息。"

                    # 格式化输出
                    output = "\n".join([
                        f"• **{r['title']}**\n  {r['body']}\n  [来源: {r.get('href', '链接')}]"
                        for r in results
                    ])
                    return output
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"搜索失败（已重试 {max_retries} 次）: {str(e)}"
                time.sleep(random.uniform(2, 5))
        return "搜索失败，请稍后再试。"
