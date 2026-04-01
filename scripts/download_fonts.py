#!/usr/bin/env python3
"""NotoSansCJK 폰트 번들 다운로드 스크립트."""
import sys
import io
from pathlib import Path
import urllib.request
import urllib.error

# Windows 터미널 UTF-8 출력 강제
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).parent.parent
FONTS_DIR = PROJECT_ROOT / "assets" / "fonts"

FONTS = {
    "NotoSansCJKkr-Regular.otf": "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/Korean/NotoSansCJKkr-Regular.otf",
    "NotoSansCJKkr-Bold.otf": "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/Korean/NotoSansCJKkr-Bold.otf",
}

MANUAL_DOWNLOAD_GUIDE = (
    "폰트 수동 다운로드 방법: https://fonts.google.com/noto/specimen/Noto+Sans+KR 에서 다운로드 후 "
    f"assets/fonts/ 에 복사"
)


def _progress_hook(block_num: int, block_size: int, total_size: int) -> None:
    downloaded = block_num * block_size
    if total_size > 0:
        percent = min(downloaded * 100 // total_size, 100)
        print(f"\r  진행: {percent}% ({downloaded:,} / {total_size:,} bytes)", end="", flush=True)


def download_font(filename: str, url: str) -> bool:
    dest = FONTS_DIR / filename

    if dest.exists():
        print(f"이미 존재함: {filename}")
        return True

    print(f"다운로드 중: {filename} ...")
    try:
        tmp_path = dest.with_suffix(".tmp")
        urllib.request.urlretrieve(url, tmp_path, reporthook=_progress_hook)
        print()  # 개행 (진행률 줄 종료)
        tmp_path.rename(dest)
        size = dest.stat().st_size
        print(f"완료: {filename} ({size:,} bytes)")
        return True
    except urllib.error.URLError as exc:
        print(f"\n오류: {filename} 다운로드 실패 — {exc}")
        if tmp_path.exists():
            tmp_path.unlink()
        return False
    except Exception as exc:
        print(f"\n오류: {filename} 다운로드 중 예외 발생 — {exc}")
        if tmp_path.exists():
            tmp_path.unlink()
        return False


def main() -> None:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    failed: list[str] = []
    for filename, url in FONTS.items():
        if not download_font(filename, url):
            failed.append(filename)

    if failed:
        print()
        print("다음 파일 다운로드에 실패했습니다:")
        for f in failed:
            print(f"  - {f}")
        print()
        print(MANUAL_DOWNLOAD_GUIDE)
        sys.exit(1)

    print()
    print(f"폰트 번들 준비 완료: {FONTS_DIR}")


if __name__ == "__main__":
    main()
