import os
import logging
import pyautogui
from autobyteus.tools.weibo.ocr import locate_word_on_screen
from autobyteus.tools.weibo.template_matching import locate_template_on_screen

class ImageUploader:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def locate_and_click_downloads_folder(self, screenshot):
        position, _ = locate_template_on_screen("downloads_folder_button.png", screenshot, occurrence=1)
        if position:
            x, y = position
            pyautogui.click(x, y)
            self.logger.info("Clicked on the Downloads folder.")
        else:
            raise Exception("Could not locate the Downloads folder on the screen.")
    
    async def locate_and_upload_image(self, screenshot):
        position, _ = locate_template_on_screen("open_file_button_template.png", screenshot, occurrence=1)
        if position:
            x, y = position
            pyautogui.doubleClick(x, y)
            self.logger.info(f"Double-clicked on the 'Open' button.")
        else:
            raise Exception(f"Could not locate the 'Open' button in the file dialog.")