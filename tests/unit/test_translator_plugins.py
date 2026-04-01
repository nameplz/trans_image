"""번역 플러그인 단위 테스트 (5개 번역기)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import PluginConfigError
from src.models.text_region import BoundingBox, TextRegion
from src.models.translation_result import TranslationResult


def make_region(text: str = "Hello") -> TextRegion:
    return TextRegion(
        raw_text=text,
        bbox=BoundingBox(x=0, y=0, width=100, height=30),
        confidence=0.9,
    )


# ── DeepL ─────────────────────────────────────────────────────────────────────

class TestDeepLTranslatorPlugin:
    def test_validate_config_no_api_key(self):
        """API 키 없음 → validate_config에서 오류 반환."""
        from src.plugins.translators.deepl_translator import DeepLTranslatorPlugin
        plugin = DeepLTranslatorPlugin(config={"api_key": ""})
        errors = plugin.validate_config()
        assert len(errors) > 0

    def test_validate_config_with_api_key(self):
        """API 키 있음 → validate_config 빈 목록 반환."""
        from src.plugins.translators.deepl_translator import DeepLTranslatorPlugin
        plugin = DeepLTranslatorPlugin(config={"api_key": "my-key"})
        errors = plugin.validate_config()
        assert errors == []

    async def test_translate_mock(self):
        """deepl.Translator mock으로 translate 호출."""
        from src.plugins.translators.deepl_translator import DeepLTranslatorPlugin

        with patch("deepl.Translator") as mock_cls:
            mock_translator = MagicMock()
            mock_result = MagicMock()
            mock_result.text = "번역됨"
            mock_translator.translate_text.return_value = mock_result
            mock_cls.return_value = mock_translator

            plugin = DeepLTranslatorPlugin(config={"api_key": "test-key"})
            await plugin.load()
            result = await plugin.translate("Hello", "en", "ko")

        assert result.translated_text == "번역됨"
        assert isinstance(result, TranslationResult)

    async def test_translate_batch_mock(self):
        """translate_batch → TranslationResult 목록 반환."""
        from src.plugins.translators.deepl_translator import DeepLTranslatorPlugin

        with patch("deepl.Translator") as mock_cls:
            mock_translator = MagicMock()
            mock_results = [MagicMock(text="번역1"), MagicMock(text="번역2")]
            mock_translator.translate_text.return_value = mock_results
            mock_cls.return_value = mock_translator

            plugin = DeepLTranslatorPlugin(config={"api_key": "test-key"})
            await plugin.load()
            regions = [make_region("Hello"), make_region("World")]
            results = await plugin.translate_batch(regions, "en", "ko")

        assert len(results) == 2
        assert all(isinstance(r, TranslationResult) for r in results)


# ── Gemini ────────────────────────────────────────────────────────────────────

class TestGeminiTranslatorPlugin:
    def test_validate_config_no_api_key(self):
        """API 키 없음 → validate_config에서 오류 반환."""
        from src.plugins.translators.gemini_translator import GeminiTranslatorPlugin
        plugin = GeminiTranslatorPlugin(config={"api_key": ""})
        errors = plugin.validate_config()
        assert len(errors) > 0

    def test_validate_config_with_api_key(self):
        """API 키 있음 → validate_config 빈 목록 반환."""
        from src.plugins.translators.gemini_translator import GeminiTranslatorPlugin
        plugin = GeminiTranslatorPlugin(config={"api_key": "my-key"})
        errors = plugin.validate_config()
        assert errors == []

    async def test_translate_mock(self):
        """google.genai.Client mock으로 translate 호출."""
        from src.plugins.translators.gemini_translator import GeminiTranslatorPlugin

        with patch("google.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "번역됨"
            mock_cls.return_value = mock_client

            plugin = GeminiTranslatorPlugin(config={"api_key": "test-key"})
            await plugin.load()

            # asyncio.to_thread를 패치하여 mock_response 반환
            with patch("src.plugins.translators.gemini_translator.asyncio.to_thread",
                       new=AsyncMock(return_value=mock_response)):
                result = await plugin.translate("Hello", "en", "ko")

        assert isinstance(result, TranslationResult)
        assert result.translated_text == "번역됨"

    async def test_translate_batch_mock(self):
        """translate_batch → TranslationResult 목록 반환 (gather 사용)."""
        from src.plugins.translators.gemini_translator import GeminiTranslatorPlugin

        with patch("google.genai.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value = mock_client

            plugin = GeminiTranslatorPlugin(config={"api_key": "test-key", "model": "gemini-1.5-flash"})
            plugin._loaded = True
            plugin._client = mock_client

            # translate를 직접 mock
            mock_tr = TranslationResult(
                region_id="", source_text="Hello",
                translated_text="안녕", source_lang="en", target_lang="ko"
            )
            plugin.translate = AsyncMock(return_value=mock_tr)

            regions = [make_region("Hello"), make_region("World")]
            results = await plugin.translate_batch(regions, "en", "ko")

        assert len(results) == 2


# ── Grok ──────────────────────────────────────────────────────────────────────

class TestGrokTranslatorPlugin:
    def test_validate_config_no_api_key(self):
        """API 키 없음 → validate_config에서 오류 반환."""
        from src.plugins.translators.grok_translator import GrokTranslatorPlugin
        plugin = GrokTranslatorPlugin(config={"api_key": ""})
        errors = plugin.validate_config()
        assert len(errors) > 0

    def test_validate_config_with_api_key(self):
        """API 키 있음 → validate_config 빈 목록 반환."""
        from src.plugins.translators.grok_translator import GrokTranslatorPlugin
        plugin = GrokTranslatorPlugin(config={"api_key": "my-key"})
        errors = plugin.validate_config()
        assert errors == []

    async def test_translate_mock(self):
        """openai.AsyncOpenAI mock으로 translate 호출."""
        from src.plugins.translators.grok_translator import GrokTranslatorPlugin

        with patch("openai.AsyncOpenAI") as mock_cls:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "번역됨"
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            plugin = GrokTranslatorPlugin(config={"api_key": "test-key"})
            await plugin.load()
            result = await plugin.translate("Hello", "en", "ko")

        assert result.translated_text == "번역됨"

    async def test_translate_batch_mock(self):
        """translate_batch → 각 region에 대한 결과 목록 반환."""
        from src.plugins.translators.grok_translator import GrokTranslatorPlugin

        plugin = GrokTranslatorPlugin(config={"api_key": "test-key"})
        plugin._loaded = True
        mock_tr = TranslationResult(
            region_id="", source_text="Hello",
            translated_text="안녕", source_lang="en", target_lang="ko"
        )
        plugin.translate = AsyncMock(return_value=mock_tr)

        regions = [make_region("Hello"), make_region("World")]
        results = await plugin.translate_batch(regions, "en", "ko")
        assert len(results) == 2


# ── Papago ────────────────────────────────────────────────────────────────────

class TestPapagoTranslatorPlugin:
    def test_validate_config_no_credentials(self):
        """client_id, client_secret 없음 → 오류 반환."""
        from src.plugins.translators.papago_translator import PapagoTranslatorPlugin
        plugin = PapagoTranslatorPlugin(config={"client_id": "", "client_secret": ""})
        errors = plugin.validate_config()
        assert len(errors) == 2

    def test_validate_config_with_credentials(self):
        """credentials 모두 있음 → 빈 목록 반환."""
        from src.plugins.translators.papago_translator import PapagoTranslatorPlugin
        plugin = PapagoTranslatorPlugin(config={"client_id": "id123", "client_secret": "secret123"})
        errors = plugin.validate_config()
        assert errors == []

    async def test_translate_mock(self):
        """requests.post mock으로 translate 호출 (_call_api를 직접 mock)."""
        from src.plugins.translators.papago_translator import PapagoTranslatorPlugin

        plugin = PapagoTranslatorPlugin(
            config={"client_id": "id123", "client_secret": "secret123"}
        )
        await plugin.load()

        # _call_api는 동기 메서드이므로 asyncio.to_thread 안에서 호출됨
        # to_thread를 통해 반환되는 결과를 직접 mock
        with patch.object(plugin, "_call_api", return_value="번역됨"):
            with patch("src.plugins.translators.papago_translator.asyncio.to_thread",
                       new=AsyncMock(return_value="번역됨")):
                result = await plugin.translate("Hello", "en", "ko")

        assert isinstance(result, TranslationResult)
        assert result.translated_text == "번역됨"

    async def test_translate_batch_mock(self):
        """translate_batch → TranslationResult 목록 반환."""
        from src.plugins.translators.papago_translator import PapagoTranslatorPlugin

        plugin = PapagoTranslatorPlugin(
            config={"client_id": "id123", "client_secret": "secret123"}
        )
        plugin._loaded = True
        mock_tr = TranslationResult(
            region_id="", source_text="Hello",
            translated_text="안녕", source_lang="en", target_lang="ko"
        )
        plugin.translate = AsyncMock(return_value=mock_tr)

        regions = [make_region("Hello"), make_region("World")]
        results = await plugin.translate_batch(regions, "en", "ko")
        assert len(results) == 2


# ── Ollama ────────────────────────────────────────────────────────────────────

class TestOllamaTranslatorPlugin:
    def test_validate_config_always_empty(self):
        """Ollama는 API 키 불필요 → 항상 빈 목록."""
        from src.plugins.translators.ollama_translator import OllamaTranslatorPlugin
        plugin = OllamaTranslatorPlugin(config={})
        errors = plugin.validate_config()
        assert errors == []

    def test_default_config(self):
        """기본 설정값 확인."""
        from src.plugins.translators.ollama_translator import OllamaTranslatorPlugin
        plugin = OllamaTranslatorPlugin(config={})
        assert plugin._base_url == "http://localhost:11434"
        assert plugin._model == "llama3.1"

    async def test_translate_mock(self):
        """ollama.AsyncClient mock으로 translate 호출."""
        from src.plugins.translators.ollama_translator import OllamaTranslatorPlugin

        with patch("ollama.AsyncClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(return_value={"response": "번역됨"})
            mock_cls.return_value = mock_client

            plugin = OllamaTranslatorPlugin(config={"model": "llama3.1"})
            await plugin.load()
            result = await plugin.translate("Hello", "en", "ko")

        assert result.translated_text == "번역됨"

    async def test_translate_batch_sequential(self):
        """translate_batch → 순차 처리, 각 region에 대한 결과 반환."""
        from src.plugins.translators.ollama_translator import OllamaTranslatorPlugin

        with patch("ollama.AsyncClient") as mock_cls:
            mock_client = MagicMock()
            call_count = 0

            async def generate_side(**kwargs):
                nonlocal call_count
                call_count += 1
                return {"response": f"번역{call_count}"}

            mock_client.generate = AsyncMock(side_effect=generate_side)
            mock_cls.return_value = mock_client

            plugin = OllamaTranslatorPlugin(config={"model": "llama3.1"})
            await plugin.load()

            regions = [make_region("Hello"), make_region("World")]
            results = await plugin.translate_batch(regions, "en", "ko")

        assert len(results) == 2
        assert all(isinstance(r, TranslationResult) for r in results)
