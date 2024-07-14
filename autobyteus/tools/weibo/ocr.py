import cv2
import pytesseract
import numpy as np
import logging
import difflib

def preprocess_image(image):
    """
    Preprocess the image to improve OCR accuracy.
    
    Args:
        image (numpy.ndarray): The original image in BGR format.
    
    Returns:
        numpy.ndarray: The preprocessed binary image.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply adaptive thresholding to handle varying background colors
    binary_image = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Invert the image if necessary (white text on black background)
    if np.mean(binary_image) > 127:
        binary_image = cv2.bitwise_not(binary_image)

    # Remove noise (optional)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel)

    return binary_image

def is_word_similar(word1, word2, threshold=0.7):
    """
    Check if two words are similar using difflib's SequenceMatcher.
    
    Args:
        word1 (str): First word to compare.
        word2 (str): Second word to compare.
        threshold (float): Similarity threshold (0 to 1).
    
    Returns:
        bool: True if words are similar, False otherwise.
    """
    similarity = difflib.SequenceMatcher(None, word1.lower(), word2.lower()).ratio()
    return similarity >= threshold

def locate_word_on_screen(target_word, screenshot, similarity_threshold=0.7, occurrence=1):
    """
    Locate a specific occurrence of a word on the screen, allowing for slight OCR inaccuracies.
    
    Args:
        target_word (str): The word to locate on the screen.
        screenshot (numpy.ndarray): The screenshot image in BGR format.
        similarity_threshold (float): Threshold for word similarity (0 to 1).
        occurrence (int): Which occurrence of the word to return (1-based index).
    
    Returns:
        tuple: ((x, y), total_occurrences) where (x, y) are the coordinates of the center of the word if found, 
               and total_occurrences is the number of similar words found. Returns (None, total_occurrences) if the 
               specific occurrence is not found.
    """


    # Perform OCR on the preprocessed screenshot
    text_data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)

    # Find all positions of the target word
    matches = []
    for i, word in enumerate(text_data['text']):
        if is_word_similar(word, target_word, similarity_threshold):
            x = text_data['left'][i]
            y = text_data['top'][i]
            w = text_data['width'][i]
            h = text_data['height'][i]
            center_x = x + w // 2
            center_y = y + h // 2
            matches.append((center_x, center_y))
            logging.info(f"Word similar to '{target_word}' found at: ({center_x}, {center_y})")

    total_occurrences = len(matches)
    logging.info(f"Total occurrences of words similar to '{target_word}' found: {total_occurrences}")

    # Return the specified occurrence if it exists
    if 0 < occurrence <= total_occurrences:
        return matches[occurrence - 1], total_occurrences
    else:
        logging.info(f"No {occurrence}th occurrence of word similar to '{target_word}' found on the screen.")
        return None, total_occurrences