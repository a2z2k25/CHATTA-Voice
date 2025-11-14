"""
PTT help system and FAQ.

Provides context-sensitive help, common issues FAQ, and documentation links.
"""

import sys
from typing import Optional, List, Dict
from dataclasses import dataclass

from voice_mode.ptt.logging import get_ptt_logger


@dataclass
class HelpTopic:
    """A help topic."""

    title: str
    content: str
    related_topics: List[str]
    doc_url: Optional[str] = None


class PTTHelpSystem:
    """
    PTT help system.

    Provides context-sensitive help and FAQ.
    """

    def __init__(self):
        """Initialize help system."""
        self.logger = get_ptt_logger()
        self.platform = sys.platform
        self._init_help_topics()
        self._init_faq()

    def _init_help_topics(self):
        """Initialize help topics."""
        self.topics: Dict[str, HelpTopic] = {
            'getting_started': HelpTopic(
                title="Getting Started with PTT",
                content="""
Push-to-Talk (PTT) allows you to control voice recording with keyboard shortcuts.

Basic Usage:
1. PTT is controlled by a key combination (default: down+right arrow keys)
2. Press/hold the keys to start recording
3. Release (or press again) to stop and transcribe

Modes:
- hold: Hold keys to record, release to stop (walkie-talkie style)
- toggle: Press to start, press again to stop
- hybrid: Hold OR toggle with automatic stop on silence

Configuration:
- Set CHATTA_PTT_MODE to your preferred mode
- Set CHATTA_PTT_KEY_COMBO to your preferred keys
- Run setup wizard: python -m voice_mode.ptt.setup_helper --setup
""",
                related_topics=['modes', 'key_combinations', 'configuration'],
                doc_url="https://github.com/yourusername/chatta/blob/main/docs/ptt/README.md"
            ),

            'modes': HelpTopic(
                title="PTT Modes",
                content="""
PTT supports three recording modes:

1. Hold Mode (default)
   - Press and hold keys to record
   - Release keys to stop
   - Like a walkie-talkie
   - Best for: Quick, controlled recordings

2. Toggle Mode
   - Press keys once to start recording
   - Press again to stop
   - Hands-free during recording
   - Best for: Longer recordings, presentations

3. Hybrid Mode
   - Can use either hold OR toggle
   - Automatically stops on silence
   - Most flexible option
   - Best for: Variable length recordings

Set mode:
  export CHATTA_PTT_MODE=hold    # or toggle, hybrid
""",
                related_topics=['getting_started', 'configuration'],
                doc_url="https://github.com/yourusername/chatta/blob/main/docs/ptt/modes.md"
            ),

            'key_combinations': HelpTopic(
                title="Key Combinations",
                content="""
PTT key combinations control when recording starts/stops.

Common Combinations:
- down+right    Arrow keys (recommended for macOS, no conflicts)
- ctrl+space    Modifier + key
- f12           Single function key
- shift+tab     Modifier + special key

Tips:
- Use arrow keys on macOS to avoid accessibility permission issues
- Avoid system shortcuts (cmd+tab, alt+tab, etc.)
- Test your combination doesn't conflict with other apps
- Modifiers alone (ctrl, shift) don't work well

Set combination:
  export CHATTA_PTT_KEY_COMBO=down+right
""",
                related_topics=['getting_started', 'macos_permissions'],
                doc_url="https://github.com/yourusername/chatta/blob/main/docs/ptt/key-combinations.md"
            ),

            'configuration': HelpTopic(
                title="Configuration",
                content="""
PTT is configured via environment variables:

Core Settings:
  CHATTA_PTT_ENABLED=true          # Enable PTT
  CHATTA_PTT_MODE=hold              # hold, toggle, hybrid
  CHATTA_PTT_KEY_COMBO=down+right  # Key combination
  CHATTA_PTT_TIMEOUT=120.0         # Max recording seconds

Feedback Settings:
  CHATTA_PTT_VISUAL_FEEDBACK=true  # Show visual status
  CHATTA_PTT_VISUAL_STYLE=compact  # minimal, compact, detailed
  CHATTA_PTT_AUDIO_FEEDBACK=true   # Play audio tones
  CHATTA_PTT_FEEDBACK_VOLUME=0.7   # Volume 0.0-1.0

Advanced Settings:
  CHATTA_PTT_MIN_DURATION=0.5      # Minimum recording length
  CHATTA_PTT_CANCEL_KEY=escape     # Key to cancel recording

Setup Wizard:
  python -m voice_mode.ptt.setup_helper --setup

Validate Configuration:
  python -m voice_mode.ptt.setup_helper --diagnose
""",
                related_topics=['getting_started', 'modes', 'troubleshooting'],
                doc_url="https://github.com/yourusername/chatta/blob/main/docs/ptt/configuration.md"
            ),

            'macos_permissions': HelpTopic(
                title="macOS Accessibility Permissions",
                content="""
macOS requires accessibility permissions for keyboard monitoring.

Grant Permissions:
1. Open System Settings (or System Preferences on older macOS)
2. Navigate to: Privacy & Security → Accessibility
3. Click the lock icon to make changes (may need password)
4. Find your terminal application in the list:
   - Terminal.app (default macOS terminal)
   - iTerm2
   - VS Code
   - Alacritty
   - Kitty
5. Enable the checkbox next to your terminal
6. Restart your terminal application

Verify Permissions:
  python -m voice_mode.ptt.setup_helper --check

Common Issues:
- Terminal not in list: Try adding it manually with the + button
- Changes not taking effect: Restart terminal completely
- Still not working: Log out and log back in

Alternative:
Use arrow keys (down+right) which may work without full permissions.
""",
                related_topics=['troubleshooting', 'key_combinations'],
                doc_url="https://github.com/yourusername/chatta/blob/main/docs/ptt/macos-permissions.md"
            ),

            'linux_wayland': HelpTopic(
                title="Linux Wayland Support",
                content="""
PTT on Linux Wayland may have limitations due to compositor restrictions.

If PTT doesn't work on Wayland:

1. Use X11 Instead:
   - Log out
   - At login screen, select "GNOME on Xorg" or "KDE Plasma (X11)"
   - Log back in

2. Set X11 Backend:
   export GDK_BACKEND=x11
   # Add to ~/.bashrc or ~/.zshrc

3. Check Compositor:
   - GNOME/Mutter: Generally works
   - KDE/KWin: Generally works
   - Sway: May need compositor configuration

4. User Group:
   sudo usermod -a -G input $USER
   # Log out and back in

Verify Setup:
  python -m voice_mode.ptt.setup_helper --check
""",
                related_topics=['troubleshooting'],
                doc_url="https://github.com/yourusername/chatta/blob/main/docs/ptt/linux-wayland.md"
            ),

            'troubleshooting': HelpTopic(
                title="Troubleshooting",
                content="""
Common PTT issues and solutions:

1. PTT Keys Not Working:
   - macOS: Grant accessibility permissions
   - Linux: Try X11 instead of Wayland
   - All: Check key combination doesn't conflict
   - Run: python -m voice_mode.ptt.setup_helper --check

2. No Audio Recording:
   - Check microphone permissions
   - Verify audio device is available
   - Test with: python -c "import sounddevice; print(sounddevice.query_devices())"
   - Check CHATTA_PTT_AUDIO_DEVICE setting

3. Recording Cuts Off Early:
   - Increase CHATTA_PTT_TIMEOUT
   - Check CHATTA_PTT_MIN_DURATION isn't too high
   - Ensure keys stay pressed (hold mode)

4. Library Import Errors:
   - pynput missing: pip install pynput
   - sounddevice missing: pip install sounddevice
   - numpy missing: pip install numpy

5. Configuration Issues:
   - Validate: python -m voice_mode.ptt.setup_helper --diagnose
   - Reset: unset all CHATTA_PTT_* variables
   - Setup wizard: python -m voice_mode.ptt.setup_helper --setup

Run Full Diagnostics:
  python -m voice_mode.ptt.setup_helper --diagnose
""",
                related_topics=['macos_permissions', 'linux_wayland', 'configuration'],
                doc_url="https://github.com/yourusername/chatta/blob/main/docs/ptt/troubleshooting.md"
            ),
        }

    def _init_faq(self):
        """Initialize FAQ."""
        self.faq: List[Dict[str, str]] = [
            {
                'question': "How do I change the PTT key combination?",
                'answer': "Set CHATTA_PTT_KEY_COMBO environment variable. Example: export CHATTA_PTT_KEY_COMBO=ctrl+space\n"
                         "Run setup wizard for interactive configuration: python -m voice_mode.ptt.setup_helper --setup"
            },
            {
                'question': "Why doesn't PTT work on my Mac?",
                'answer': "macOS requires accessibility permissions. Go to System Settings → Privacy & Security → "
                         "Accessibility, enable your terminal app, and restart the terminal. See 'macos_permissions' topic for details."
            },
            {
                'question': "Can I use PTT without audio feedback?",
                'answer': "Yes! Disable audio feedback with: export CHATTA_PTT_AUDIO_FEEDBACK=false\n"
                         "Visual feedback will still show recording status."
            },
            {
                'question': "What's the difference between hold and toggle mode?",
                'answer': "Hold mode: Press and hold to record, release to stop (walkie-talkie style)\n"
                         "Toggle mode: Press once to start, press again to stop (hands-free)\n"
                         "Hybrid mode: Can use either, plus automatic silence detection\n"
                         "See 'modes' topic for details."
            },
            {
                'question': "How do I increase the recording timeout?",
                'answer': "Set CHATTA_PTT_TIMEOUT to desired seconds. Example: export CHATTA_PTT_TIMEOUT=300 (5 minutes)\n"
                         "Default is 120 seconds (2 minutes)."
            },
            {
                'question': "PTT stops recording immediately. Why?",
                'answer': "Check CHATTA_PTT_MIN_DURATION. If too high, short recordings are rejected.\n"
                         "Try: export CHATTA_PTT_MIN_DURATION=0.3\n"
                         "Also ensure you're holding the keys long enough in hold mode."
            },
            {
                'question': "Can I cancel a recording in progress?",
                'answer': "Yes! Press the cancel key (default: escape) or use Ctrl+C.\n"
                         "Customize cancel key: export CHATTA_PTT_CANCEL_KEY=your_key"
            },
            {
                'question': "Does PTT work on Linux Wayland?",
                'answer': "Wayland support varies by compositor. If PTT doesn't work, try X11 instead.\n"
                         "See 'linux_wayland' topic for detailed instructions."
            },
            {
                'question': "How do I disable visual status display?",
                'answer': "Set: export CHATTA_PTT_VISUAL_FEEDBACK=false\n"
                         "Or change style: export CHATTA_PTT_VISUAL_STYLE=minimal"
            },
            {
                'question': "Where can I find complete documentation?",
                'answer': "Run: python -m voice_mode.ptt.setup_helper --guide\n"
                         "Or visit: https://github.com/yourusername/chatta/blob/main/docs/ptt/README.md"
            },
        ]

    def get_help(self, topic: str) -> Optional[str]:
        """
        Get help for a specific topic.

        Args:
            topic: Topic name

        Returns:
            Formatted help text or None
        """
        help_topic = self.topics.get(topic)

        if not help_topic:
            return None

        lines = [
            "=" * 70,
            help_topic.title,
            "=" * 70,
            "",
            help_topic.content.strip(),
            ""
        ]

        if help_topic.related_topics:
            lines.extend([
                "",
                "Related Topics:",
                "  " + ", ".join(help_topic.related_topics)
            ])

        if help_topic.doc_url:
            lines.extend([
                "",
                f"Documentation: {help_topic.doc_url}"
            ])

        lines.append("=" * 70)

        return "\n".join(lines)

    def list_topics(self) -> str:
        """
        List all available help topics.

        Returns:
            Formatted topic list
        """
        lines = [
            "PTT Help Topics",
            "=" * 70,
            ""
        ]

        for topic_key, topic in sorted(self.topics.items()):
            lines.append(f"  {topic_key:20} - {topic.title}")

        lines.extend([
            "",
            "Get help on a topic:",
            "  python -c \"from voice_mode.ptt import get_help; print(get_help('topic_name'))\"",
            "",
            "=" * 70
        ])

        return "\n".join(lines)

    def get_faq(self) -> str:
        """
        Get formatted FAQ.

        Returns:
            Formatted FAQ text
        """
        lines = [
            "PTT Frequently Asked Questions",
            "=" * 70,
            ""
        ]

        for i, item in enumerate(self.faq, 1):
            lines.extend([
                f"Q{i}: {item['question']}",
                "",
                f"A: {item['answer']}",
                "",
                "-" * 70,
                ""
            ])

        lines.append("=" * 70)

        return "\n".join(lines)

    def search_help(self, query: str) -> List[str]:
        """
        Search help topics and FAQ for query.

        Args:
            query: Search query

        Returns:
            List of matching topic keys
        """
        query = query.lower()
        matches = []

        # Search topics
        for topic_key, topic in self.topics.items():
            if (query in topic_key.lower() or
                query in topic.title.lower() or
                query in topic.content.lower()):
                matches.append(topic_key)

        return matches


