# src/createaidemo/tools/memory_tool.py
import json
import os

# 记忆文件路径
MEMORY_FILE = os.path.join(os.getcwd(), "user_memory.json")

def load_memory():
    """每次重启都会自动读取记忆"""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_memory(data):
    """保存记忆到本地文件"""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clear_memory():
    """一键清除记忆"""
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
        print("🗑️ 记忆已清空")