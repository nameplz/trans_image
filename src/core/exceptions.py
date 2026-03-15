"""trans_image 커스텀 예외 계층."""
from __future__ import annotations


class TransImageError(Exception):
    """모든 trans_image 예외의 기반 클래스."""


# --- 플러그인 예외 ---

class PluginError(TransImageError):
    """플러그인 관련 기반 예외."""


class PluginNotFoundError(PluginError):
    """요청한 플러그인 ID를 찾을 수 없음."""


class PluginLoadError(PluginError):
    """플러그인 로드/초기화 실패."""


class PluginConfigError(PluginError):
    """플러그인 설정 오류 (API 키 누락 등)."""


# --- OCR 예외 ---

class OCRError(TransImageError):
    """OCR 처리 실패."""


# --- 번역 예외 ---

class TranslationError(TransImageError):
    """번역 처리 실패 기반 예외."""


class TranslationAPIError(TranslationError):
    """번역 API 호출 실패 (HTTP 오류 등)."""
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(TranslationAPIError):
    """API 속도 제한 초과 (HTTP 429)."""


class UnsupportedLanguagePairError(TranslationError):
    """해당 플러그인이 지원하지 않는 언어 쌍."""


# --- 에이전트 예외 ---

class AgentError(TransImageError):
    """AI 에이전트 처리 실패 기반 예외."""


class AgentAPIError(AgentError):
    """에이전트 API 호출 실패."""
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# --- 이미지 처리 예외 ---

class ImageProcessingError(TransImageError):
    """이미지 로드/저장/변환 실패."""


class InpaintingError(ImageProcessingError):
    """인페인팅 처리 실패."""


class RenderingError(ImageProcessingError):
    """텍스트 렌더링 실패."""


# --- 설정 예외 ---

class ConfigError(TransImageError):
    """설정 로드/파싱 실패."""


# --- 파이프라인 예외 ---

class PipelineError(TransImageError):
    """파이프라인 실행 중 복구 불가능한 오류."""
