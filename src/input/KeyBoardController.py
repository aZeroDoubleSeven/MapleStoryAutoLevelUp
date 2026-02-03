'''
KeyBoardController
Simulate user keyboard input to control character in the game

Supports multiple input backends:
- pyautogui: Default, uses Windows SendInput (easily detected)
- interception: Hardware-level simulation (recommended for anti-cheat bypass)
- ctypes_raw: Direct Windows API with hardware scancodes
'''
# Standard Import
import threading
import time
import random

# Library import
from pynput import keyboard

# Local import
from src.utils.logger import logger
from src.utils.common import is_mac
from src.utils.anti_detect import get_human_behavior, TimingRandomizer
from src.input.InputBackend import get_input_backend, init_input_backend

if is_mac():
    import Quartz
else:
    import pygetwindow as gw

# Global input backend instance
_input_backend = None

def _get_backend():
    '''Get or initialize the input backend'''
    global _input_backend
    if _input_backend is None:
        _input_backend = get_input_backend('auto')
    return _input_backend

def set_input_backend(cfg):
    '''Set the input backend from config'''
    global _input_backend
    _input_backend = init_input_backend(cfg)
    logger.info(f"[KeyBoardController] Using input backend: {_input_backend.get_name()}")

def key_down(key):
    '''
    Press key down with slight random delay
    '''
    try:
        # Add tiny random delay before key press to avoid detection
        human = get_human_behavior()
        time.sleep(human.get_action_delay() * 0.3)  # Smaller delay for key down
        _get_backend().key_down(key)
    except Exception as e:
        logger.warning(f"[key_down] Failed: {e}")

def key_up(key):
    '''
    Release key with slight random delay
    '''
    try:
        # Add tiny random delay before key release
        human = get_human_behavior()
        time.sleep(human.get_action_delay() * 0.2)  # Even smaller delay for key up
        _get_backend().key_up(key)
    except Exception as e:
        logger.warning(f"[key_up] Failed: {e}")

def press_key(key, duration=None):
    '''
    Simulates a key press for a randomized duration to mimic human behavior
    
    Args:
        key: The key to press
        duration: Base duration (will be randomized). If None, uses default with variance
    '''
    if key:
        human = get_human_behavior()
        
        # Get randomized duration
        actual_duration = human.get_key_duration(duration or 0.05)
        
        # Check for micro-pause before action
        should_pause, pause_duration = human.should_micro_pause()
        if should_pause:
            time.sleep(pause_duration)
        
        _get_backend().press_key(key, actual_duration)
        
        # Update fatigue tracking
        human.update_fatigue()


