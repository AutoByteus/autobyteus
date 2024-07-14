from bs4 import BeautifulSoup, Comment
import re

def clean(html_text, lite=False):
    """
    Clean HTML text by removing unwanted elements, attributes, and whitespace.

    Args:
        html_text (str): The input HTML text to be cleaned.
        lite (bool): If True, perform a lite cleaning that preserves attributes and styles.
                     If False (default), perform a more thorough cleaning.

    Returns:
        str: The cleaned HTML text.
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

    if not lite:
        # Thorough cleaning mode
        # Expanded whitelist of attributes to keep
        whitelist_attrs = [
            'href', 'src', 'alt', 'title', 'id', 'class', 'name', 'value', 'type', 'placeholder',
            'checked', 'selected', 'disabled', 'readonly', 'for', 'action', 'method', 'target',
            'width', 'height', 'colspan', 'rowspan', 'lang'
        ]

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