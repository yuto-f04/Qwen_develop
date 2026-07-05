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

        # フォールバック: ソースビルド（数分かかる）
        print("flash-attn: プリビルド wheel が見つからないためソースビルドします（数分かかります）...")
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "packaging", "ninja", "-q"],
            capture_output=True, text=True,
        )
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "flash-attn==2.6.3", "--no-build-isolation", "-q"],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            print("flash-attn: ✅ ソースビルド成功")
        else:
            print("flash-attn: ⚠️ インストール失敗（TTS は正常動作します、速度が低下するのみ）")
            print(f"  → CUDA={torch.version.cuda}, PyTorch={tv}, Python={py} を開発者に伝えてください")

    except Exception as e:
        print(f"flash-attn: ⚠️ エラー: {e}")


if __name__ == "__main__":
    install_sox()
    install_flash_attn()