# Global help system instance
_help_system: Optional[PTTHelpSystem] = None


def get_help_system() -> PTTHelpSystem:
    """
    Get global PTT help system instance.

    Returns:
        PTTHelpSystem instance
    """
    global _help_system

    if _help_system is None:
        _help_system = PTTHelpSystem()

    return _help_system


def get_help(topic: str) -> str:
    """
    Get help for a topic.

    Args:
        topic: Topic name

    Returns:
        Formatted help text
    """
    help_system = get_help_system()
    help_text = help_system.get_help(topic)

    if help_text is None:
        return f"Help topic '{topic}' not found. Use list_help_topics() to see available topics."

    return help_text


def list_help_topics() -> str:
    """
    List all help topics.

    Returns:
        Formatted topic list
    """
    return get_help_system().list_topics()


def get_faq() -> str:
    """
    Get FAQ.

    Returns:
        Formatted FAQ
    """
    return get_help_system().get_faq()


def search_help(query: str) -> str:
    """
    Search help for query.

    Args:
        query: Search query

    Returns:
        Formatted search results
    """
    help_system = get_help_system()
    matches = help_system.search_help(query)

    if not matches:
        return f"No help topics found for '{query}'"

    lines = [
        f"Help topics matching '{query}':",
        "=" * 70,
        ""
    ]

    for topic_key in matches:
        topic = help_system.topics[topic_key]
        lines.append(f"  {topic_key:20} - {topic.title}")

    lines.extend([
        "",
        "View a topic:",
        "  get_help('topic_name')",
        ""
    ])

    return "\n".join(lines)


def print_help(topic: str):
    """Print help for a topic."""
    print(get_help(topic))


def print_faq():
    """Print FAQ."""
    print(get_faq())


def print_help_topics():
    """Print list of help topics."""
    print(list_help_topics())
