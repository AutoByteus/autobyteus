"""
Description: This module provides utility functions for working with input messages and waiting for clipboard content changes.
"""

import pynput
from colorama import Fore, Style, init
import sys
import pyperclip

init(autoreset=True)

_current_line = ""
_message_lines = []
_shift_pressed = False
_ctrl_pressed = False
_user_confirmation_char = ""

def get_input_message():
    """
    Collects user input as a multi-line string.

    Returns:
        str: The user input message as a multi-line string.
    """
    global _message_lines
    print(Fore.GREEN + "INPUT: Start typing your message (press Enter to send):" + Style.RESET_ALL)

    with pynput.keyboard.Listener(on_release=_on_key_release, on_press=_on_key_press) as listener:
        listener.join()

    message = "\n".join(_message_lines)
    _message_lines = []  # Reset the _message_lines for future calls
    return message

def get_input_character(prompt):
    """
    Collects a single character input from the user.

    Args:
        prompt (str): The prompt to display to the user.

    Returns:
        str: The user input character as a lowercase string.
    """
    global _user_confirmation_char
    _user_confirmation_char = ""
    print(prompt, end='', flush=True)
    with pynput.keyboard.Listener(on_release=_on_key_release_single_char) as listener:
        listener.join()
    return _user_confirmation_char

def _on_key_release_single_char(key):
    """
    Handles key releases in single character input mode and waits for the user to press Enter.

    Args:
        key: The key released by the user.
    """
    global _user_confirmation_char

    if isinstance(key, pynput.keyboard.KeyCode):
        char = key.char.lower()
        _user_confirmation_char = char
    elif key == pynput.keyboard.Key.enter:
        return False

def _on_key_press(key):
    """
    Handles key presses and tracks the states of the Shift and Ctrl keys.

    Args:
        key: The key pressed by the user.
    """
    global _shift_pressed, _ctrl_pressed
    if key == pynput.keyboard.Key.shift:
        _shift_pressed = True
    if key == pynput.keyboard.Key.ctrl_l or key == pynput.keyboard.Key.ctrl_r:
        _ctrl_pressed = True

def _on_key_release(key):
    """
    Handles key releases and manages input message composition.

    Args:
        key: The key released by the user.
    """
    global _current_line, _message_lines, _shift_pressed, _ctrl_pressed

    if key == pynput.keyboard.Key.enter and not _shift_pressed:
        if _current_line:
            _message_lines.append(_current_line)
            _current_line = ""
        return False
    elif key == pynput.keyboard.Key.enter and _shift_pressed:
        _message_lines.append(_current_line)
        _current_line = ""
    elif key == pynput.keyboard.Key.backspace:
        _current_line = _current_line[:-1]
    elif key == pynput.keyboard.Key.shift:
        _shift_pressed = False
    elif key == pynput.keyboard.Key.ctrl_l or key == pynput.keyboard.Key.ctrl_r:
        _ctrl_pressed = False
    elif _ctrl_pressed and _shift_pressed and key == pynput.keyboard.KeyCode.from_char('V'):  # Handle the paste action
        pasted_text = pyperclip.paste()
        _current_line += pasted_text
        sys.stdout.write(pasted_text)
        sys.stdout.flush()
    elif key == pynput.keyboard.Key.space:  # Handle the space key
        _current_line += " "
    elif _ctrl_pressed and key == pynput.keyboard.KeyCode.from_char('c'):
        return 
    elif isinstance(key, pynput.keyboard.KeyCode):
        _current_line += key.char

