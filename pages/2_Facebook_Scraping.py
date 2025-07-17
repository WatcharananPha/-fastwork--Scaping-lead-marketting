import streamlit as st
import time
import os
import pandas as pd
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException

# --- CONFIG & HELPERS ---
load_dotenv()
FACEBOOK_EMAIL = os.getenv('FACEBOOK_EMAIL')
FACEBOOK_PASSWORD = os.getenv('FACEBOOK_PASSWORD')
PROFILE_PATH = r'C:\chrome-profiles\fb_profile'
WAIT_TIMEOUT = 20

def get_fb_driver():
    st.info("Initializing Chrome browser for Facebook...")
    os.makedirs(PROFILE_PATH, exist_ok=True)
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_PATH}")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=en-US")
    driver = uc.Chrome(options=options)
    return driver

def login_facebook(driver, status_placeholder):
    status_placeholder.info("Navigating to Facebook...")
    driver.get("https://www.facebook.com")
    time.sleep(3)
    try:
        # Handle cookie banner
        cookie_buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-cookiebanner='accept_button_dialog']")
        if cookie_buttons and cookie_buttons[0].is_displayed():
            cookie_buttons[0].click()
            time.sleep(2)
        
        # Check if login form is present
        email_input_list = driver.find_elements(By.ID, "email")
        if email_input_list:
            status_placeholder.info("Login form found. Entering credentials...")
            pass_input = driver.find_element(By.ID, "pass")
            email_input_list[0].send_keys(FACEBOOK_EMAIL)
            pass_input.send_keys(FACEBOOK_PASSWORD)
            pass_input.submit()
            wait = WebDriverWait(driver, WAIT_TIMEOUT)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']")))
            status_placeholder.success("Facebook login successful!")
        else:
            status_placeholder.success("Already logged into Facebook.")
    except Exception as e:
        status_placeholder.error(f"Facebook login failed. Error: {e}")
        raise

def run_fb_profile_scraper(page_url, scroll_count):
    driver = None
    results = []
    with st.status("Running: Scrape Reactor Profiles...", expanded=True) as status:
        try:
            driver = get_fb_driver()
            login_facebook(driver, st)
            
            st.info(f"Navigating to Facebook page: {page_url}")
            driver.get(page_url)
            WebDriverWait(driver, WAIT_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']")))

            st.info(f"Scrolling feed {scroll_count} times to load posts...")
            for i in range(scroll_count):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
                st.text(f"Scroll {i+1}/{scroll_count}")

            all_scraped_profiles = {}
            reactors_button_selector = "div[role='article'] div[aria-label='See who reacted to this']"
            post_reaction_buttons = driver.find_elements(By.CSS_SELECTOR, reactors_button_selector)
            st.info(f"Found {len(post_reaction_buttons)} posts with reactions.")

            progress_bar = st.progress(0, "Processing posts...")
            for i, button in enumerate(post_reaction_buttons):
                progress_bar.progress((i + 1) / len(post_reaction_buttons), f"Processing post {i+1}/{len(post_reaction_buttons)}")
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", button)

                    dialog_selector = "div[role='dialog']"
                    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, dialog_selector)))

                    no_change_count = 0
                    while no_change_count < 3:
                        profiles_before = len(all_scraped_profiles)
                        profile_elements = driver.find_elements(By.CSS_SELECTOR, f"{dialog_selector} a[href*='facebook.com/']")
                        for element in profile_elements:
                            name = element.text
                            url = element.get_attribute('href')
                            if name and url and len(name) > 1:
                                all_scraped_profiles[url.split('?')[0]] = {'profile_name': name, 'profile_url': url.split('?')[0]}
                        
                        dialog = driver.find_element(By.CSS_SELECTOR, dialog_selector)
                        driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', dialog)
                        time.sleep(2.5)
                        
                        if len(all_scraped_profiles) == profiles_before:
                            no_change_count += 1
                        else:
                            no_change_count = 0
                    
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(2)
                except TimeoutException:
                    st.warning(f"Skipping post {i+1} (dialog timeout).")
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    continue
            
            results = list(all_scraped_profiles.values())
            status.update(label="Profile scraping complete!", state="complete")
        except Exception as e:
            status.update(label=f"An error occurred: {e}", state="error")
        finally:
            if driver:
                driver.quit()
    return results

def run_fb_contact_scraper(uploaded_file):
    # This function would be similar but is left as a placeholder for brevity
    # It would read the uploaded file and iterate through URLs
    st.info("Contact scraping feature is under development.")
    return []

# --- STREAMLIT UI ---
st.set_page_config(page_title="Facebook Scraper", layout="wide")
st.title("🇫acebook Scraping")
st.markdown("---")

tab1, tab2 = st.tabs(["1. Scrape Profiles from Post Reactions", "2. Scrape Contact Info from Profiles"])

with tab1:
    st.header("ดึงโปรไฟล์จากคน React โพสต์")
    fb_page_url = st.text_input("Facebook Page URL", "https://www.facebook.com/anantajewelry", key="fb_page_url")
    scroll_count = st.slider("จำนวนครั้งที่ Scroll เพื่อโหลดโพสต์", 1, 20, 5)

    if st.button("Start Scraping Profiles", type="primary"):
        if fb_page_url:
            profile_data = run_fb_profile_scraper(fb_page_url, scroll_count)
            if profile_data:
                st.success(f"Successfully collected {len(profile_data)} unique profiles.")
                df = pd.DataFrame(profile_data)
                st.dataframe(df, use_container_width=True)
                st.download_button("Download Profiles as CSV", df.to_csv(index=False), "fb_profiles.csv", "text/csv")
        else:
            st.error("Please enter a Facebook Page URL.")

with tab2:
    st.header("ดึงข้อมูลติดต่อจากไฟล์ Profile")
    st.warning("Feature in development.")
    uploaded_file = st.file_uploader("Upload the CSV file with profile URLs", type=["csv"])
    if st.button("Start Scraping Contact Info", disabled=True):
        if uploaded_file is not None:
            # contact_data = run_fb_contact_scraper(uploaded_file)
            # ... display results ...
            pass
        else:
            st.error("Please upload a CSV file.")