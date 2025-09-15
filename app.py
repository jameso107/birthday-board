# Streamlit Birthday Board
# -------------------------------------------------------------
# A lightweight Streamlit app to view, filter, and celebrate
# birthdays from a simple CSV file in your GitHub repo.
#
# Repo layout suggestion:
#   /app.py                  ← this file
#   /data/birthdays.csv      ← your birthday list (sample below)
#   /requirements.txt        ← streamlit, pandas, python-dateutil
#
# Sample CSV (put this in data/birthdays.csv):
# name,date,notes
# Ada Lovelace,1815-12-10,Pioneer 💻
# Marie Curie,1867-11-07,Two-time Nobel 🧪
# Your Friend,05-27,Loves tacos 🌮
#
# Date formats supported in `date` column:
#   • YYYY-MM-DD  → computes age/turning age
#   • MM-DD       → year omitted (age not computed, still scheduled each year)
# -------------------------------------------------------------

from __future__ import annotations
import io
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
import streamlit as st
from dateutil import parser

APP_TITLE = "🎉 Birthday Board"
DEFAULT_CSV_PATH = "data/birthdays.csv"

# ----------------------- Utilities -----------------------
@dataclass
class Person:
    name: str
    month: int
    day: int
    year: Optional[int]  # None if not provided
    notes: str = ""

    def next_birthday(self, today: date) -> date:
        # Compute the next occurrence (this year or next)
        y = today.year
        # Handle Feb 29 gracefully: move to Feb 28 on non-leap years for scheduling
        m, d = self.month, self.day
        try:
            candidate = date(y, m, d)
        except ValueError:
            # e.g., Feb 29 on non-leap year
            if m == 2 and d == 29:
                candidate = date(y, 2, 28)
            else:
                raise
        if candidate < today:
            # next year
            ny = y + 1
            try:
                candidate = date(ny, m, d)
            except ValueError:
                if m == 2 and d == 29:
                    candidate = date(ny, 2, 28)
                else:
                    raise
        return candidate

    def turning_age(self, today: date) -> Optional[int]:
        if self.year is None:
            return None
        next_bd = self.next_birthday(today)
        return next_bd.year - self.year


def parse_date_cell(cell: str | float | int | None) -> tuple[int, int, Optional[int]]:
    """Accepts YYYY-MM-DD or MM-DD (strings). Returns (month, day, year?).
    Raises ValueError on failure.
    """
    if cell is None:
        raise ValueError("Empty date cell")
    s = str(cell).strip()
    # Allow e.g., 5/27, 05-27, 2020-05-27, etc.
    # Prefer dateutil parsing but ensure we don't guess day-first incorrectly.
    # If input has only month/day, parser will attach today's year; we strip it.
    if "-" in s and len(s.split("-")) == 2:
        # MM-DD
        m, d = s.split("-")
        return int(m), int(d), None
    try:
        dt = parser.parse(s, dayfirst=False, yearfirst=True)
    except Exception as e:
        raise ValueError(f"Could not parse date '{s}': {e}")
    y = dt.year
    m = dt.month
    d = dt.day
    # Heuristic: if user wrote like "05-27" but parsed with current year appended by parser
    if s.count("-") == 1 or ("/" in s and s.count("/") == 1):
        return m, d, None
    return m, d, y


@st.cache_data(show_spinner=False)
def load_birthdays(path: str = DEFAULT_CSV_PATH) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        df = pd.DataFrame(columns=["name", "date", "notes"])  # empty shell
    # Normalize columns
    for col in ["name", "date", "notes"]:
        if col not in df.columns:
            df[col] = ""
    df = df[["name", "date", "notes"]].fillna("")
    # Parse
    records = []
    today = date.today()
    for _, row in df.iterrows():
        name = str(row["name"]).strip()
        if not name:
            continue
        try:
            m, d, y = parse_date_cell(row["date"])
        except Exception:
            # Skip unparseable rows but keep in a log table
            continue
        p = Person(name=name, month=m, day=d, year=y, notes=str(row["notes"]).strip())
        next_bd = p.next_birthday(today)
        days_until = (next_bd - today).days
        turning = p.turning_age(today)
        records.append({
            "name": name,
            "month": m,
            "day": d,
            "year": y,
            "notes": p.notes,
            "next_date": next_bd,
            "days_until": days_until,
            "turning": turning,
            "is_today": days_until == 0,
        })
    out = pd.DataFrame(records)
    if not out.empty:
        out.sort_values(["days_until", "name"], inplace=True)
        out.reset_index(drop=True, inplace=True)
    return out