class KeyBoardController():
    '''
    KeyBoardController with multi-backend support
    '''
    def __init__(self, cfg):
        self.cfg = cfg
        self.cmd_action = "none"
        self.cmd_up_down = "none"
        self.cmd_left_right = "none"
        self.cmd_up_down_last = ""
        self.cmd_left_right_last = ""
        self.window_title = cfg["game_window"]["title"]
        self.fps = 0 # Frame per seconds
        # Timer
        self.t_last_up = 0.0
        self.t_last_down = 0.0
        self.t_last_toggle = 0.0
        self.t_last_screenshot = 0.0
        self.t_last_jump_down = 0.0
        self.t_last_run = time.time()
        self.t_last_skill = 0.0 # Last time character perform action(attack, cast spell, ...)
        self.t_last_buff_cast = [0] * len(self.cfg["buff_skill"]["keys"]) # Last time cast buff skill
        # Flags
        self.is_enable = True
        self.is_need_force_heal = False
        self.is_terminated = False
        # Parameters
        self.debounce_interval = self.cfg["system"]["key_debounce_interval"]
        self.fps_limit = self.cfg["system"]["fps_limit_keyboard_controller"]

        # Initialize input backend from config
        set_input_backend(cfg)

        # use 'ctrl', 'alt' for mac, because it's hard to get around
        # macOS's security settings
        if is_mac():
            self.toggle_key = keyboard.Key.ctrl
            self.screenshot_key = keyboard.Key.alt
            self.terminate_key = keyboard.Key.esc
        else:
            self.toggle_key = keyboard.Key.f1
            self.screenshot_key = keyboard.Key.f2
            self.terminate_key = keyboard.Key.f12

        # set up attack key
        self.attack_key = ""
        if cfg["bot"]["attack"] == "aoe_skill":
            self.attack_key = cfg["key"]["aoe_skill"]
        elif cfg["bot"]["attack"] == "directional":
            self.attack_key = cfg["key"]["directional_attack"]
        else:
            raise ValueError(f"Unexpected attack type: {cfg['bot']['attack']}")

        # Start keyboard control thread
        threading.Thread(target=self.run, daemon=True).start()

        logger.info(f"[KeyBoardController] Init done (backend: {_get_backend().get_name()})")

    def toggle_enable(self):
        '''
        toggle_enable
        '''
        self.is_enable = not self.is_enable
        logger.info(f"Player pressed F1, is_enable:{self.is_enable}")

        # Make sure all key are released
        self.release_all_key()

    def disable(self):
        '''
        disable keyboard controlller
        '''
        self.is_enable = False

    def enable(self):
        '''
        enable keyboard controlller
        '''
        self.is_enable = True

    def set_command(self, new_command):
        '''
        Set keyboard command
        '''
        self.cmd_left_right, self.cmd_up_down, self.cmd_action = new_command.split()

    def is_game_window_active(self):
        '''
        Check if the game window is currently the active (foreground) window.

        Returns:
        - True
        - False
        '''
        if is_mac():
            active_window = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID
            )
            for window in active_window:
                window_name = window.get(Quartz.kCGWindowName, '')
                if window_name and self.window_title in window_name:
                    return True
            return False
        else:
            try:
                active_window = gw.getActiveWindow()
                if not active_window:
                    return False
                return self.window_title in active_window.title
            except Exception as e:
                return False

    def release_all_key(self):
        '''
        Release all key
        '''
        key_up("left")
        key_up("right")
        key_up("up")
        key_up("down")
        # Also release attack keys to stop any ongoing attacks
        key_up(self.attack_key)

    def limit_fps(self):
        '''
        Limit FPS with slight randomization
        '''
        # If the loop finished early, sleep to maintain target FPS
        base_target = 1.0 / self.fps_limit
        # Add slight variance to FPS timing (±5%)
        target_duration = base_target * random.uniform(0.95, 1.05)
        frame_duration = time.time() - self.t_last_run
        if frame_duration < target_duration:
            time.sleep(target_duration - frame_duration)

        # Update FPS
        self.fps = round(1.0 / (time.time() - self.t_last_run))
        self.t_last_run = time.time()
        # logger.info(f"FPS = {self.fps}")

    def run(self):
        '''
        run
        '''
        human = get_human_behavior()
        
        while not self.is_terminated:
            # Check if game window is active
            if not self.is_enable or not self.is_game_window_active():
                self.limit_fps()
                continue

            # Occasional idle behavior to appear more human-like
            should_idle, idle_duration = human.should_idle()
            if should_idle:
                logger.debug(f"[KeyBoardController] Taking a brief pause ({idle_duration:.2f}s)")
                self.release_all_key()
                time.sleep(idle_duration)
                continue

            # Buff skill with randomized timing
            for i, buff_skill_key in enumerate(self.cfg["buff_skill"]["keys"]):
                base_cooldown = self.cfg["buff_skill"]["cooldown"][i]
                # Add variance to buff cooldown
                cooldown = human.randomize_cooldown(base_cooldown, 'buff')
                if time.time() - self.t_last_buff_cast[i] >= cooldown and \
                    time.time() - self.t_last_skill > self.cfg["buff_skill"]["action_cooldown"]:
                    # Add small random delay before casting buff
                    time.sleep(random.uniform(0.05, 0.15))
                    press_key(buff_skill_key)
                    logger.info(f"[Buff] Press buff skill key: '{buff_skill_key}' (cooldown: {cooldown:.2f}s)")
                    # Reset timers with slight randomization
                    self.t_last_buff_cast[i] = time.time() + random.uniform(-0.1, 0.1)
                    self.t_last_skill = time.time()
                    break

            # Force Heal
            if self.is_need_force_heal:
                self.cmd_action = "add_hp"

            ##########################
            ### Left-Right Command ###
            ##########################
            if self.cmd_left_right == "left":
                key_up("right")
                key_down("left")
            elif self.cmd_left_right == "right":
                key_up("left")
                key_down("right")
            elif self.cmd_left_right == "stop":
                key_up("left")
                key_up("right")
            elif self.cmd_left_right == "none":
                if self.cmd_left_right_last != "none":
                    key_up("left")
                    key_up("right")
            else:
                logger.error("[KeyBoardController] Unsupported left-right command: "
                             f"{self.cmd_left_right}")
            self.cmd_left_right_last = self.cmd_left_right

            #######################
            ### Up-Down Command ###
            #######################
            if self.cmd_up_down == "up":
                key_up("down")
                key_down("up")
            elif self.cmd_up_down == "down":
                key_up("up")
                key_down("down")
            elif self.cmd_up_down == "stop":
                key_up("up")
                key_up("down")
            elif self.cmd_up_down == "none":
                if self.cmd_up_down_last != "none":
                    key_up("up")
                    key_up("down")
            else:
                logger.error("[KeyBoardController] Unsupported up-down command: "
                             f"{self.cmd_up_down}")
            self.cmd_up_down_last = self.cmd_up_down

            ######################
            ### Action Command ###
            ######################
            if self.cmd_action == "jump":
                press_key(self.cfg["key"]["jump"])
            elif self.cmd_action == "teleport":
                press_key(self.cfg["key"]["teleport"])
            elif self.cmd_action == "attack":
                press_key(self.attack_key)
                self.t_last_skill = time.time()
            elif self.cmd_action == "add_hp":
                press_key(self.cfg["key"]["add_hp"])
                self.cmd_action = "none"  # Reset command
            elif self.cmd_action == "add_mp":
                press_key(self.cfg["key"]["add_mp"])
                self.cmd_action = "none"  # Reset command
            elif self.cmd_action == "goal":
                pass
            elif self.cmd_action == "none":
                pass
            else:
                logger.error("[KeyBoardController] Unsupported action command: "
                             f"{self.cmd_action}")

            self.limit_fps()

        self.release_all_key() # Prevent key keep press down after termination

        logger.info("[KeyBoardController] terminated")
