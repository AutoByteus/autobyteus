#%% 
import asyncio
from playwright.async_api import async_playwright
from playwright.async_api import TimeoutError
import beep

import os
os.environ['DEBUG'] = 'pw:api, pw:browser'

async def run():
    user_data_dir = '/home/ryan/.config/microsoft-edge/Default'  # Replace with your actual user data directory path
    executable_path = '/usr/bin/microsoft-edge-stable'  # Replace with the path to your Edge executable

    async with async_playwright() as playwright:
        await automate_bing_actions(playwright, user_data_dir, executable_path)

async def automate_bing_actions(playwright, user_data_dir, executable_path):
    context = await playwright.chromium.launch_persistent_context(user_data_dir, executable_path=executable_path, headless=False)
    page = await context.new_page()
    await page.goto('https://www.bing.com')

    await accept_cookies_if_present(page)
    await navigate_to_chat(page)
    await login_if_needed(page, "username", "password")  # Replace 'username' and 'password' with the actual username and password
    await locate_input_and_type_text(page, "hello")
    await page.close()
    await context.close()

async def accept_cookies_if_present(page):
    accept_button_selector = '#bnp_btn_accept'
    try:
        await page.wait_for_selector(accept_button_selector, timeout=5000)
        await page.click(accept_button_selector)
        print("Clicked the Accept button.")
    except TimeoutError:
        print("Accept button did not appear. Continuing...")

async def navigate_to_chat(page):
    chat_link_selector = "a[href*='/search?q=Bing+AI'][class='customIcon']"
    await page.wait_for_selector(chat_link_selector, timeout=5000)
    await page.click(chat_link_selector)

async def login_if_needed(page, username, password):
    login_button_selector = "button.muid-cta"
    try:
        await page.wait_for_selector(login_button_selector, timeout=5000)
        await page.click(login_button_selector)
        await enter_credentials(page, username, password)
    except TimeoutError:
        print("Login button did not appear. User might already be logged in. Continuing...")

async def enter_credentials(page, username, password):
    username_input_selector = "input[type='email']"
    await page.wait_for_selector(username_input_selector, timeout=5000)
    await page.fill(username_input_selector, username)
    await page.keyboard.press('Enter')

    password_input_selector = "input[type='password']"
    await page.wait_for_selector(password_input_selector, timeout=5000)
    await page.fill(password_input_selector, password)
    await page.keyboard.press('Enter')

    submit_button_selector = "input[type='submit']"
    await page.wait_for_selector(submit_button_selector, timeout=5000)
    await page.click(submit_button_selector)


async def locate_input_and_type_text(page, text):
    # The selector for the input container
    input_container_selector = "div.input-container.as-ghost-placement"

    # Wait for the input container to be visible
    await page.wait_for_selector(input_container_selector, state="visible")

    # Play a beep sound
    beep.beep()

    # Click on the input container to focus it
    await page.click(input_container_selector)

    # Type the sample text into the input container
    await page.type(input_container_selector, text)

if __name__ == "__main__":
    asyncio.run(run())

#%% 
from gtts import gTTS

# Create a TTS object
tts = gTTS("I found a termin")

# Save the audio file
tts.save('successful.wav')

# %%
