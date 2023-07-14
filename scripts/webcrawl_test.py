"""
This module contains tools for web crawling and web searching.
"""

import requests
from bs4 import BeautifulSoup
from pyppeteer import launch
import asyncio

def crawl_webpage(url):
    """
    Fetch the content of a webpage given its URL.

    Args:
        url (str): The URL of the webpage.

    Returns:
        str: The text content of the webpage.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup.get_text()

async def search_google(query):
    """
    Perform a Google search and return the URLs of the search results.

    Args:
        query (str): The search query.

    Returns:
        list: The URLs of the search results.
    """
    browser = await launch()
    page = await browser.newPage()
    await page.goto('https://www.google.com')
    await page.type('input[name=q]', query)
    await page.keyboard.press('Enter')
    await page.waitForNavigation()

    elements = await page.querySelectorAll('.g .r a')
    urls = [await page.evaluate('(element) => element.href', element) for element in elements]

    await browser.close()
    
    return urls


print(crawl_webpage('https://python.langchain.com/docs/modules/data_connection/document_loaders/integrations/url'))