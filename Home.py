import streamlit as st

st.set_page_config(
    page_title="Social Media Scraper",
    page_icon="🕸️",
    layout="wide"
)

st.title("เลือก Platform ที่ต้องการ Scraping")
st.markdown("---")
st.write("แพลตฟอร์มสำหรับดึงข้อมูลจาก Social Media ต่างๆ กรุณาเลือกเมนูจากแถบด้านซ้ายเพื่อเริ่มต้น")

# --- Navigation Buttons ---
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("Facebook Scraping", use_container_width=True):
        st.switch_page("pages/2_Facebook_Scraping.py")

with col2:
    if st.button("Instagram Scraping", use_container_width=True):
        st.switch_page("pages/1_Instagram_Scraping.py")

with col3:
    if st.button("LinkedIn Scraping", use_container_width=True, disabled=True):
        st.info("Coming soon!")

# --- Sidebar ---
st.sidebar.header("Social Media Scraper")
st.sidebar.success("เลือกหน้าจอที่ต้องการจากเมนูหลัก")