# app.py
import time
from datetime import datetime
import streamlit as st
from streamlit_autorefresh import st_autorefresh

APP_TITLE = "🎉 Birthday Countdown & Wish List"
TARGET_DATE = datetime(2025, 9, 26, 0, 0, 0)

# ----------------------- Utility -----------------------
def get_countdown(target: datetime):
    now = datetime.now()
    delta = target - now
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return days, hours, minutes, seconds

# ----------------------- Config -----------------------
st.set_page_config(page_title=APP_TITLE, page_icon="🎂", layout="centered")

st.title(APP_TITLE)
st.caption("Counting down to September 26, 2025 🎂")

# ----------------------- Auto Refresh -----------------------
# Refresh every 1000 ms (1 second)
st_autorefresh(interval=1000, key="countdown_refresh")

# ----------------------- Countdown -----------------------
days, hours, minutes, seconds = get_countdown(TARGET_DATE)

st.markdown(
    f"""
    ## ⏳ Countdown
    **{days} days, {hours} hours, {minutes} minutes, {seconds} seconds**
    until the big day! 🎉
    """
)

# ----------------------- Wish List -----------------------
wishlist = {
    "Under $25": [
        "Sample Item 1",
        "Sample Item 2"
    ],
    "$25 - $50": [
        "Sample Item 3",
        "Sample Item 4"
    ],
    "$50+": [
        "Sample Item 5",
        "Sample Item 6"
    ]
}

st.divider()
st.header("🎁 Birthday Wish List")

for category, items in wishlist.items():
    st.subheader(category)
    if items:
        for item in items:
            st.markdown(f"- {item}")
    else:
        st.write("(No items yet)")
