"""Colab 環境セットアップスクリプト。

Cell 1 の git pull/clone 直後に実行される。
古い notebook でも Cell 1 が git pull すれば最新版のこのスクリプトが使われる。
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

        cuda = torch.version.cuda.replace(".", "")[:3]
        tv = torch.__version__.split("+")[0]
        tv_mm = ".".join(tv.split(".")[:2])
        py = f"cp{sys.version_info.major}{sys.version_info.minor}"

        print(f"flash-attn: CUDA={torch.version.cuda}, PyTorch={tv}, Python={py}")

        for ver in ["2.7.4", "2.7.3", "2.6.3", "2.5.9.post1", "2.5.8"]:
            whl = (
                f"flash_attn-{ver}+cu{cuda}torch{tv_mm}"
                f"cxx11abiFALSE-{py}-{py}-linux_x86_64.whl"
            )
            url = (
                f"https://github.com/Dao-AILab/flash-attention"
                f"/releases/download/v{ver}/{whl}"
            )
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", url],
                capture_output=True, text=True,
            )
            if r.returncode == 0:
                print(f"flash-attn: ✅ {ver} インストール成功")
                return
            print(f"flash-attn:    v{ver}: 対応 wheel なし")

        print("flash-attn: ⚠️ 対応 wheel が見つかりませんでした（TTS は正常動作します）")

    except Exception as e:
        print(f"flash-attn: ⚠️ スキップ: {e}")


if __name__ == "__main__":
    install_sox()
    install_flash_attn()
