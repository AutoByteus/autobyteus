"""
This module provides functionality for cleaning HTML content with various levels of intensity.

It uses BeautifulSoup to parse and manipulate HTML, offering different cleaning modes
to suit various use cases. Empty tags are removed in all cleaning modes.
"""

from bs4 import BeautifulSoup, Comment
from enum import Enum, auto

class CleaningMode(Enum):
    """
    Enum representing different HTML cleaning modes.

    ULTIMATE: Most aggressive cleaning (removes container tags)
    TEXT_CONTENT_FOCUSED: Focuses on elements providing text content
    THOROUGH: Comprehensive cleaning (removes 'class' attribute)
    STANDARD: Moderate cleaning (keeps 'class' attribute)
    MINIMAL: Least invasive cleaning (preserves most attributes and styles)

    Note: All modes now remove empty tags.
    """
    ULTIMATE = auto()
    TEXT_CONTENT_FOCUSED = auto()
    THOROUGH = auto()
    STANDARD = auto()
    MINIMAL = auto()

def remove_empty_tags(element):
    """
    Recursively remove empty tags from a BeautifulSoup element.

    Args:
        element: A BeautifulSoup Tag or NavigableString object.

    Returns:
        bool: True if the element is empty (should be removed), False otherwise.
    """
    if isinstance(element, Comment):
        return True

    if isinstance(element, str) and not element.strip():
        return True

    if hasattr(element, 'contents'):
        children = element.contents[:]
        for child in children:
            if remove_empty_tags(child):
                child.extract()

    return len(element.get_text(strip=True)) == 0 and element.name not in ['br', 'hr', 'img']

def clean(html_text: str, mode: CleaningMode = CleaningMode.STANDARD) -> str:
    """
    Clean HTML text by removing unwanted elements, attributes, empty tags, and whitespace.

    This function parses the input HTML, removes unnecessary tags and attributes,
    empty tags, and returns a cleaned version of the HTML. The level of cleaning is determined
    by the specified mode, but empty tags are removed in all modes.

    Args:
        html_text (str): The input HTML text to be cleaned.
        mode (CleaningMode): The cleaning mode to use. Defaults to CleaningMode.STANDARD.

    Returns:
        str: The cleaned HTML text.

    Raises:
        ValueError: If an invalid cleaning mode is provided.

    Example:
        >>> dirty_html = '<html><body><div class="wrapper" style="color: red;">Hello <script>alert("world");</script><p></p></div></body></html>'
        >>> clean_html = clean(dirty_html, CleaningMode.TEXT_CONTENT_FOCUSED)
        >>> print(clean_html)
        Hello
    """
    # Create a BeautifulSoup object
    soup = BeautifulSoup(html_text, 'html.parser')

    # Focus on the body content if it exists, otherwise use the whole soup
    content = soup.body or soup

    # Remove script and style tags
    for script in content(['script', 'style']):
        script.decompose()

    # Remove comments
    for comment in content.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Define whitelist tags based on cleaning mode
    if mode == CleaningMode.ULTIMATE:
        whitelist_tags = [
            'p', 'span', 'em', 'strong', 'i', 'b', 'u', 'sub', 'sup',
            'a', 'img', 'br', 'hr', 'blockquote', 'pre', 'code',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'dl', 'dt', 'dd',
            'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td'
        ]
    elif mode == CleaningMode.TEXT_CONTENT_FOCUSED:
        whitelist_tags = [
            'p', 'span', 'em', 'strong', 'i', 'b', 'u', 'sub', 'sup',
            'a', 'blockquote', 'pre', 'code',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'dl', 'dt', 'dd',
            'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
            'div'  # Included for structural integrity, but will be unwrapped
        ]
    else:
        whitelist_tags = [
            'header', 'nav', 'main', 'footer', 'section', 'article', 'aside',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div', 'em', 'strong', 'i', 'b', 'u', 'sub', 'sup',
            'a', 'img',
            'ul', 'ol', 'li', 'dl', 'dt', 'dd',
            'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
            'form', 'input', 'textarea', 'select', 'option', 'button', 'label',
            'br', 'hr', 'blockquote', 'pre', 'code', 'figure', 'figcaption',
        ]

    # Remove or unwrap unwanted tags
    for tag in content.find_all(True):
        if tag.name not in whitelist_tags:
            if mode in [CleaningMode.ULTIMATE, CleaningMode.TEXT_CONTENT_FOCUSED]:
                tag.unwrap()  # Keep the content of removed tags
            else:
                tag.decompose()  # Remove the tag and its content
        elif mode == CleaningMode.TEXT_CONTENT_FOCUSED and tag.name == 'div':
            tag.unwrap()  # Unwrap div tags in TEXT_CONTENT_FOCUSED mode

    # Remove embedded images with src attribute starting with "data:image"
    for img in content.find_all('img'):
        if 'src' in img.attrs and img['src'].startswith('data:image'):
            img.decompose()

    if mode in [CleaningMode.ULTIMATE, CleaningMode.TEXT_CONTENT_FOCUSED, CleaningMode.THOROUGH, CleaningMode.STANDARD]:
        # Expanded whitelist of attributes to keep
        whitelist_attrs = [
            'href', 'src', 'alt', 'title', 'id', 'name', 'value', 'type', 'placeholder',
            'checked', 'selected', 'disabled', 'readonly', 'for', 'action', 'method', 'target',
            'width', 'height', 'colspan', 'rowspan', 'lang'
        ]

        # Add 'class' to whitelist_attrs for STANDARD mode
        if mode == CleaningMode.STANDARD:
            whitelist_attrs.append('class')

        # Remove unnecessary attributes
        for tag in content.find_all(True):
            attrs = dict(tag.attrs)
            for attr in attrs:
                if attr not in whitelist_attrs:
                    del tag[attr]

        # Remove all style attributes
        for tag in content.find_all(True):
            if 'style' in tag.attrs:
                del tag['style']

    # Remove empty tags for all modes
    remove_empty_tags(content)

    # Return the cleaned HTML
    return ''.join(str(child) for child in content.children).strip()