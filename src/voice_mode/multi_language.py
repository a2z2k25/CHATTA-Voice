"""
Multi-language support for voice conversations.

This module provides language detection, translation, and
localization capabilities for global voice interactions.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
import unicodedata

logger = logging.getLogger(__name__)


class Language(Enum):
    """Supported languages."""
    # Major languages
    ENGLISH = ("en", "English", "en-US")
    SPANISH = ("es", "Español", "es-ES")
    FRENCH = ("fr", "Français", "fr-FR")
    GERMAN = ("de", "Deutsch", "de-DE")
    ITALIAN = ("it", "Italiano", "it-IT")
    PORTUGUESE = ("pt", "Português", "pt-BR")
    RUSSIAN = ("ru", "Русский", "ru-RU")
    CHINESE = ("zh", "中文", "zh-CN")
    JAPANESE = ("ja", "日本語", "ja-JP")
    KOREAN = ("ko", "한국어", "ko-KR")
    ARABIC = ("ar", "العربية", "ar-SA")
    HINDI = ("hi", "हिन्दी", "hi-IN")
    
    # Additional languages
    DUTCH = ("nl", "Nederlands", "nl-NL")
    POLISH = ("pl", "Polski", "pl-PL")
    TURKISH = ("tr", "Türkçe", "tr-TR")
    SWEDISH = ("sv", "Svenska", "sv-SE")
    NORWEGIAN = ("no", "Norsk", "no-NO")
    DANISH = ("da", "Dansk", "da-DK")
    FINNISH = ("fi", "Suomi", "fi-FI")
    GREEK = ("el", "Ελληνικά", "el-GR")
    CZECH = ("cs", "Čeština", "cs-CZ")
    HUNGARIAN = ("hu", "Magyar", "hu-HU")
    ROMANIAN = ("ro", "Română", "ro-RO")
    UKRAINIAN = ("uk", "Українська", "uk-UA")
    
    @property
    def code(self) -> str:
        """Get language code."""
        return self.value[0]
    
    @property
    def name(self) -> str:
        """Get language name."""
        return self.value[1]
    
    @property
    def locale(self) -> str:
        """Get locale code."""
        return self.value[2]
    
    @classmethod
    def from_code(cls, code: str) -> Optional['Language']:
        """Get language from code.
        
        Args:
            code: Language code (e.g., 'en', 'es')
            
        Returns:
            Language enum or None
        """
        code = code.lower().split('-')[0].split('_')[0]
        for lang in cls:
            if lang.code == code:
                return lang
        return None


@dataclass
class LanguageConfig:
    """Language-specific configuration."""
    language: Language
    voice_id: Optional[str] = None
    model_variant: Optional[str] = None
    speech_rate: float = 1.0
    pitch_adjustment: float = 0.0
    formality_level: str = "neutral"  # casual, neutral, formal
    dialect: Optional[str] = None
    custom_vocabulary: List[str] = field(default_factory=list)
    phonetic_hints: Dict[str, str] = field(default_factory=dict)


@dataclass
class TranslationPair:
    """Translation between two languages."""
    source_language: Language
    target_language: Language
    source_text: str
    translated_text: str
    confidence: float = 0.0
    alternatives: List[str] = field(default_factory=list)


class LanguageDetector:
    """Detects language from text or audio."""
    
    def __init__(self):
        """Initialize language detector."""
        self.patterns = self._load_patterns()
        self.char_ranges = self._load_char_ranges()
    
    def _load_patterns(self) -> Dict[Language, List[str]]:
        """Load language-specific patterns.
        
        Returns:
            Pattern dictionary
        """
        return {
            Language.ENGLISH: [
                r'\b(the|is|are|was|were|been|have|has|had)\b',
                r'\b(and|or|but|if|then|else)\b'
            ],
            Language.SPANISH: [
                r'\b(el|la|los|las|un|una)\b',
                r'\b(es|está|son|están|fue|fueron)\b'
            ],
            Language.FRENCH: [
                r'\b(le|la|les|un|une|des)\b',
                r'\b(est|sont|été|avoir|être)\b'
            ],
            Language.GERMAN: [
                r'\b(der|die|das|ein|eine)\b',
                r'\b(ist|sind|war|waren|haben|sein)\b'
            ],
            Language.CHINESE: [
                r'[\u4e00-\u9fff]+',  # Chinese characters
                r'[的是在有我他这个们]'
            ],
            Language.JAPANESE: [
                r'[\u3040-\u309f]+',  # Hiragana
                r'[\u30a0-\u30ff]+',  # Katakana
                r'[\u4e00-\u9fff]+',  # Kanji
            ],
            Language.KOREAN: [
                r'[\uac00-\ud7af]+',  # Hangul
                r'[\u1100-\u11ff]+',  # Jamo
            ],
            Language.ARABIC: [
                r'[\u0600-\u06ff]+',  # Arabic
                r'[\u0750-\u077f]+',  # Arabic Supplement
            ],
            Language.RUSSIAN: [
                r'[\u0400-\u04ff]+',  # Cyrillic
                r'\b(и|в|не|на|я|с|что|это)\b'
            ],
        }
    
    def _load_char_ranges(self) -> Dict[Language, Tuple[int, int]]:
        """Load Unicode character ranges.
        
        Returns:
            Character range dictionary
        """
        return {
            Language.CHINESE: (0x4e00, 0x9fff),
            Language.JAPANESE: (0x3040, 0x30ff),
            Language.KOREAN: (0xac00, 0xd7af),
            Language.ARABIC: (0x0600, 0x06ff),
            Language.RUSSIAN: (0x0400, 0x04ff),
            Language.GREEK: (0x0370, 0x03ff),
        }
    
    def detect(self, text: str) -> Tuple[Language, float]:
        """Detect language from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            (Language, confidence) tuple
        """
        if not text:
            return Language.ENGLISH, 0.0
        
        # Normalize text
        text = text.lower().strip()
        
        # Score each language
        scores = {}
        
        # Check patterns
        for lang, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            scores[lang] = score
        
        # Check character ranges
        for char in text:
            code_point = ord(char)
            for lang, (start, end) in self.char_ranges.items():
                if start <= code_point <= end:
                    scores[lang] = scores.get(lang, 0) + 1
        
        # Find best match
        if not scores:
            return Language.ENGLISH, 0.5
        
        total = sum(scores.values())
        if total == 0:
            return Language.ENGLISH, 0.5
        
        best_lang = max(scores, key=scores.get)
        confidence = scores[best_lang] / total
        
        return best_lang, confidence
    
    def detect_from_locale(self, locale: str) -> Optional[Language]:
        """Detect language from locale string.
        
        Args:
            locale: Locale string (e.g., 'en-US', 'es-ES')
            
        Returns:
            Language or None
        """
        return Language.from_code(locale)


class LanguageLocalizer:
    """Provides localized strings and formats."""
    
    def __init__(self):
        """Initialize localizer."""
        self.translations = self._load_translations()
        self.formats = self._load_formats()
    
    def _load_translations(self) -> Dict[Language, Dict[str, str]]:
        """Load translation strings.
        
        Returns:
            Translation dictionary
        """
        return {
            Language.ENGLISH: {
                "greeting": "Hello! How can I help you?",
                "goodbye": "Goodbye!",
                "listening": "Listening...",
                "thinking": "Let me think...",
                "error": "Sorry, I encountered an error.",
                "retry": "Let me try again.",
                "confirm": "Got it!",
                "wait": "One moment please...",
                "ready": "I'm ready!",
                "help": "How can I assist you?"
            },
            Language.SPANISH: {
                "greeting": "¡Hola! ¿Cómo puedo ayudarte?",
                "goodbye": "¡Adiós!",
                "listening": "Escuchando...",
                "thinking": "Déjame pensar...",
                "error": "Lo siento, encontré un error.",
                "retry": "Déjame intentar de nuevo.",
                "confirm": "¡Entendido!",
                "wait": "Un momento por favor...",
                "ready": "¡Estoy listo!",
                "help": "¿Cómo puedo asistirte?"
            },
            Language.FRENCH: {
                "greeting": "Bonjour! Comment puis-je vous aider?",
                "goodbye": "Au revoir!",
                "listening": "J'écoute...",
                "thinking": "Laissez-moi réfléchir...",
                "error": "Désolé, j'ai rencontré une erreur.",
                "retry": "Laissez-moi réessayer.",
                "confirm": "Compris!",
                "wait": "Un moment s'il vous plaît...",
                "ready": "Je suis prêt!",
                "help": "Comment puis-je vous aider?"
            },
            Language.GERMAN: {
                "greeting": "Hallo! Wie kann ich Ihnen helfen?",
                "goodbye": "Auf Wiedersehen!",
                "listening": "Ich höre zu...",
                "thinking": "Lass mich nachdenken...",
                "error": "Entschuldigung, ich bin auf einen Fehler gestoßen.",
                "retry": "Lass mich es nochmal versuchen.",
                "confirm": "Verstanden!",
                "wait": "Einen Moment bitte...",
                "ready": "Ich bin bereit!",
                "help": "Wie kann ich Ihnen helfen?"
            },
            Language.CHINESE: {
                "greeting": "你好！我能帮您什么？",
                "goodbye": "再见！",
                "listening": "正在听...",
                "thinking": "让我想想...",
                "error": "抱歉，我遇到了错误。",
                "retry": "让我再试一次。",
                "confirm": "明白了！",
                "wait": "请稍等...",
                "ready": "我准备好了！",
                "help": "我能帮您什么？"
            },
            Language.JAPANESE: {
                "greeting": "こんにちは！何かお手伝いできますか？",
                "goodbye": "さようなら！",
                "listening": "聞いています...",
                "thinking": "考えさせてください...",
                "error": "申し訳ありません、エラーが発生しました。",
                "retry": "もう一度試させてください。",
                "confirm": "分かりました！",
                "wait": "少々お待ちください...",
                "ready": "準備できました！",
                "help": "何かお手伝いできますか？"
            },
        }
    
    def _load_formats(self) -> Dict[Language, Dict[str, str]]:
        """Load formatting rules.
        
        Returns:
            Format dictionary
        """
        return {
            Language.ENGLISH: {
                "date": "%B %d, %Y",
                "time": "%I:%M %p",
                "number": "{:,.2f}",
                "currency": "${:,.2f}"
            },
            Language.SPANISH: {
                "date": "%d de %B de %Y",
                "time": "%H:%M",
                "number": "{:,.2f}",
                "currency": "{:,.2f} €"
            },
            Language.FRENCH: {
                "date": "%d %B %Y",
                "time": "%H:%M",
                "number": "{:,.2f}",
                "currency": "{:,.2f} €"
            },
            Language.GERMAN: {
                "date": "%d. %B %Y",
                "time": "%H:%M",
                "number": "{:,.2f}",
                "currency": "{:,.2f} €"
            },
        }
    
    def get_string(
        self,
        key: str,
        language: Language = Language.ENGLISH
    ) -> str:
        """Get localized string.
        
        Args:
            key: String key
            language: Target language
            
        Returns:
            Localized string
        """
        if language not in self.translations:
            language = Language.ENGLISH
        
        strings = self.translations[language]
        return strings.get(key, self.translations[Language.ENGLISH].get(key, key))
    
    def format_date(
        self,
        date: Any,
        language: Language = Language.ENGLISH
    ) -> str:
        """Format date for language.
        
        Args:
            date: Date object
            language: Target language
            
        Returns:
            Formatted date string
        """
        if language not in self.formats:
            language = Language.ENGLISH
        
        format_str = self.formats[language]["date"]
        return date.strftime(format_str)


class VoiceSelector:
    """Selects appropriate voice for language."""
    
    def __init__(self):
        """Initialize voice selector."""
        self.voice_map = self._load_voice_map()
    
    def _load_voice_map(self) -> Dict[Language, List[str]]:
        """Load voice mappings.
        
        Returns:
            Voice map dictionary
        """
        return {
            Language.ENGLISH: ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            Language.SPANISH: ["es_ES_voice", "es_MX_voice"],
            Language.FRENCH: ["fr_FR_voice", "fr_CA_voice"],
            Language.GERMAN: ["de_DE_voice", "de_AT_voice"],
            Language.ITALIAN: ["it_IT_voice"],
            Language.PORTUGUESE: ["pt_BR_voice", "pt_PT_voice"],
            Language.RUSSIAN: ["ru_RU_voice"],
            Language.CHINESE: ["zh_CN_voice", "zh_TW_voice"],
            Language.JAPANESE: ["ja_JP_voice"],
            Language.KOREAN: ["ko_KR_voice"],
            Language.ARABIC: ["ar_SA_voice"],
        }
    
    def get_voice(
        self,
        language: Language,
        gender: Optional[str] = None,
        age: Optional[str] = None
    ) -> str:
        """Get appropriate voice for language.
        
        Args:
            language: Target language
            gender: Preferred gender (male/female/neutral)
            age: Preferred age (young/middle/senior)
            
        Returns:
            Voice ID
        """
        voices = self.voice_map.get(language, self.voice_map[Language.ENGLISH])
        
        if not voices:
            return "alloy"  # Default
        
        # TODO: Add gender/age filtering
        return voices[0]


class MultiLanguageManager:
    """Manages multi-language conversations."""
    
    def __init__(self):
        """Initialize manager."""
        self.detector = LanguageDetector()
        self.localizer = LanguageLocalizer()
        self.voice_selector = VoiceSelector()
        self.current_language = Language.ENGLISH
        self.auto_detect = True
        self.translation_cache: Dict[str, TranslationPair] = {}
    
    def detect_language(self, text: str) -> Tuple[Language, float]:
        """Detect language from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            (Language, confidence) tuple
        """
        return self.detector.detect(text)
    
    def set_language(self, language: Language):
        """Set current language.
        
        Args:
            language: Language to use
        """
        self.current_language = language
        logger.info(f"Language set to {language.name}")
    
    def get_localized_string(self, key: str) -> str:
        """Get localized string for current language.
        
        Args:
            key: String key
            
        Returns:
            Localized string
        """
        return self.localizer.get_string(key, self.current_language)
    
    def get_voice_for_language(self, language: Optional[Language] = None) -> str:
        """Get voice for language.
        
        Args:
            language: Target language (uses current if None)
            
        Returns:
            Voice ID
        """
        if language is None:
            language = self.current_language
        return self.voice_selector.get_voice(language)
    
    def get_language_config(self, language: Optional[Language] = None) -> LanguageConfig:
        """Get configuration for language.
        
        Args:
            language: Target language (uses current if None)
            
        Returns:
            Language configuration
        """
        if language is None:
            language = self.current_language
        
        return LanguageConfig(
            language=language,
            voice_id=self.get_voice_for_language(language),
            model_variant=f"whisper-{language.code}",
            speech_rate=1.0,
            pitch_adjustment=0.0,
            formality_level="neutral"
        )
    
    def process_input(self, text: str) -> Tuple[str, Language]:
        """Process input with language detection.
        
        Args:
            text: Input text
            
        Returns:
            (processed_text, detected_language) tuple
        """
        if self.auto_detect:
            language, confidence = self.detect_language(text)
            if confidence > 0.7 and language != self.current_language:
                logger.info(
                    f"Language switched: {self.current_language.name} -> "
                    f"{language.name} (confidence: {confidence:.2f})"
                )
                self.current_language = language
        else:
            language = self.current_language
        
        return text, language
    
    def prepare_output(self, text: str, target_language: Optional[Language] = None) -> str:
        """Prepare output for language.
        
        Args:
            text: Output text
            target_language: Target language (uses current if None)
            
        Returns:
            Prepared text
        """
        if target_language is None:
            target_language = self.current_language
        
        # TODO: Add translation support
        return text


# Global manager instance
_manager: Optional[MultiLanguageManager] = None


def get_manager() -> MultiLanguageManager:
    """Get global language manager.
    
    Returns:
        Language manager instance
    """
    global _manager
    if _manager is None:
        _manager = MultiLanguageManager()
    return _manager


# Example usage
def example_usage():
    """Example of using multi-language support."""
    
    manager = get_manager()
    
    # Test language detection
    texts = [
        ("Hello, how are you?", Language.ENGLISH),
        ("Hola, ¿cómo estás?", Language.SPANISH),
        ("Bonjour, comment allez-vous?", Language.FRENCH),
        ("你好，你好吗？", Language.CHINESE),
        ("こんにちは、元気ですか？", Language.JAPANESE),
    ]
    
    print("Language Detection:")
    for text, expected in texts:
        detected, confidence = manager.detect_language(text)
        status = "✓" if detected == expected else "✗"
        print(f"{status} '{text[:20]}...' -> {detected.name} ({confidence:.2f})")
    
    # Test localization
    print("\nLocalized Strings:")
    for lang in [Language.ENGLISH, Language.SPANISH, Language.FRENCH]:
        manager.set_language(lang)
        greeting = manager.get_localized_string("greeting")
        print(f"{lang.name}: {greeting}")
    
    # Test voice selection
    print("\nVoice Selection:")
    for lang in [Language.ENGLISH, Language.SPANISH, Language.CHINESE]:
        voice = manager.get_voice_for_language(lang)
        print(f"{lang.name}: {voice}")


if __name__ == "__main__":
    example_usage()