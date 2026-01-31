"""
TikTok Message Bot

A bot for automating TikTok messaging using Selenium WebDriver.
"""

import logging
import os
import tempfile
import time
from contextlib import contextmanager
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_firefox_options(headless: bool = True, profile_path: Optional[str] = None) -> FirefoxOptions:
    """
    Set up Firefox options for the WebDriver.
    
    Args:
        headless: Whether to run Firefox in headless mode
        profile_path: Optional path to Firefox profile directory
    
    Returns:
        FirefoxOptions: Configured Firefox options
    """
    options = FirefoxOptions()
    
    if headless:
        options.add_argument('--headless')
    
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # Set preferences to avoid detection
    options.set_preference('dom.webdriver.enabled', False)
    options.set_preference('useAutomationExtension', False)
    
    if profile_path:
        options.add_argument(f'-profile={profile_path}')
    
    return options


def wait_for_page_load(driver, timeout: int = 30) -> bool:
    """
    Wait for page to be fully loaded.
    
    Args:
        driver: WebDriver instance
        timeout: Maximum time to wait in seconds
    
    Returns:
        bool: True if page loaded successfully, False otherwise
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        return True
    except TimeoutException:
        logger.warning("Page load timeout")
        return False


def login_to_tiktok(driver, username: str, password: str) -> bool:
    """
    Log in to TikTok.
    
    Args:
        driver: WebDriver instance
        username: TikTok username or email
        password: TikTok password
    
    Returns:
        bool: True if login successful, False otherwise
    """
    try:
        logger.info("Navigating to TikTok login page")
        driver.get("https://www.tiktok.com/login")
        
        wait = WebDriverWait(driver, 20)
        
        # Wait for login form
        logger.info("Waiting for login form")
        username_input = wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        
        # Enter credentials
        logger.info("Entering credentials")
        username_input.send_keys(username)
        
        password_input = driver.find_element(By.NAME, "password")
        password_input.send_keys(password)
        
        # Click login button
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        # Wait for successful login
        time.sleep(5)
        wait.until(EC.url_changes(driver.current_url))
        
        logger.info("Login successful")
        return True
        
    except (TimeoutException, NoSuchElementException) as e:
        logger.error(f"Login failed: {str(e)}")
        return False


def navigate_to_messages(driver) -> bool:
    """
    Navigate to TikTok messages page.
    
    Args:
        driver: WebDriver instance
    
    Returns:
        bool: True if navigation successful, False otherwise
    """
    try:
        logger.info("Navigating to messages")
        driver.get("https://www.tiktok.com/messages")
        
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='chat-list']")))
        
        logger.info("Successfully navigated to messages")
        return True
        
    except TimeoutException:
        logger.error("Failed to navigate to messages page")
        return False


def find_and_click_conversation(driver, contact_name: str) -> bool:
    """
    Find and click on a conversation with the specified contact.
    
    Args:
        driver: WebDriver instance
        contact_name: Name of the contact to find
    
    Returns:
        bool: True if conversation found and clicked, False otherwise
    """
    try:
        logger.info(f"Searching for conversation with {contact_name}")
        
        wait = WebDriverWait(driver, 15)
        
        # Wait for chat list to load
        chat_list = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='chat-list']"))
        )
        
        # Find all conversation items
        conversations = chat_list.find_elements(By.CSS_SELECTOR, "[data-e2e='chat-item']")
        
        logger.info(f"Found {len(conversations)} conversations")
        
        for item in conversations:
            try:
                # Get conversation name
                name_element = item.find_element(By.CSS_SELECTOR, "[data-e2e='chat-name']")
                name = name_element.text.strip()
                
                if contact_name.lower() in name.lower():
                    logger.info(f"Found matching conversation: {name}")
                    
                    # Scroll conversation into view with smooth scrolling
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                        item
                    )
                    time.sleep(0.5)
                    
                    # Click on the conversation
                    item.click()
                    
                    logger.info("Conversation clicked successfully")
                    return True
                    
            except NoSuchElementException:
                continue
        
        logger.warning(f"Conversation with {contact_name} not found")
        return False
        
    except TimeoutException:
        logger.error("Timeout while searching for conversations")
        return False


def send_message(driver, message: str) -> bool:
    """
    Send a message in the currently open conversation.
    
    Args:
        driver: WebDriver instance
        message: Message text to send
    
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    try:
        logger.info("Preparing to send message")
        
        wait = WebDriverWait(driver, 15)
        
        # Wait for message input box
        message_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='message-input']"))
        )
        
        # Type the message
        logger.info("Typing message")
        message_input.clear()
        message_input.send_keys(message)
        
        time.sleep(0.5)
        
        # Find and click send button
        send_button = driver.find_element(By.CSS_SELECTOR, "[data-e2e='send-button']")
        send_button.click()
        
        logger.info("Message sent successfully")
        return True
        
    except (TimeoutException, NoSuchElementException) as e:
        logger.error(f"Failed to send message: {str(e)}")
        return False


