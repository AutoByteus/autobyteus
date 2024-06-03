from bs4 import BeautifulSoup, Comment
import re

def clean(html_text):
    # Create a BeautifulSoup object
    soup = BeautifulSoup(html_text, 'html.parser')

    # Remove script and style tags
    for script in soup(['script', 'style']):
        script.decompose()

    # Remove inline styles
    for tag in soup.find_all():
        tag.attrs['style'] = '' if 'style' in tag.attrs else None

    # Remove comments
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Preserve CSS classes and IDs
    for tag in soup.find_all():
        if 'class' in tag.attrs:
            tag['class'] = re.sub(r'\s+', ' ', tag['class'])
        if 'id' in tag.attrs:
            tag['id'] = re.sub(r'\s+', ' ', tag['id'])

    # Return the cleaned HTML
    return str(soup)
