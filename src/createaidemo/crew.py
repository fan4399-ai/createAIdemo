import os

from .tools.ddg_search_tool import DDGSearchTool
from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from pathlib import Path

# 确保在类定义前加载环境变量
load_dotenv()


@CrewBase
class Createaidemo():
    """Createaidemo crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self):
        # 创建 DeepSeek LLM 实例（使用 OpenAI 兼容模式）
        self.llm = LLM(
            model=os.getenv("OPENAI_MODEL_NAME", "deepseek-chat"),
            base_url=os.getenv("OPENAI_API_BASE", "https://api.deepseek.com/v1"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.7,
            max_tokens=8000,
            # 单次 LLM 请求超时：防止某个调用永久挂起导致 cancel 后 CrewAI
            # 线程迟迟不结束、进程退出被卡住。超时后异常回到 step 边界，
            # 协作式取消即可生效。
            request_timeout=120,
        )
        self.search_tool = DDGSearchTool()  # 初始化

        # 获取项目根目录（根据你的目录结构调整）
        # 假设 crew.py 位于 src/createaidemo/ 下
        self.project_root = Path(__file__).parent.parent.parent
        self.output_file = self.project_root / "report.md"


    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['researcher'],  # type: ignore
            verbose=True,
            llm=self.llm,  # 使用 DeepSeek
            tools=[self.search_tool],  # 使用 DuckDuckGo 搜索

        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config['writer'],  # type: ignore
            verbose=True,
            llm=self.llm
        )

    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config['editor'],  # type: ignore
            verbose=True,
            llm=self.llm
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'],  # type: ignore
        )

    @task
    def writing_task(self) -> Task:
        return Task(
            config=self.tasks_config['writing_task'],  # type: ignore
        )

    @task
    def editing_task(self) -> Task:
        return Task(
            config=self.tasks_config['editing_task'],  # type: ignore
        )

    @crew
    def crew(self) -> Crew:
        """创建并返回 Crew 实例"""
        return Crew(
            agents=self.agents,   # 自动收集所有 @agent 装饰的方法
            tasks=self.tasks,     # 自动收集所有 @task 装饰的方法
            process=Process.sequential,
            verbose=True,
            memory=False,  # 彻底禁用记忆
        )