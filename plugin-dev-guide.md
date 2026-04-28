# 플러그인 개발 가이드

> AGENTS.md에서 참조됩니다.

## 새 번역 플러그인 추가

1. `src/plugins/base/translator_plugin.py`의 `AbstractTranslatorPlugin` 상속
2. 클래스 변수 설정:
   - `PLUGIN_NAME`
   - `PLUGIN_VERSION`
   - `PLUGIN_DESCRIPTION`
3. 필수 메서드 구현:
   - `load()` / `unload()` / `validate_config()` / `get_capabilities()`
   - `translate(text, source_lang, target_lang, context)` → `TranslationResult`
   - `translate_batch(regions, source_lang, target_lang)` → `list[TranslationResult]`
   - `get_supported_language_pairs()` → `list[tuple[str, str]]`
4. `config/plugins.yaml`의 `translators` 섹션에 등록