def to_display_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    disp = df.copy()
    disp["date"] = disp["next_date"].dt.strftime("%Y-%m-%d")
    disp["birthday"] = disp.apply(lambda r: f"{r['month']:02d}-{r['day']:02d}", axis=1)
    disp["turning"] = disp["turning"].apply(lambda x: ("—" if pd.isna(x) else int(x)))
    disp = disp[["name", "date", "days_until", "turning", "birthday", "notes"]]
    disp.rename(columns={
        "date": "Next",
        "days_until": "Days",
        "turning": "Turning",
        "birthday": "MM-DD",
        "notes": "Notes",
    }, inplace=True)
    return disp


def make_ics(df: pd.DataFrame, cal_name: str = "Birthday Board") -> bytes:
    """Generate a minimal iCalendar (.ics) file for all birthdays in df.
    Uses all-day events recurring yearly.
    """
    if df.empty:
        return b""
    def ics_dt(d: date) -> str:
        return d.strftime("%Y%m%d")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"X-WR-CALNAME:{cal_name}",
        "PRODID:-//BirthdayBoard//Streamlit//EN",
    ]
    for _, r in df.iterrows():
        # For yearly recurrence, use the month/day of the canonical birthday (not next occurrence)
        bymonth = int(r["month"]) if not pd.isna(r["month"]) else r["next_date"].month
        bymonthday = int(r["day"]) if not pd.isna(r["day"]) else r["next_date"].day
        # DTSTART must be a real date — use the next upcoming one
        start = r["next_date"]
        summary = f"🎂 {r['name']}"
        if not pd.isna(r["turning"]):
            summary += f" turns {int(r['turning'])}"
        desc = str(r.get("notes", ""))
        uid = f"{r['name'].replace(' ', '_')}--{bymonth:02d}{bymonthday:02d}@birthdayboard"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART;VALUE=DATE:{ics_dt(start)}",
            f"RRULE:FREQ=YEARLY;BYMONTH={bymonth};BYMONTHDAY={bymonthday}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\n".join(lines).encode()


# ----------------------- UI -----------------------
st.set_page_config(page_title=APP_TITLE, page_icon="🎉", layout="wide")
st.title(APP_TITLE)

st.caption(
    "Load birthdays from a CSV in your repo (data/birthdays.csv) or upload one below. "
    "Supports YYYY-MM-DD and MM-DD. Add notes/emojis for flair!"
)

# Sidebar: Data source
st.sidebar.header("Data Source")
uploaded = st.sidebar.file_uploader("Upload CSV (name,date,notes)", type=["csv"])  # type: ignore
if uploaded is not None:
    df_raw = pd.read_csv(uploaded)
    st.session_state["_source"] = "uploaded"
else:
    df_raw = None

if df_raw is not None:
    # Save a temp copy to compute metrics
    tmp_path = "data/_uploaded.csv"
    try:
        df_raw.to_csv(tmp_path, index=False)
        df = load_birthdays(tmp_path)
    except Exception:
        df = load_birthdays(DEFAULT_CSV_PATH)
else:
    df = load_birthdays(DEFAULT_CSV_PATH)

# Sidebar: Filters
st.sidebar.header("Filters")
query = st.sidebar.text_input("Search name/notes")
soon_days = st.sidebar.slider("Upcoming within (days)", min_value=7, max_value=365, value=60, step=1)
only_upcoming = st.sidebar.checkbox("Only show upcoming", value=True)

