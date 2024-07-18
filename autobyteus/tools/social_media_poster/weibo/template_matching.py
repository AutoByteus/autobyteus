import cv2
import numpy as np
import logging
import os

def locate_template_on_screen(template_name, screenshot, threshold=0.8, occurrence=1):
    """
    Locate a specific occurrence of a template on the screen.
    
    Args:
        template_name (str): The name of the template image file (should be in the same folder as this file).
        screenshot (numpy.ndarray): The screenshot image in BGR format.
        threshold (float): The matching threshold (0 to 1).
        occurrence (int): Which occurrence of the template to return (1-based index).
    
    Returns:
        tuple: ((x, y), total_occurrences) where (x, y) are the coordinates of the center of the template if found,
               and total_occurrences is the number of template occurrences found. Returns (None, total_occurrences) if the
               specific occurrence is not found.
    
    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    # Get the path to the template image file (assuming it's in the same folder as this file)
    template_path = os.path.join(os.path.dirname(__file__)+"/images", template_name)

    # Check if the template file exists
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found: {template_path}")

    # Load the template image
    template = cv2.imread(template_path)

    # Perform template matching
    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)

    # Extract the coordinates of matched regions
    matches = []
    for loc in zip(*locations[::-1]):
        x, y = loc
        w, h = template.shape[1], template.shape[0]
        center_x = x + w // 2
        center_y = y + h // 2
        matches.append((center_x, center_y))
        logging.info(f"Template found at: ({center_x}, {center_y})")

    total_occurrences = len(matches)
    logging.info(f"Total occurrences of the template found: {total_occurrences}")

    # Return the specified occurrence if it exists
    if 0 < occurrence <= total_occurrences:
        return matches[occurrence - 1], total_occurrences
    else:
        logging.info(f"No {occurrence}th occurrence of the template found on the screen.")
        return None, total_occurrences