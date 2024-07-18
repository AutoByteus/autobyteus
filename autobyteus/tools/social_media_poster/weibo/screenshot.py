import cv2
import pyautogui
import numpy as np
import logging

def capture_screenshot():
    """
    Capture a screenshot of the entire screen.
    
    Returns:
        numpy.ndarray: The screenshot as a numpy array in BGR format.
    """
    try:
        screenshot = pyautogui.screenshot()
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    except Exception as e:
        logging.error(f"Error capturing screenshot: {str(e)}")
        return None

def save_screenshot(screenshot, filename):
    """
    Save the screenshot to a file.
    
    Args:
        screenshot (numpy.ndarray): The screenshot image in BGR format.
        filename (str): The name of the file to save the screenshot as.
    """
    try:
        cv2.imwrite(filename, screenshot)
        logging.info(f"Screenshot saved as {filename}")
    except Exception as e:
        logging.error(f"Error saving screenshot: {str(e)}")