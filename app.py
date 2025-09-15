from datetime import datetime
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from zoneinfo import ZoneInfo  # standard library

APP_TITLE = "🎉 Birthday Countdown & Wish List"
# Set birthday in Eastern Time
TARGET_DATE = datetime(2025, 9, 26, 0, 0, 0, tzinfo=ZoneInfo("America/New_York"))

def get_countdown(target: datetime):
    now = datetime.now(ZoneInfo("America/New_York"))  # also in ET
    delta = target - now
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return days, hours, minutes, seconds

st.set_page_config(page_title=APP_TITLE, page_icon="🎂", layout="centered")
st.title(APP_TITLE)
st.caption("Counting down to September 26, 2025 (Eastern Time) 🎂")

st_autorefresh(interval=1000, key="countdown_refresh")

days, hours, minutes, seconds = get_countdown(TARGET_DATE)

st.markdown(
    f"""
    ## ⏳ Countdown
    **{days} days, {hours} hours, {minutes} minutes, {seconds} seconds**
    until the big day! 🎉
    """
)
