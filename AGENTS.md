# AGENTS.md

## Build / Lint / Test Commands

### Installation
```bash
# Setup virtual environment (make sure to use Python 3.12)
make setup
# or manually:
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Running the Application
```bash
# Run with UI (recommended)
python -m src.main

# Run without UI
python -m src.engine.MapleStoryAutoLevelUp

# Run with custom config
python -m src.engine.MapleStoryAutoLevelUp --cfg custom

# Run specific map presets (see Makefile for more)
python -m src.engine.MapleStoryAutoLevelUp --map cloud_balcony --cfg custom
```

### Running Tests
```bash
# Run Arduino HID tests
python tests/test_arduino_hid.py

# Run with specific port
python tests/test_arduino_hid.py --port COM3

# Quick test (connection + heartbeat only)
python tests/test_arduino_hid.py --quick

# List available serial ports
python tests/test_arduino_hid.py --list
```

### Building Executable
```bash
# Build standalone executable
build.bat

# Manual build with PyInstaller
pyinstaller --noconsole --onefile src/main.py -p . --icon=media/icon.ico -n MapleStoryAutoLevelUp --hidden-import=pkg_resources.py2_warn --hidden-import=pkg_resources.extern
```

---

## Code Style Guidelines

### Import Order (STRICT)
All Python files must follow this exact import order with section separators:
```python
# Standard Import
import time
import os
import sys
from collections import defaultdict

# Library Import
import numpy as np
import cv2
import yaml
from PySide6.QtWidgets import QApplication

# macOS Import (platform-specific)
if platform.system() == 'Darwin':
    import Quartz
else:
    import win32gui
    import win32con

# Local Import
from src.utils.logger import logger
from src.utils.common import load_yaml, is_mac
from src.input.KeyBoardController import KeyBoardController
```

### Naming Conventions
- **Classes**: PascalCase (e.g., `MapleStoryAutoBot`, `HealthMonitor`, `ArduinoHIDBackend`)
- **Functions/Methods**: snake_case (e.g., `update_cmd_by_route`, `get_player_location`)
- **Private methods**: _snake_case (e.g., `_monitor_loop`, `_heal`)
- **Variables**: snake_case (e.g., `img_frame`, `hp_percent`, `loc_player`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `WINDOW_WORKING_SIZE`, `SCAN_CODES`)
- **Config keys**: snake_case (e.g., `key_duration_base`, `search_range`)

### Type Hints
Use type hints for clarity, especially for function signatures:
```python
def process_command(self, cmd: str) -> bool:
    """Process a command and return success status."""
    pass

from typing import Optional, List, Tuple, Callable

def get_location(self) -> Optional[Tuple[int, int]]:
    """Get player location or None if not found."""
    pass
```

### Docstrings
Use triple quotes for docstrings. Keep them concise:
```python
def update_cmd_by_route(self):
    '''
    Update movement commands based on route map color codes.
    Reads nearest color pixel around player and sets corresponding command.
    '''
    pass
```

### Error Handling
- Use logger for all errors/warnings
- Return None, -1, or False on failure (check documentation for expected return type)
- Use try-except for expected exceptions, especially I/O operations:
```python
try:
    self.capture = GameWindowCapturor(self.cfg)
except Exception as e:
    logger.error(f"[load_config] Failed to initialize capture: {e}")
    return -1
```

### Threading
- Always use `daemon=True` for background threads
- Use locks for shared resources:
```python
self.lock = threading.Lock()
with self.lock:
    # access shared data
```

### Configuration
- Never modify `config/config_default.yaml` directly
- Use `config/config_custom.yaml` for user settings
- Config values are accessed via dictionary: `self.cfg["bot"]["map"]`

### Platform Compatibility
- Use `is_mac()` or `is_windows()` from `src.utils.common` for platform checks
- Keep macOS-specific imports separate
- Game window title must match `cfg["game_window"]["title"]`

### Testing
- Tests are standalone scripts (not pytest-based yet)
- Use `logger` for test output, not `print()`
- Tests should be self-contained and clean up resources
- Use `try-finally` to ensure cleanup even on failure

### File Structure
- `/src/` - All application code
  - `/engine/` - Core game logic (FSM, state machines, main bot)
  - `/states/` - FSM state implementations (hunting, patrol, etc.)
  - `/input/` - Input backends (keyboard, mouse, Arduino HID)
  - `/ui/` - PySide6 UI components
  - `/utils/` - Utilities (logger, common functions, anti-detect)
- `/config/` - YAML configuration files
- `/tools/` - Utility scripts (route recorder, mob maker)
- `/arduino/` - Arduino firmware for HID backend
- `/tests/` - Test scripts

### Key Constants
- `WINDOW_WORKING_SIZE = (693, 1282)` - Working resolution (excludes title bar)
- Game must run in windowed mode at smallest resolution
- Minimap must be enabled in top-left corner
- Party red bar must be visible (create party to enable)

### Comments
- Use Chinese for detailed comments explaining complex logic
- Keep comments minimal - prefer clear code over explanatory comments
- No inline comments for obvious code

### Anti-Detection Integration
- When adding keyboard input, always use `get_human_behavior()` for randomization
- Call `human.get_key_duration()` for variable press durations
- Use `human.should_micro_pause()` for occasional pauses
- All input goes through `src.input.InputBackend` abstraction layer
