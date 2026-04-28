"""CLI entrypoint for ``python -m src``."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="AI 기반 이미지 텍스트 자동 번역",
    )
    parser.add_argument("--input", "-i", required=True, help="입력 이미지 경로")
    parser.add_argument("--output", "-o", help="출력 이미지 경로 (기본: {input}_translated.png)")
    parser.add_argument("--target-lang", "-t", default="ko", help="목표 언어 코드 (기본: ko)")
    parser.add_argument("--source-lang", "-s", default="auto", help="소스 언어 코드 (기본: auto)")
    parser.add_argument("--translator", default="deepl", help="번역 플러그인 ID (기본: deepl)")
    parser.add_argument("--agent", default="claude", help="에이전트 플러그인 ID (기본: claude)")
    parser.add_argument("--ocr", default="easyocr", help="OCR 플러그인 ID (기본: easyocr)")
    parser.add_argument("--no-agent", action="store_true", help="에이전트 비활성화")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그 출력")
    return parser.parse_args(argv)


async def run_cli(args: argparse.Namespace) -> int:
    from src.core.config_manager import ConfigManager
    from src.core.pipeline import Pipeline
    from src.core.plugin_manager import PluginManager
    from src.core.session import Session
    from src.utils.logger import setup_logging

    setup_logging("DEBUG" if args.verbose else "INFO")

    config = ConfigManager()
    config.load()

    plugin_manager = PluginManager(config)
    session = Session()
    pipeline = Pipeline(config, plugin_manager)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"오류: 입력 파일 없음: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else (
        input_path.with_stem(input_path.stem + "_translated")
    )

    job = session.create_job_for_file(
        input_path=input_path,
        target_lang=args.target_lang,
        source_lang=args.source_lang,
        ocr_plugin_id=args.ocr,
        translator_plugin_id=args.translator,
        agent_plugin_id=args.agent,
        use_agent=not args.no_agent,
        output_path=output_path,
    )

    def on_progress(job, msg):
        print(f"[{int(job.progress * 100):3d}%] {msg}")

    try:
        await pipeline.run(job, progress_cb=on_progress)
        print(f"\n완료! 저장: {output_path}")
        return 0
    except Exception as e:
        print(f"\n실패: {e}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return asyncio.run(run_cli(args))


if __name__ == "__main__":
    sys.exit(main())