def get_recent_messages(driver, count: int = 10) -> list:
    """
    Get recent messages from the current conversation.
    
    Args:
        driver: WebDriver instance
        count: Number of recent messages to retrieve
    
    Returns:
        list: List of message dictionaries with sender and text
    """
    try:
        logger.info(f"Retrieving last {count} messages")
        
        wait = WebDriverWait(driver, 10)
        
        # Wait for message container
        message_container = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-e2e='message-container']"))
        )
        
        # Find all message elements
        message_elements = message_container.find_elements(
            By.CSS_SELECTOR, "[data-e2e='message-item']"
        )
        
        messages = []
        
        # Get the last 'count' messages
        for msg_element in message_elements[-count:]:
            try:
                sender = msg_element.find_element(By.CSS_SELECTOR, "[data-e2e='message-sender']").text
                text = msg_element.find_element(By.CSS_SELECTOR, "[data-e2e='message-text']").text
                
                messages.append({
                    'sender': sender,
                    'text': text
                })
            except NoSuchElementException:
                continue
        
        logger.info(f"Retrieved {len(messages)} messages")
        return messages
        
    except TimeoutException:
        logger.error("Timeout while retrieving messages")
        return []


@contextmanager
def managed_webdriver(headless: bool = True, use_temp_profile: bool = True):
    """
    Context manager for WebDriver with proper resource cleanup.
    
    Args:
        headless: Whether to run browser in headless mode
        use_temp_profile: Whether to use a temporary profile directory
    
    Yields:
        WebDriver: Configured Firefox WebDriver instance
    """
    # Define SESSION_DIR at the beginning of the function
    SESSION_DIR = tempfile.mkdtemp(prefix="firefox_session_") if use_temp_profile else None
    logger.info(f"Created temporary session directory: {SESSION_DIR}")
    
    # Initialize driver variable before try block
    driver = None
    
    try:
        # Set up Firefox options
        options = setup_firefox_options(headless=headless, profile_path=SESSION_DIR)
        
        # Create WebDriver instance
        logger.info("Initializing Firefox WebDriver")
        driver = webdriver.Firefox(options=options)
        
        # Set timeouts
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)
        
        logger.info("WebDriver initialized successfully")
        
        yield driver
        
    except WebDriverException as e:
        logger.error(f"WebDriver error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise
    finally:
        # Clean up driver
        if driver is not None:
            try:
                logger.info("Quitting WebDriver")
                driver.quit()
                logger.info("WebDriver quit successfully")
            except Exception as e:
                logger.error(f"Error quitting driver: {str(e)}")
        
        # Clean up session directory
        if SESSION_DIR is not None:
            try:
                logger.info(f"Removing session directory: {SESSION_DIR}")
                import shutil
                shutil.rmtree(SESSION_DIR, ignore_errors=True)
                logger.info("Session directory removed successfully")
            except Exception as e:
                logger.error(f"Failed to remove session directory: {str(e)}")


def run_message_bot(username: str, password: str, contact: str, message: str, headless: bool = True):
    """
    Run the TikTok message bot to send a message to a contact.
    
    Args:
        username: TikTok username or email
        password: TikTok password
        contact: Name of the contact to message
        message: Message text to send
        headless: Whether to run browser in headless mode
    """
    try:
        with managed_webdriver(headless=headless) as driver:
            # Log in to TikTok
            if not login_to_tiktok(driver, username, password):
                logger.error("Login failed, aborting")
                return
            
            # Navigate to messages
            if not navigate_to_messages(driver):
                logger.error("Failed to navigate to messages, aborting")
                return
            
            # Find and click conversation
            if not find_and_click_conversation(driver, contact):
                logger.error(f"Failed to find conversation with {contact}, aborting")
                return
            
            # Send message
            if not send_message(driver, message):
                logger.error("Failed to send message, aborting")
                return
            
            logger.info("Message bot completed successfully")
            
    except Exception as e:
        logger.error(f"Message bot failed with error: {str(e)}")


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) != 5:
        print("Usage: python tiktok_message_bot.py <username> <password> <contact> <message>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    contact = sys.argv[3]
    message = sys.argv[4]
    
    run_message_bot(username, password, contact, message, headless=False)
