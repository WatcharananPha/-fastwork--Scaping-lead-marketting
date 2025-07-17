import streamlit as st
import time
import os
import pandas as pd
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 1. SETUP AND HELPER FUNCTIONS ---

# Load environment variables from .env file
load_dotenv()
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')

# Constants for Selenium
# Use a persistent profile path to reduce login frequency
PROFILE_PATH = r'C:\chrome-profiles\ig-pipeline-stage1-persistent'
WAIT_TIMEOUT = 20

def login_to_instagram(driver: uc.Chrome, status_placeholder):
    """Logs into Instagram, updating a Streamlit placeholder with the current status."""
    status_placeholder.info("Navigating to Instagram login page...")
    driver.get("https://www.instagram.com/accounts/login/")
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    try:
        status_placeholder.info("Entering username and password...")
        username_input = wait.until(EC.visibility_of_element_located((By.NAME, "username")))
        password_input = driver.find_element(By.NAME, "password")

        username_input.send_keys(INSTAGRAM_USERNAME)
        password_input.send_keys(INSTAGRAM_PASSWORD)
        password_input.send_keys(Keys.RETURN)

        status_placeholder.info("Waiting for login confirmation...")
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[@aria-label='Home' or @aria-label='หน้าหลัก']")))
        status_placeholder.success("Login successful!")
        time.sleep(3)

        # Handle pop-ups gracefully
        popups_to_handle = {
            "Save Info": "//div[contains(@class, '_ac8f')]/button[text()='Not Now' or text()='ไว้ทีหลัง']",
            "Notifications": "//button[text()='Not Now' or text()='ปิด']"
        }
        for name, xpath in popups_to_handle.items():
            try:
                button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                button.click()
                status_placeholder.info(f"Handled '{name}' pop-up.")
                time.sleep(2)
            except Exception:
                status_placeholder.warning(f"'{name}' pop-up not found or timeout. Continuing...")
    except Exception as e:
        status_placeholder.error(f"An error occurred during login. Please check credentials or network. Error: {e}")
        raise

def collect_post_urls(driver: uc.Chrome, page_url: str, target_count: int, progress_bar, status_text) -> list[str]:
    """Collects post URLs from a given Instagram page, updating Streamlit UI elements."""
    driver.get(page_url)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "main[role='main']")))
    time.sleep(2)

    post_urls = set()
    js_get_links = "return Array.from(document.querySelectorAll(\"a[href^='/p/'], a[href*='/reel/']\")).map(a => a.href);"
    last_height = driver.execute_script("return document.body.scrollHeight")

    while len(post_urls) < target_count:
        hrefs = driver.execute_script(js_get_links)
        for url in hrefs:
            clean_url = url.split('?')[0]
            post_urls.add(clean_url)

        # Update Streamlit progress UI
        progress_value = min(len(post_urls) / target_count, 1.0)
        progress_bar.progress(progress_value)
        status_text.text(f"Collected {len(post_urls)} / {target_count} URLs...")

        if len(post_urls) >= target_count:
            status_text.text(f"Target of {target_count} URLs reached. Finalizing...")
            break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            status_text.warning("Reached the bottom of the page before hitting the target count.")
            break
            
    return list(post_urls)[:target_count]

# --- 2. STREAMLIT UI ---

st.set_page_config(page_title="Instagram Scraper", layout="wide")
st.title("📸 Instagram Post URL Scraper")
st.markdown("Enter an Instagram page URL to collect the URLs of its recent posts.")

# Check for required setup before proceeding
if not (INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD):
    st.error("⚠️ **Setup Required:** `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD` must be set in your `.env` file.")
    st.stop()
if not os.path.exists(PROFILE_PATH):
     st.warning(f"**Profile Path Not Found:** For best results, please create the directory: `{PROFILE_PATH}` to reduce login frequency.")

# User inputs
page_url = st.text_input("Instagram Page URL", placeholder="e.g., https://www.instagram.com/nasa")
target_count = st.number_input("Number of posts to collect", min_value=1, max_value=1000, value=50)

if st.button("🚀 Start Scraping", type="primary"):
    if not page_url or "instagram.com" not in page_url:
        st.error("Please enter a valid Instagram Page URL.")
    else:
        try:
            options = uc.ChromeOptions()
            options.add_argument("--disable-notifications")
            options.add_argument("--lang=en-US")
            options.add_argument(f"--user-data-dir={PROFILE_PATH}")

            with st.spinner("Initializing Chrome Browser..."):
                driver = uc.Chrome(options=options)
            
            status_placeholder = st.empty()
            
            # Check if login is needed
            driver.get("https://www.instagram.com")
            time.sleep(3)
            if "login" in driver.current_url:
                login_to_instagram(driver, status_placeholder)
            else:
                status_placeholder.success("✅ Already logged in using a persistent profile.")

            # Start collecting URLs with progress indication
            st.info(f"Starting to collect URLs from {page_url}...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            all_found_urls = collect_post_urls(driver, page_url, target_count, progress_bar, status_text)
            driver.quit()

            # Process and display results
            if all_found_urls:
                st.success(f"✅ Successfully collected {len(all_found_urls)} post URLs.")
                
                df = pd.DataFrame(all_found_urls, columns=['PostURL'])
                st.dataframe(df)
                
                csv_data = df.to_csv(index=False).encode('utf-8')
                page_name = page_url.split('/')[-1] or page_url.split('/')[-2]
                st.download_button(
                    label="📥 Download URLs as CSV",
                    data=csv_data,
                    file_name=f"{page_name}_posts.csv",
                    mime='text/csv',
                )
            else:
                st.warning("No post URLs were found. The page might be private or have no posts.")

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            st.error("Please check the terminal for more details. The browser might have closed unexpectedly.")