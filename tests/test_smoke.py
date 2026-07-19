"""冒烟测试：覆盖导出、用户画像解析与运行体初始化，不触发真实 LLM 调用。"""
import sys
from pathlib import Path

# 确保项目根目录与 src 布局可被导入
_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
for _p in (str(_ROOT), str(_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from api.crew_runner import CrewRunner  # noqa: E402
from createaidemo.export_utils import export_to_word  # noqa: E402


def test_export_to_word_returns_docx_bytes():
    md = (
        "# 测试标题\n\n"
        "正文含 **加粗** 与 *斜体* 以及 `代码`。\n\n"
        "| 指标 | 数值 |\n| --- | --- |\n| 增长率 | 12% |\n"
    )
    data = export_to_word(md, "测试报告")
    assert isinstance(data, bytes)
    assert len(data) > 0
    # .docx 本质是 ZIP 包，以 PK 头开头
    assert data[:2] == b"PK"


def test_load_profile_has_expected_keys():
    profile = CrewRunner.load_profile()
    assert isinstance(profile, dict)
    for key in ("name", "career", "expected_salary", "interest", "location", "raw"):
        assert key in profile


def test_crew_runner_initialization():
    runner = CrewRunner(topic="人工智能医疗")
    assert runner.session_id
    assert runner.topic == "人工智能医疗"
    assert runner.final_markdown is None
    assert runner.finished_at is None
