"""
This module provides functionality for cleaning HTML content with various levels of intensity.

It uses BeautifulSoup to parse and manipulate HTML, offering different cleaning modes
to suit various use cases. Empty tags are removed in all cleaning modes except NONE.
"""

from bs4 import BeautifulSoup, Comment
from enum import Enum, auto
import re

class CleaningMode(Enum):
    """
    Enum representing different HTML cleaning modes.

    NONE: No cleaning, returns the input HTML as-is
    ULTIMATE: Most aggressive cleaning (removes container tags)
    TEXT_CONTENT_FOCUSED: Extracts only text content, removing all HTML tags
    THOROUGH: Comprehensive cleaning (removes 'class' attribute)
    STANDARD: Moderate cleaning (keeps 'class' attribute)
    MINIMAL: Least invasive cleaning (preserves most attributes and styles)
    GOOGLE_SEARCH_RESULT: Specific mode for cleaning Google search results

    Note: All modes except NONE remove empty tags.
    """
    NONE = auto()
    ULTIMATE = auto()
    TEXT_CONTENT_FOCUSED = auto()
    THOROUGH = auto()
    STANDARD = auto()
    MINIMAL = auto()
    GOOGLE_SEARCH_RESULT = auto()

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

def clean_whitespace(text):
    """
    Clean up whitespace in the given text.

    Args:
        text (str): The input text to clean.

    Returns:
        str: The text with cleaned up whitespace.
    """
    # Replace multiple whitespace characters with a single space
    text = re.sub(r'\s+', ' ', text)
    # Remove leading and trailing whitespace
    text = text.strip()
    return text

def clean_google_search_result(soup):
    """
    Clean HTML specifically for Google search results.

    This function keeps <a> tags with their href attributes and all text content,
    while removing all other HTML elements and attributes.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object to clean.

    Returns:
        str: The cleaned HTML string.
    """
    # Find all <a> tags
    links = soup.find_all('a')
    
    # Create a new soup with only the desired content
    new_soup = BeautifulSoup('<div></div>', 'html.parser')
    container = new_soup.div

    # Set to keep track of text content already added from links
    added_text = set()

    for link in links:
        # Create a new <a> tag with only the href attribute
        new_a = new_soup.new_tag('a')
        if 'href' in link.attrs:
            new_a['href'] = link['href']
        
        # Add the text content of the original link
        link_text = link.get_text(strip=True)
        new_a.string = link_text
        added_text.add(link_text)
        
        # Add the new <a> tag to the container
        container.append(new_a)
        container.append(' ')

    # Add any remaining text that's not within <a> tags
    for text in soup.stripped_strings:
        if text not in added_text:
            container.append(text + ' ')

    # Clean whitespace and remove empty tags
    remove_empty_tags(container)
    return clean_whitespace(str(container))

def clean(html_text: str, mode: CleaningMode = CleaningMode.STANDARD) -> str:
    """
    Clean HTML text by removing unwanted elements, attributes, empty tags, and whitespace.

    This function parses the input HTML, removes unnecessary tags and attributes,
    empty tags, and returns a cleaned version of the HTML. The level of cleaning is determined
    by the specified mode. Empty tags are removed in all modes except NONE.

    For TEXT_CONTENT_FOCUSED mode, all HTML tags are removed, and only the text content is returned.
    For NONE mode, the input HTML is returned as-is without any cleaning.
    For GOOGLE_SEARCH_RESULT mode, only <a> tags with href attributes and text content are preserved.

    Args:
        html_text (str): The input HTML text to be cleaned.
        mode (CleaningMode): The cleaning mode to use. Defaults to CleaningMode.STANDARD.

    Returns:
        str: The cleaned HTML text, plain text (for TEXT_CONTENT_FOCUSED mode),
             or original HTML (for NONE mode).

    Raises:
        ValueError: If an invalid cleaning mode is provided.

    Example:
        >>> dirty_html = '<html><body><div class="wrapper" style="color: red;">Hello <script>alert("world");</script><p></p></div></body></html>'
        >>> clean_html = clean(dirty_html, CleaningMode.TEXT_CONTENT_FOCUSED)
        >>> print(clean_html)
        Hello
    """
    # Handle NONE mode
    if mode == CleaningMode.NONE:
        return html_text

    # Create a BeautifulSoup object
    soup = BeautifulSoup(html_text, 'html.parser')

    # Handle TEXT_CONTENT_FOCUSED mode separately
    if mode == CleaningMode.TEXT_CONTENT_FOCUSED:
        # Extract only text content, stripping all HTML tags
        text_content = soup.get_text(separator=' ', strip=True)
        return clean_whitespace(text_content)

    # Handle GOOGLE_SEARCH_RESULT mode
    if mode == CleaningMode.GOOGLE_SEARCH_RESULT:
        return clean_google_search_result(soup)

    # For other modes, proceed with the existing cleaning logic
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
            if mode == CleaningMode.ULTIMATE:
                tag.unwrap()  # Keep the content of removed tags
            else:
                tag.decompose()  # Remove the tag and its content

    # Remove embedded images with src attribute starting with "data:image"
    for img in content.find_all('img'):
        if 'src' in img.attrs and img['src'].startswith('data:image'):
            img.decompose()

    if mode in [CleaningMode.ULTIMATE, CleaningMode.THOROUGH, CleaningMode.STANDARD]:
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
    return clean_whitespace(''.join(str(child) for child in content.children))