# Apply filters
if not df.empty:
    m = df[
        (df["name"].str.contains(query, case=False, na=False) |
         df["notes"].str.contains(query, case=False, na=False))
    ]
    if only_upcoming:
        m = m[m["days_until"] <= soon_days]
else:
    m = df

# Stats header
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total", int(df.shape[0]))
col2.metric("Today 🎂", int(df[df["is_today"]].shape[0]))
# Next birthday
if not df.empty:
    next_row = df.iloc[0]
    col3.metric("Next", next_row["next_date"].strftime("%b %d"), f"in {int(next_row['days_until'])}d")
else:
    col3.metric("Next", "—")
# Window count
col4.metric(f"≤ {soon_days} days", int(df[df["days_until"] <= soon_days].shape[0]))

st.divider()

# Today shoutouts
today_rows = df[df["is_today"]] if not df.empty else df
if not today_rows.empty:
    st.subheader("🎈 Today’s Birthdays")
    for _, r in today_rows.iterrows():
        age_str = f"turns {int(r['turning'])}!" if not pd.isna(r["turning"]) else "🎉"
        st.success(f"**{r['name']}** {age_str}  —  {r['notes']}")

# Main table
st.subheader("📅 Birthday List")
if m.empty:
    st.info("No matches yet. Try clearing filters or upload your CSV.")
else:
    st.dataframe(to_display_df(m), use_container_width=True, hide_index=True)

# Calendar-style month grouping
if not df.empty:
    st.subheader("🗓️ By Month")
    month_map = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    grouped = (
        df.assign(month_name=df["month"].map(month_map))
          .sort_values(["month","day","name"])  # type: ignore
          .groupby("month_name", sort=False)
    )
    cols = st.columns(3)
    i = 0
    for mon, g in grouped:
        with cols[i % 3]:
            st.markdown(f"### {mon}")
            if g.empty:
                st.write("—")
            else:
                lines = [f"**{int(r.day):02d}**  {r.name}  {('(' + r.notes + ')') if r.notes else ''}" for r in g.sort_values(["day","name"]).itertuples()]
                st.markdown("\n".join(["- " + x for x in lines]))
        i += 1

st.divider()

# Downloads (CSV + ICS)
if not df.empty:
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            label="⬇️ Download filtered CSV",
            data=to_display_df(m).to_csv(index=False).encode(),
            file_name="birthdays_filtered.csv",
            mime="text/csv",
        )
    with c2:
        st.download_button(
            label="📆 Export .ics (all birthdays)",
            data=make_ics(df),
            file_name="birthdays.ics",
            mime="text/calendar",
        )

# Add new entry (in-session; offers downloadable row)
st.subheader("➕ Quick Add (one-off)")
with st.form("quick_add"):
    cc1, cc2, cc3, cc4 = st.columns([2,1,1,2])
    name_in = cc1.text_input("Name")
    month_in = cc2.number_input("Month", min_value=1, max_value=12, value=1, step=1)
    day_in = cc3.number_input("Day", min_value=1, max_value=31, value=1, step=1)
    year_in = cc4.text_input("Year (optional)")
    notes_in = st.text_input("Notes/emoji (optional)")
    submitted = st.form_submit_button("Add row → CSV")
    if submitted and name_in.strip():
        mm = int(month_in)
        dd = int(day_in)
        if year_in.strip():
            date_str = f"{int(year_in):04d}-{mm:02d}-{dd:02d}"
        else:
            date_str = f"{mm:02d}-{dd:02d}"
        new_row = pd.DataFrame([[name_in.strip(), date_str, notes_in.strip()]], columns=["name","date","notes"])
        st.success(f"Prepared new row for **{name_in}**. Download and append to your CSV in the repo.")
        st.download_button(
            label="Download new row (CSV)",
            data=new_row.to_csv(index=False).encode(),
            file_name="birthday_new_row.csv",
            mime="text/csv",
        )

# Footer help
st.caption(
    "ℹ️ Deploy on Streamlit Community Cloud: set the app file to `app.py`. "
    "Ensure `requirements.txt` includes: streamlit, pandas, python-dateutil."
)
