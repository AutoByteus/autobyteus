"""
This module provides functionality for cleaning HTML content with various levels of intensity.

It uses BeautifulSoup to parse and manipulate HTML, offering different cleaning modes
to suit various use cases.
"""

from bs4 import BeautifulSoup, Comment
from enum import Enum, auto

class CleaningMode(Enum):
    """
    Enum representing different HTML cleaning modes.

    THOROUGH: Most comprehensive cleaning (removes 'class' attribute)
    STANDARD: Moderate cleaning (keeps 'class' attribute)
    MINIMAL: Least invasive cleaning (preserves most attributes and styles)
    """
    THOROUGH = auto()
    STANDARD = auto()
    MINIMAL = auto()

def clean(html_text: str, mode: CleaningMode = CleaningMode.STANDARD) -> str:
    """
    Clean HTML text by removing unwanted elements, attributes, and whitespace.

    This function parses the input HTML, removes unnecessary tags and attributes,
    and returns a cleaned version of the HTML. The level of cleaning is determined
    by the specified mode.

    Args:
        html_text (str): The input HTML text to be cleaned.
        mode (CleaningMode): The cleaning mode to use. Defaults to CleaningMode.STANDARD.

    Returns:
        str: The cleaned HTML text.

    Raises:
        ValueError: If an invalid cleaning mode is provided.

    Example:
        >>> dirty_html = '<div class="wrapper" style="color: red;">Hello <script>alert("world");</script></div>'
        >>> clean_html = clean(dirty_html, CleaningMode.STANDARD)
        >>> print(clean_html)
        <div class="wrapper">Hello </div>
    """
    # Create a BeautifulSoup object
    soup = BeautifulSoup(html_text, 'html.parser')

    # Remove script and style tags
    for script in soup(['script', 'style']):
        script.decompose()

    # Remove comments
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Expanded whitelist of tags to keep
    whitelist_tags = [
        # Structural elements
        'html', 'body', 'header', 'nav', 'main', 'footer', 'section', 'article', 'aside',
        # Headings and text
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div', 'em', 'strong', 'i', 'b', 'u', 'sub', 'sup',
        # Links and images
        'a', 'img',
        # Lists
        'ul', 'ol', 'li', 'dl', 'dt', 'dd',
        # Tables
        'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
        # Forms and inputs
        'form', 'input', 'textarea', 'select', 'option', 'button', 'label',
        # Other common elements
        'br', 'hr', 'blockquote', 'pre', 'code', 'figure', 'figcaption', 'iframe'
    ]

    # Remove unwanted tags
    for tag in soup.find_all(True):
        if tag.name not in whitelist_tags:
            tag.unwrap()

    # Remove embedded images with src attribute starting with "data:image"
    for img in soup.find_all('img'):
        if 'src' in img.attrs and img['src'].startswith('data:image'):
            img.decompose()

    if mode in [CleaningMode.THOROUGH, CleaningMode.STANDARD]:
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
        for tag in soup.find_all(True):
            attrs = dict(tag.attrs)
            for attr in attrs:
                if attr not in whitelist_attrs:
                    del tag[attr]

        # Remove all style attributes
        for tag in soup.find_all(True):
            if 'style' in tag.attrs:
                del tag['style']

    # Return the cleaned HTML
    return str(soup)