"""AbstractAgentPlugin ABC."""
from __future__ import annotations

from abc import abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from src.models.processing_job import ProcessingJob
from src.models.text_region import TextRegion
from src.plugins.base.plugin_base import PluginBase


class AbstractAgentPlugin(PluginBase):
    """AI 에이전트 플러그인 추상 기반 클래스.

    중요: 에이전트는 번역 API를 직접 호출하지 않는다.
    OCR 결과 분석, 번역 컨텍스트 생성, 번역 결과 검증만 담당.
    실제 번역은 파이프라인을 통해 번역 플러그인에 위임.
    """

    PLUGIN_TYPE = "agent"

    @abstractmethod
    async def analyze_ocr_results(
        self,
        regions: list[TextRegion],
        image_description: str | None = None,
    ) -> list[TextRegion]:
        """OCR 결과를 분석하여 품질 개선.

        수행 작업:
        - OCR 오류 텍스트 교정
        - 읽기 순서 정렬 (만화 등 비선형 레이아웃)
        - 저신뢰도 영역 병합/분리 제안
        - 각 TextRegion의 reading_order 설정

        Args:
            regions: OCR 탐지 결과
            image_description: 이미지 유형 힌트 ("manga", "document", "screenshot" 등)

        Returns:
            분석·교정된 TextRegion 목록
        """

    @abstractmethod
    async def generate_translation_context(
        self,
        regions: list[TextRegion],
        job: ProcessingJob,
    ) -> dict[str, str]:
        """각 TextRegion에 대한 번역 컨텍스트 힌트 생성.

        Args:
            regions: 언어 감지 완료된 TextRegion 목록
            job: 현재 ProcessingJob (source_lang, target_lang 포함)

        Returns:
            {region_id: context_hint} 딕셔너리
        """

    @abstractmethod
    async def validate_translations(
        self,
        original_regions: list[TextRegion],
        translated_regions: list[TextRegion],
    ) -> list[TextRegion]:
        """번역 결과 일관성·완전성 검증.

        검증 항목:
        - 번역 누락 영역 탐지
        - 언어 일관성 확인
        - 고유명사/전문용어 검증
        - 문맥 연속성 검사

        의심 영역의 needs_review = True 설정.

        Args:
            original_regions: 원문 TextRegion 목록
            translated_regions: 번역된 TextRegion 목록

        Returns:
            needs_review 플래그가 업데이트된 TextRegion 목록
        """

    @abstractmethod
    async def stream_analysis(self, prompt: str) -> AsyncIterator[str]:
        """GUI 실시간 피드백을 위한 스트리밍 분석.

        Args:
            prompt: 에이전트에게 전달할 프롬프트

        Yields:
            텍스트 청크 (SSE 스타일)
        """

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "plugin_type": "agent",
            "plugin_name": self.PLUGIN_NAME,
        }
