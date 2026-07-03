"""app.py が GPU 依存ライブラリなしでインポートできることを確認するテスト。

実際の Gradio UI の動作確認は Colab 上で行う。
"""
import sys
from unittest.mock import MagicMock


def test_app_has_demo_attribute():
    """gradio をモック化して app.py をインポートし、demo 属性が存在することを検証する。"""
    mock_gr = MagicMock()

    # 既にキャッシュされていれば削除
    sys.modules.pop("app", None)

    with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
        sys.modules, {"gradio": mock_gr}
    ):
        import app  # noqa: F401
        assert hasattr(app, "demo"), "app.py は demo 属性を持つ必要があります"

    sys.modules.pop("app", None)
