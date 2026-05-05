"""trans_image 진입점 — GUI 모드."""
from __future__ import annotations

import sys


def main() -> int:
    from src.app import main as gui_main

    return gui_main(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
