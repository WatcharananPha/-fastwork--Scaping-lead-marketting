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

# --- CONFIG & HELPERS ---
load_dotenv()
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
PROFILE_PATH = r'C:\chrome-profiles\ig_profile'
WAIT_TIMEOUT = 20

# Function to initialize the driver
def get_driver():
    st.info("Initializing Chrome browser...")
    os.makedirs(PROFILE_PATH, exist_ok=True)
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_PATH}")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=en-US")
    driver = uc.Chrome(options=options)
    return driver

# Function for login process
def login(driver, status_placeholder):
    status_placeholder.info("Navigating to Instagram login...")
    driver.get("https://www.instagram.com/accounts/login/")
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    try:
        username_input = wait.until(EC.visibility_of_element_located((By.NAME, "username")))
        password_input = driver.find_element(By.NAME, "password")
        username_input.send_keys(INSTAGRAM_USERNAME)
        password_input.send_keys(INSTAGRAM_PASSWORD)
        password_input.send_keys(Keys.RETURN)
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[@aria-label='Home' or @aria-label='หน้าหลัก']")))
        status_placeholder.success("Login Successful!")
        time.sleep(3)
        # Handle potential pop-ups after login
        for text in ['Not Now', 'ไว้ทีหลัง', 'Turn Off', 'ปิด']:
            try:
                button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), '{text}')]")))
                button.click()
                time.sleep(2)
            except Exception:
                pass # Pop-up not found, continue
    except Exception as e:
        status_placeholder.error(f"Login failed. Error: {e}")
        raise

# Function to scrape post URLs
def run_post_url_scraper(page_url, target_count):
    driver = None
    results = []
    with st.status("Running: Scrape Post URLs...", expanded=True) as status:
        try:
            driver = get_driver()
            driver.get("https://www.instagram.com")
            time.sleep(2)
            if "login" in driver.current_url:
                login(driver, st)
            else:
                st.success("Already logged in.")

            st.info(f"Navigating to {page_url}...")
            driver.get(page_url)
            wait = WebDriverWait(driver, WAIT_TIMEOUT)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "main[role='main']")))
            
            post_urls = set()
            progress_bar = st.progress(0, text="Collecting URLs...")
            last_height = driver.execute_script("return document.body.scrollHeight")

            while len(post_urls) < target_count:
                js_get_links = "return Array.from(document.querySelectorAll(\"a[href^='/p/'], a[href*='/reel/']\")).map(a => a.href);"
                hrefs = driver.execute_script(js_get_links)
                post_urls.update([url.split('?')[0] for url in hrefs])
                
                progress_value = min(len(post_urls) / target_count, 1.0)
                progress_bar.progress(progress_value, text=f"Collected {len(post_urls)} / {target_count} URLs")
                
                if len(post_urls) >= target_count: break

                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    st.warning("Reached end of page before hitting target.")
                    break
                last_height = new_height
            
            results = list(post_urls)[:target_count]
            status.update(label="Scraping complete!", state="complete")
        except Exception as e:
            status.update(label=f"An error occurred: {e}", state="error")
        finally:
            if driver:
                driver.quit()
    return results

# Function to scrape profile URLs from likers
def run_profile_url_scraper(post_url, target_count):
    driver = None
    results = []
    with st.status("Running: Scrape Profile URLs from Likers...", expanded=True) as status:
        try:
            driver = get_driver()
            driver.get("https://www.instagram.com")
            time.sleep(2)
            if "login" in driver.current_url:
                login(driver, st)
            else:
                st.success("Already logged in.")
            
            st.info(f"Navigating to post: {post_url}")
            driver.get(post_url)
            wait = WebDriverWait(driver, WAIT_TIMEOUT)
            
            likes_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'liked_by')]")))
            likes_link.click()
            st.info("Opened likers list.")
            
            dialog_xpath = "div[role='dialog']"
            wait.until(EC.presence_of_element_located((By.XPATH, f"//{dialog_xpath}")))
            
            profile_urls = set()
            progress_bar = st.progress(0, "Collecting profiles...")
            last_height = 0

            while len(profile_urls) < target_count:
                user_links_xpath = f"//{dialog_xpath}//a[contains(@href, '/') and .//span]"
                links = driver.find_elements(By.XPATH, user_links_xpath)
                profile_urls.update([link.get_attribute('href').split('?')[0] for link in links if link.get_attribute('href')])
                
                progress_value = min(len(profile_urls) / target_count, 1.0)
                progress_bar.progress(progress_value, text=f"Collected {len(profile_urls)} / {target_count} profiles")
                
                if len(profile_urls) >= target_count: break

                dialog_element = driver.find_element(By.XPATH, f"//{dialog_xpath}//div[@role='dialog']")
                driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', dialog_element)
                time.sleep(3)
                
                new_height = driver.execute_script("return arguments[0].scrollHeight", dialog_element)
                if new_height == last_height:
                    st.warning("Reached end of likers list.")
                    break
                last_height = new_height

            results = list(profile_urls)[:target_count]
            status.update(label="Scraping complete!", state="complete")
        except Exception as e:
            status.update(label=f"An error occurred: {e}", state="error")
        finally:
            if driver:
                driver.quit()
    return results

# --- STREAMLIT UI ---
st.set_page_config(page_title="Instagram Scraper", layout="wide")
st.title("📸 Instagram Scraping")
st.markdown("---")

tab1, tab2 = st.tabs(["1. Scrape Post URLs from Page", "2. Scrape Profile URLs from Post Likers"])

with tab1:
    st.header("ดึง URL ของโพสต์จากหน้าเพจ")
    page_url_input = st.text_input("Instagram Page URL", "https://www.instagram.com/apple", key="page_url")
    target_post_count = st.number_input("จำนวนโพสต์ที่ต้องการ", 1, 1000, 50, key="post_count")
    
    if st.button("Start Scraping Post URLs", type="primary"):
        if page_url_input:
            scraped_data = run_post_url_scraper(page_url_input, target_post_count)
            if scraped_data:
                st.success(f"Successfully collected {len(scraped_data)} URLs.")
                df = pd.DataFrame(scraped_data, columns=["PostURL"])
                st.dataframe(df, use_container_width=True)
                st.download_button("Download Post URLs as CSV", df.to_csv(index=False), "post_urls.csv", "text/csv")
        else:
            st.error("Please enter a Page URL.")

with tab2:
    st.header("ดึง URL ของโปรไฟล์จากคนกดไลก์")
    post_url_liker_input = st.text_input("Instagram Post URL", "https://www.instagram.com/p/C-your-post-id/", key="liker_url")
    target_profile_count = st.number_input("จำนวนโปรไฟล์ที่ต้องการ", 1, 2000, 100, key="profile_count")

    if st.button("Start Scraping Liker Profiles", type="primary"):
        if post_url_liker_input:
            scraped_profiles = run_profile_url_scraper(post_url_liker_input, target_profile_count)
            if scraped_profiles:
                st.success(f"Successfully collected {len(scraped_profiles)} profiles.")
                df_profiles = pd.DataFrame(scraped_profiles, columns=["ProfileURL"])
                st.dataframe(df_profiles, use_container_width=True)
                st.download_button("Download Profile URLs as CSV", df_profiles.to_csv(index=False), "liker_profiles.csv", "text/csv")
        else:
            st.error("Please enter a Post URL.")