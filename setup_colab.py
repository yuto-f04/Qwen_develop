"""Colab 環境セットアップスクリプト。

Cell 1 の git pull/clone 直後に実行される。
sox・flash-attn など OS 依存ライブラリをインストールする。
"""
import subprocess
import sys


def install_sox():
    r = subprocess.run(
        ["apt-get", "install", "-y", "sox", "libsox-fmt-all"],
        capture_output=True, text=True,
    )
    status = "✅ インストール済み" if r.returncode == 0 else f"⚠️ 失敗: {r.stderr[-100:]}"
    print(f"sox: {status}")


def install_flash_attn():
    try:
        import torch

        if torch.version.cuda is None:
            print("flash-attn: ⚠️ GPU未接続のためスキップ"
                  "（ランタイム → ランタイムのタイプを変更 → GPU を選択してから再実行）")
            return

        # すでにインストール済みなら何もしない
        try:
            import flash_attn  # noqa: F401
            print(f"flash-attn: ✅ インストール済み（スキップ）")
            return
        except ImportError:
            pass

        cuda = torch.version.cuda.replace(".", "")[:3]
        tv = torch.__version__.split("+")[0]
        tv_mm = ".".join(tv.split(".")[:2])
        py = f"cp{sys.version_info.major}{sys.version_info.minor}"

        print(f"flash-attn: CUDA={torch.version.cuda}, PyTorch={tv}, Python={py}")

        # プリビルド wheel を試す（新しい順 × cxx11abi 両方）
        versions = [
            "2.7.4", "2.7.3", "2.7.2", "2.7.1",
            "2.6.3", "2.6.2", "2.6.1",
            "2.5.9.post1", "2.5.8", "2.5.7",
        ]
        for ver in versions:
            for cxx in ["FALSE", "TRUE"]:
                whl = (f"flash_attn-{ver}+cu{cuda}torch{tv_mm}"
                       f"cxx11abi{cxx}-{py}-{py}-linux_x86_64.whl")
                url = (f"https://github.com/Dao-AILab/flash-attention"
                       f"/releases/download/v{ver}/{whl}")
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-q", url],
                    capture_output=True, text=True,
                )
                if r.returncode == 0:
                    print(f"flash-attn: ✅ {ver} (cxx11abi{cxx}) インストール成功")
                    return

        # プリビルド wheel が見つからなかった場合はスキップ
        # ソースビルドは20〜30分かかるため採用しない
        print("flash-attn: ⚠️ 対応プリビルド wheel なし → スキップ")
        print(f"  （TTS は正常動作します。速度低下のみ）")
        print(f"  → CUDA={torch.version.cuda}, PyTorch={tv}, Python={py}")

    except Exception as e:
        print(f"flash-attn: ⚠️ エラー: {e}")


def install_quickjs():
    """yt-dlp の n challenge 解決用 JS ランタイムをインストールする。"""
    try:
        import quickjs  # noqa: F401
        print("quickjs: ✅ インストール済み（スキップ）")
        return
    except ImportError:
        pass
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "quickjs"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        print("quickjs: ✅ インストール成功")
    else:
        print(f"quickjs: ⚠️ インストール失敗: {r.stderr[-200:]}")


def install_demucs():
    """demucs を確認・インストールする。"""
    try:
        import demucs  # noqa: F401
        print("demucs: ✅ インストール済み（スキップ）")
        return
    except ImportError:
        pass
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "demucs"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        print("demucs: ✅ インストール成功")
    else:
        print(f"demucs: ❌ インストール失敗\n{r.stderr[-300:]}")


def install_qwen_tts():
    """qwen-tts を確認・インストールする。"""
    try:
        import qwen_tts  # noqa: F401
        print("qwen-tts: ✅ インストール済み（スキップ）")
        return
    except ImportError:
        pass

    print("qwen-tts: インストール中...")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "qwen-tts"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        print("qwen-tts: ✅ インストール成功")
    else:
        print(f"qwen-tts: ⚠️ pip install 失敗\n--- stdout ---\n{r.stdout[-500:]}\n--- stderr ---\n{r.stderr[-500:]}")
        print("qwen-tts: GitHub から直接インストールを試みます...")
        r2 = subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "git+https://github.com/QwenLM/Qwen3-TTS.git"],
            capture_output=True, text=True,
        )
        if r2.returncode == 0:
            print("qwen-tts: ✅ GitHub からインストール成功")
        else:
            print(f"qwen-tts: ❌ インストール失敗\n{r2.stderr[-500:]}")
            print("手動で以下を実行してください: pip install qwen-tts")


if __name__ == "__main__":
    install_sox()
    install_demucs()
    install_quickjs()
    install_qwen_tts()
    install_flash_attn()
