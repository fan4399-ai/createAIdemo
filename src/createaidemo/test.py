# from crewai.utilities.paths import db_storage_path
# import os
#
# # 获取基础存储路径
# storage_path = db_storage_path()
# print(f"CrewAI 存储位置: {storage_path}")  # 打印存储路径
#
# # 列出所有 CrewAI 存储目录
# if os.path.exists(storage_path):
#     print("\n已存储的文件和目录:")
#     for item in os.listdir(storage_path):
#         item_path = os.path.join(storage_path, item)
#         if os.path.isdir(item_path):
#             print(f"📁 {item}/")
#             # 显示 ChromaDB 集合：如果目录内有内容，再列出其下一级
#             if os.path.exists(item_path):
#                 for subitem in os.listdir(item_path):
#                     print(f"   └── {subitem}")
#         else:
#             print(f"📄 {item}")
# else:
#     print("尚未找到 CrewAI 存储目录。")


# from crewai import Agent, Task, Crew
#
# # ==========================
# # 本地知识库读取
# # ==========================
# def get_knowledge_base():
#     try:
#         with open(r"C:\Users\Admin\createaidemo\knowledge\user_preference.txt", "r", encoding="utf-8") as f:
#             return f.read()
#     except:
#         return "未找到知识库内容"
#
# # ==========================
# # 创建带记忆的智能助手
# # ==========================
# assistant = Agent(
#     role="个人智能助手",
#     goal="根据用户的偏好文件回答问题，并且记住对话内容",
#     backstory="你是一个本地运行的智能助手，拥有记忆功能，严格依据知识库内容回答问题，不编造信息。",
#     verbose=True,
#     memory=True,  # 开启会话记忆
# )
#
# # ==========================
# # 任务1：加载知识库 + 确认信息
# # ==========================
# task1 = Task(
#     description=f"""
#     这是用户的个人偏好知识库内容：
#     ---
#     {get_knowledge_base()}
#     ---
#     请你记住这些内容，并回复：已成功加载个人知识库。
#     """,
#     agent=assistant,
#     expected_output="已成功加载个人知识库"
# )
#
# # ==========================
# # 任务2：测试记忆 + 知识库问答
# # ==========================
# task2 = Task(
#     description="""
#     请回答：
#     1. 我的偏好是什么？
#     2. 我刚刚让你记住了什么信息？
#     """,
#     agent=assistant,
#     expected_output="准确回答用户偏好与对话内容"
# )
#
# # ==========================
# # 启动运行
# # ==========================
# crew = Crew(
#     agents=[assistant],
#     tasks=[task1, task2],
#     verbose=1
# )
#
# # 运行
# result = crew.kickoff()
#
# # ==========================
# # 最终输出
# # ==========================
# print("\n" + "="*50)
# print("🤖 智能助手运行完成！")
# print("🧠 会话记忆：已开启")
# print("📚 知识库：已加载")
# print("✅ 状态：完全正常")
# print("="*50)
# print("\n【最终回答】：\n", result)


# ==========================
# 测试永久记忆功能
# ==========================
from crewai import Agent, Task, Crew
import json
import os
from tools import load_memory, save_memory, clear_memory

# ==========================
# 永久记忆配置
# ==========================
# 加载记忆（正确）
memory_data = load_memory()
user_info = str(memory_data)

print("="*50)
print("📂 读取到的记忆文件内容：")
print(user_info)
print("="*50)

# ==========================
# 智能助手（完全正确写法）
# ==========================
agent = Agent(
    role="本地记忆助手",
    goal="准确说出记住的用户信息",
    backstory="你完全使用本地文件记忆，不联网",
    verbose=True,
    memory=False,  # ✅ 这里只能是 True/False！！！
)

task = Task(
    description=f"""
    你记住的所有信息：
    {user_info}

    请清晰回答：你记住了什么？
    """,
    agent=agent,
    expected_output="完整复述所有记忆"
)

crew = Crew(agents=[agent], tasks=[task])
result = crew.kickoff()

print("\n【最终回答】:\n", result)