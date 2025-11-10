# Platform Permission Requirements for PTT
Date: November 9, 2025
Sprint: 1.2

## Overview
Global keyboard monitoring requires different permissions across platforms. This document outlines requirements and user flows for each OS.

## macOS

### Requirements
- **Accessibility Permissions** required for keyboard monitoring
- Cannot be requested programmatically (Apple TCC policy)
- User must manually grant through System Preferences

### User Flow
1. First PTT attempt triggers macOS permission dialog
2. User directed to: System Preferences → Security & Privacy → Privacy → Accessibility
3. User must add Terminal/iTerm/IDE to allowed apps
4. Application restart may be required

### Detection & Handling
```python
import platform
import subprocess

def check_macos_accessibility():
    """Check if we have accessibility permissions on macOS"""
    if platform.system() != "Darwin":
        return True

    try:
        # Test if we can create a listener
        from pynput import keyboard
        test_listener = keyboard.Listener(on_press=lambda k: None)
        test_listener.start()
        test_listener.stop()
        return True
    except Exception:
        return False

def request_macos_permission():
    """Guide user to grant permissions"""
    print("""
    🔐 Accessibility Permission Required

    To use Push-to-Talk, please grant accessibility permissions:

    1. Open System Preferences
    2. Go to Security & Privacy → Privacy → Accessibility
    3. Click the lock to make changes
    4. Add this terminal/application to the list
    5. Restart the application

    Opening System Preferences now...
    """)

    subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])
```

### Fallback Strategy
- If permissions denied: Revert to standard voice mode
- Show clear message about PTT unavailable
- Provide instructions to enable later

## Windows

### Requirements
- **No elevation required** for keyboard monitoring
- Works in standard user context
- May trigger Windows Defender SmartScreen on first run

### User Flow
1. PTT works immediately - no permissions needed
2. If SmartScreen warning: User clicks "More info" → "Run anyway"
3. No restart required

### Detection & Handling
```python
def check_windows_permissions():
    """Windows doesn't require special permissions for pynput"""
    return True

def handle_windows_defender():
    """Inform user about potential SmartScreen warning"""
    print("""
    ℹ️ Windows Defender Note

    On first use, Windows may show a SmartScreen warning.
    This is normal for keyboard monitoring software.

    If prompted:
    1. Click "More info"
    2. Click "Run anyway"

    This only happens once.
    """)
```

## Linux

### Requirements
- **X11**: Works without elevation
- **Wayland**: May require additional configuration
- User must be in `input` group for some distros

### User Flow

#### X11 (Most desktop environments)
1. PTT works immediately in most cases
2. No special permissions needed

#### Wayland
1. May not work by default
2. User may need to:
   - Switch to X11 session, OR
   - Install additional packages (e.g., `ydotool`)

### Detection & Handling
```python
import os

def check_linux_permissions():
    """Check Linux display server and permissions"""
    display_server = os.environ.get('XDG_SESSION_TYPE', 'x11')

    if display_server == 'wayland':
        print("""
        ⚠️ Wayland Detected

        Push-to-Talk may have limited support on Wayland.

        Options:
        1. Switch to an X11 session for full support
        2. Install ydotool for Wayland support:
           sudo apt install ydotool  # Ubuntu/Debian
           sudo dnf install ydotool  # Fedora
        """)
        return False

    # Check if user is in input group (some distros)
    import grp
    import pwd
    username = pwd.getpwuid(os.getuid()).pw_name
    groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]

    if 'input' not in groups:
        print("""
        ℹ️ Input Group Membership

        For better device access, add yourself to the input group:
        sudo usermod -a -G input $USER

        Then log out and back in.
        """)

    return True
```

## Permission Flow Matrix

| Platform | Elevation Required | User Action Required | Programmatic Request | Fallback Available |
|----------|-------------------|---------------------|---------------------|-------------------|
| macOS | No | Yes (Manual) | No | Yes |
| Windows | No | No* | N/A | Yes |
| Linux/X11 | No | No | N/A | Yes |
| Linux/Wayland | No | Maybe | N/A | Yes |

*May show SmartScreen warning on first run

## Unified Permission Handler

```python
class PermissionManager:
    """Unified permission handling for PTT across platforms"""

    def __init__(self):
        self.platform = platform.system()
        self.has_permission = False

    async def check_permissions(self) -> bool:
        """Check if we have necessary permissions"""
        if self.platform == "Darwin":
            return check_macos_accessibility()
        elif self.platform == "Windows":
            return check_windows_permissions()
        elif self.platform == "Linux":
            return check_linux_permissions()
        return False

    async def request_permissions(self) -> None:
        """Guide user through permission granting"""
        if self.platform == "Darwin":
            request_macos_permission()
        elif self.platform == "Windows":
            handle_windows_defender()
        elif self.platform == "Linux":
            # Linux usually doesn't need permission request
            pass

    def get_fallback_message(self) -> str:
        """Get platform-specific fallback message"""
        messages = {
            "Darwin": "PTT unavailable. Grant accessibility permissions to enable.",
            "Windows": "PTT unavailable. Check Windows Defender settings.",
            "Linux": "PTT unavailable. Check display server compatibility."
        }
        return messages.get(self.platform, "PTT unavailable on this platform.")
```

## User Communication Strategy

### First-Time Setup
1. Detect PTT request
2. Check permissions
3. If missing: Show platform-specific instructions
4. Guide through permission process
5. Offer to continue without PTT

### Permission Denied
1. Log permission status
2. Show clear message
3. Provide instructions for later
4. Fall back to standard mode
5. Reminder in statistics/info commands

### Success Flow
1. Permissions granted
2. Show success message
3. Brief tutorial on key combinations
4. Begin PTT session

## Security Considerations

### User Trust
- Explain WHY permissions are needed
- Link to documentation
- Show exactly what will be monitored
- Provide privacy policy reference

### Minimal Permissions
- Only request what's needed
- Don't persist beyond session
- Clear data on exit
- No keylogging beyond PTT keys

## Implementation Notes

1. **Always provide fallback** - Never block user from voice features
2. **Clear messaging** - Explain permissions in simple terms
3. **One-time setup** - Remember permission status
4. **Platform detection** - Automatic, no user config needed
5. **Graceful degradation** - PTT optional enhancement