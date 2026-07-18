#!/usr/bin/env python
import sys
import warnings

from datetime import datetime
from pathlib import Path
from createaidemo.crew import Createaidemo

# 忽略 pysbd 模块中的 SyntaxWarning 警告
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# 此主文件旨在让你在本地运行 crew，请勿在此文件中添加不必要的逻辑。
# 将 inputs 替换为你想要测试的输入，它会自动插值到所有任务和智能体中。

def run():
    """
    运行 crew
    """
    # 获取项目根目录（假设 main.py 在 src/createaidemo/ 下）
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent  # 根据实际层级调整
    knowledge_file = project_root / "knowledge" / "user_preference.txt"

    try:
        with open(knowledge_file, "r", encoding="utf-8") as f:
            user_pref = f.read().strip()
    except FileNotFoundError:
        user_pref = "未提供用户偏好。"

    # 定义输入变量，topic 和 current_year 会传递给 agents.yaml 和 tasks.yaml 中的占位符
    inputs = {
        'topic': 'AI人工智能agent',                # 主题，可替换为其他内容
        'user_preference': user_pref,
        'current_year': str(datetime.now().year)   # 当前年份，自动获取
    }
    try:
        # 实例化 Createaidemo crew 并启动执行
        Createaidemo().crew().kickoff(inputs=inputs)
    except Exception as e:
        # 捕获异常并抛出包含上下文信息的错误
        raise Exception(f"An error occurred while running the crew: {e}")
    print("用户偏好内容：", user_pref)

def train():
    """
    训练 crew，执行指定次数的迭代。
    用法: python main.py train <n_iterations> <filename>
    """
    inputs = {
        "topic": "AI LLMs",
        'current_year': str(datetime.now().year)
    }
    try:
        # 调用 crew 的 train 方法，传入迭代次数和输出文件名
        Createaidemo().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    从指定任务重放 crew 的执行过程。
    用法: python main.py replay <task_id>
    """
    try:
        # 调用 crew 的 replay 方法，传入任务 ID
        Createaidemo().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    测试 crew 的执行并返回结果。
    用法: python main.py test <n_iterations> <eval_llm>
    """
    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year)
    }

    try:
        # 调用 crew 的 test 方法，传入迭代次数和评估模型
        Createaidemo().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def run_with_trigger():
    """
    使用触发器负载运行 crew。
    用法: python main.py run_with_trigger '{"key": "value"}'
    """
    import json

    # 检查是否提供了触发器负载参数
    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        # 解析 JSON 格式的触发器负载
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    # 构建输入，将触发器负载传递给 crew
    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": "",        # 此处留空，实际由触发器提供
        "current_year": ""  # 此处留空，实际由触发器提供
    }

    try:
        # 执行 crew 并返回结果
        result = Createaidemo().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")

if __name__ == "__main__":
    run()

