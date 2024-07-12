from bs4 import BeautifulSoup, Comment
import re

def clean(html_text):
    # Create a BeautifulSoup object
    soup = BeautifulSoup(html_text, 'html.parser')

    # Remove script and style tags
    for script in soup(['script', 'style']):
        script.decompose()

    # Remove comments
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove all style attributes
    for tag in soup.find_all(True):
        tag.attrs.pop('style', None)

    # Whitelist of attributes to keep
    whitelist_attrs = ['href']

    # Remove unnecessary attributes
    for tag in soup.find_all(True):
        attrs = dict(tag.attrs)
        for attr in attrs:
            if attr not in whitelist_attrs:
                del tag[attr]

    # Whitelist of tags to keep
    whitelist_tags = ['a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span', 'em', 'strong']

    # Remove unwanted tags
    for tag in soup.find_all(True):
        if tag.name not in whitelist_tags:
            tag.unwrap()

    # Return the cleaned HTML
    return str(soup)