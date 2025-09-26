#!/usr/bin/env python3
"""Test multi-language support."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.multi_language import (
    Language,
    LanguageConfig,
    LanguageDetector,
    LanguageLocalizer,
    VoiceSelector,
    MultiLanguageManager,
    TranslationPair,
    get_manager
)


def test_language_enum():
    """Test language enumeration."""
    print("\n=== Testing Language Enum ===")
    
    # Test properties
    lang = Language.SPANISH
    print(f"Language: {lang.name}")
    print(f"Code: {lang.code}")
    print(f"Locale: {lang.locale}")
    
    # Test from_code
    test_codes = ["en", "es", "fr", "de", "zh", "ja", "invalid"]
    for code in test_codes:
        lang = Language.from_code(code)
        if lang:
            print(f"✓ {code} -> {lang.name}")
        else:
            print(f"✗ {code} -> None")


def test_language_detection():
    """Test language detection."""
    print("\n=== Testing Language Detection ===")
    
    detector = LanguageDetector()
    
    test_texts = [
        ("Hello, how are you today?", Language.ENGLISH),
        ("The weather is nice", Language.ENGLISH),
        ("Hola, ¿cómo estás?", Language.SPANISH),
        ("Buenos días amigo", Language.SPANISH),
        ("Bonjour, comment allez-vous?", Language.FRENCH),
        ("C'est magnifique!", Language.FRENCH),
        ("Guten Tag, wie geht es dir?", Language.GERMAN),
        ("Das ist sehr gut", Language.GERMAN),
        ("你好，你好吗？", Language.CHINESE),
        ("这是一个测试", Language.CHINESE),
        ("こんにちは、元気ですか？", Language.JAPANESE),
        ("これはテストです", Language.JAPANESE),
        ("Привет, как дела?", Language.RUSSIAN),
        ("안녕하세요", Language.KOREAN),
    ]
    
    for text, expected in test_texts:
        detected, confidence = detector.detect(text)
        status = "✓" if detected == expected else "✗"
        print(f"{status} {detected.name:10} ({confidence:.2f}): {text[:30]}")


def test_localization():
    """Test localization strings."""
    print("\n=== Testing Localization ===")
    
    localizer = LanguageLocalizer()
    
    # Test different languages
    languages = [
        Language.ENGLISH,
        Language.SPANISH,
        Language.FRENCH,
        Language.GERMAN,
        Language.CHINESE,
        Language.JAPANESE
    ]
    
    keys = ["greeting", "listening", "thinking", "ready"]
    
    for lang in languages:
        print(f"\n{lang.name}:")
        for key in keys:
            text = localizer.get_string(key, lang)
            print(f"  {key}: {text}")


def test_voice_selection():
    """Test voice selection."""
    print("\n=== Testing Voice Selection ===")
    
    selector = VoiceSelector()
    
    languages = [
        Language.ENGLISH,
        Language.SPANISH,
        Language.FRENCH,
        Language.GERMAN,
        Language.CHINESE,
        Language.JAPANESE,
        Language.KOREAN,
        Language.ARABIC,
        Language.RUSSIAN
    ]
    
    for lang in languages:
        voice = selector.get_voice(lang)
        print(f"{lang.name:12}: {voice}")


def test_language_config():
    """Test language configuration."""
    print("\n=== Testing Language Config ===")
    
    configs = [
        LanguageConfig(
            language=Language.ENGLISH,
            voice_id="alloy",
            speech_rate=1.0
        ),
        LanguageConfig(
            language=Language.SPANISH,
            voice_id="es_ES_voice",
            speech_rate=1.1,
            formality_level="formal"
        ),
        LanguageConfig(
            language=Language.JAPANESE,
            voice_id="ja_JP_voice",
            pitch_adjustment=0.2,
            formality_level="formal"
        )
    ]
    
    for config in configs:
        print(f"\n{config.language.name}:")
        print(f"  Voice: {config.voice_id}")
        print(f"  Rate: {config.speech_rate}")
        print(f"  Pitch: {config.pitch_adjustment}")
        print(f"  Formality: {config.formality_level}")


def test_manager_detection():
    """Test manager language detection."""
    print("\n=== Testing Manager Detection ===")
    
    manager = MultiLanguageManager()
    manager.auto_detect = True
    
    inputs = [
        "Hello, how can I help you?",
        "Hola, ¿en qué puedo ayudarte?",
        "Bonjour, comment puis-je vous aider?",
        "你好，我能帮你什么？",
    ]
    
    for text in inputs:
        processed, language = manager.process_input(text)
        print(f"Input: {text[:30]}")
        print(f"  Detected: {language.name}")
        print(f"  Current: {manager.current_language.name}")


def test_manager_localization():
    """Test manager localization."""
    print("\n=== Testing Manager Localization ===")
    
    manager = MultiLanguageManager()
    
    # Test different languages
    for lang in [Language.ENGLISH, Language.SPANISH, Language.FRENCH]:
        manager.set_language(lang)
        
        print(f"\n{lang.name}:")
        print(f"  Greeting: {manager.get_localized_string('greeting')}")
        print(f"  Error: {manager.get_localized_string('error')}")
        print(f"  Voice: {manager.get_voice_for_language()}")


def test_auto_language_switching():
    """Test automatic language switching."""
    print("\n=== Testing Auto Language Switching ===")
    
    manager = MultiLanguageManager()
    manager.auto_detect = True
    
    conversation = [
        ("Hello, I need help", Language.ENGLISH),
        ("Can you assist me?", Language.ENGLISH),
        ("Hola, necesito ayuda", Language.SPANISH),
        ("¿Puedes ayudarme?", Language.SPANISH),
        ("Merci beaucoup", Language.FRENCH),
        ("Back to English please", Language.ENGLISH),
    ]
    
    print("Conversation flow:")
    for text, expected in conversation:
        _, detected = manager.process_input(text)
        status = "✓" if manager.current_language == expected else "✗"
        print(f"{status} '{text[:25]}' -> {manager.current_language.name}")


def test_special_characters():
    """Test special character handling."""
    print("\n=== Testing Special Characters ===")
    
    detector = LanguageDetector()
    
    texts = [
        ("Café résumé naïve", Language.FRENCH),
        ("Español niño señor", Language.SPANISH),
        ("Über schön größer", Language.GERMAN),
        ("日本語のテスト", Language.JAPANESE),
        ("中文测试文本", Language.CHINESE),
        ("한글 테스트", Language.KOREAN),
        ("العربية نص", Language.ARABIC),
        ("Русский текст", Language.RUSSIAN),
    ]
    
    for text, expected in texts:
        detected, confidence = detector.detect(text)
        status = "✓" if detected == expected else "✗"
        print(f"{status} {text[:20]:20} -> {detected.name}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("MULTI-LANGUAGE SUPPORT TESTS")
    print("=" * 60)
    
    test_language_enum()
    test_language_detection()
    test_localization()
    test_voice_selection()
    test_language_config()
    test_manager_detection()
    test_manager_localization()
    test_auto_language_switching()
    test_special_characters()
    
    print("\n" + "=" * 60)
    print("✓ All multi-language tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()