import time
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
from datetime import datetime, time as dt_time
from collections import Counter
import pytz  # Timezone साठी

# ──────────────────────────────────────────────
#  CONFIG & TIMEZONE
# ──────────────────────────────────────────────
IST = pytz.timezone('Asia/Kolkata')

TIMETABLE = [
    (8,  0,  9,  0,  "Mathematics"),
    (9,  0,  10, 0,  "Physics"),
    (10, 0,  11, 0,  "Chemistry"),
    (11, 0,  11, 20, "Break"),
    (11, 20, 12, 20, "English"),
    (12, 20, 13, 20, "Biology"),
    (13, 20, 14, 0,  "Lunch"),
    (14, 0,  15, 0,  "Computer Sci."),
    (15, 0,  16, 0,  "History"),
]

def get_subject_for_time(t: datetime) -> str:
    if pd.isna(t): return "—"
    # जर वेळ UTC असेल तर तिला IST मध्ये रूपांतरित करा
    if t.tzinfo is not None:
        t = t.astimezone(IST)
    ct = dt_time(t.hour, t.minute)
    for sh, sm, eh, em, subject in TIMETABLE:
        if dt_time(sh, sm) <= ct < dt_time(eh, em):
            return subject
    return "—"

def get_current_subject() -> tuple:
    now = datetime.now(IST)
    ct  = dt_time(now.hour, now.minute)
    for sh, sm, eh, em, subject in TIMETABLE:
        if dt_time(sh, sm) <= ct < dt_time(eh, em):
            return subject, f"{sh:02d}:{sm:02d} – {eh:02d}:{em:02d}"
    return "No Class", "Outside schedule"

# ──────────────────────────────────────────────
#  Firebase Init
# ──────────────────────────────────────────────
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://attendance-e4940-default-rtdb.firebaseio.com/"
        })
init_firebase()

# ──────────────────────────────────────────────
#  Page Config & CSS (Same as yours)
# ──────────────────────────────────────────────
st.set_page_config(page_title="RFID Live Attendance", page_icon="📡", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; background-color: #0a0c0f !important; color: #e8ecf4 !important; }
.stApp { background-color: #0a0c0f !important; }
.rfid-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 32px; background: #111318; border-bottom: 1px solid #222730; position: relative; overflow: hidden; margin-bottom: 24px; }
.live-pill { display: flex; align-items: center; gap: 7px; background: rgba(0,229,160,.1); border: 1px solid rgba(0,229,160,.25); border-radius: 99px; padding: 5px 14px; font-size: 12px; font-weight: 500; color: #00e5a0; font-family: 'Space Mono', monospace; }
.live-dot { width: 7px; height: 7px; border-radius: 50%; background: #00e5a0; animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(0,229,160,.4); } 50% { box-shadow: 0 0 0 5px rgba(0,229,160,0); } }
.stat-card { background: #111318; border: 1px solid #222730; border-radius: 14px; padding: 18px 20px; min-height: 110px; }
.sv-green { color: #00e5a0; } .sv-blue { color: #00aaff; } .sv-purple { color: #a78bfa; } .sv-red { color: #ff4d6d; }
.stat-value { font-family: 'Space Mono', monospace; font-size: 26px; font-weight: 700; }
.last-scan-banner { margin: 0 32px 20px; border-radius: 12px; background: rgba(0,229,160,.06); border: 1px solid rgba(0,229,160,.2); padding: 12px 18px; display: flex; align-items: center; gap: 14px; }
.subject-fill { height: 100%; border-radius: 4px; background: #a78bfa; }
.subject-track { flex: 1; height: 8px; background: #181c22; border-radius: 4px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
#  Helper Functions
# ──────────────────────────────────────────────
def fetch_data() -> pd.DataFrame:
    ref = db.reference("attendance")
    data = ref.get()
    if not data: return pd.DataFrame()
    records = list(data.values()) if isinstance(data, dict) else data
    df = pd.DataFrame(records)
    if "time" in df.columns:
        # Firebase कडून येणारी वेळ UTC असू शकते, तिला timezone-aware करा
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize('UTC').dt.tz_convert(IST)
        else:
            df["time"] = df["time"].dt.tz_convert(IST)
        df = df.sort_values("time", ascending=False).reset_index(drop=True)
    return df

def compute_metrics(df: pd.DataFrame, expected: int) -> dict:
    if df.empty: return dict(total=0, unique=0, absent=expected, subject_dist={})
    uid_col = "uid" if "uid" in df.columns else ("name" if "name" in df.columns else None)
    unique = df[uid_col].nunique() if uid_col else len(df)
    subjects = df["time"].apply(get_subject_for_time)
    dist = dict(Counter(subjects))
    dist.pop("—", None)
    return dict(total=len(df), unique=unique, absent=max(0, expected-unique), subject_dist=dist)

# --- HTML UI Components ---
def header_html(time_str):
    return f'<div class="rfid-header"><div class="brand"><div class="brand-name">RFID Attendance</div><div class="brand-sub">LIVE IST SYSTEM</div></div><div class="hdr-right"><div class="clock-chip" style="color:#5a6278; font-family:monospace; margin-right:15px;">{time_str}</div><div class="live-pill"><div class="live-dot"></div>LIVE</div></div></div>'

def stat_card_html(label, value, css_class, sub):
    return f'<div class="stat-card"><div style="font-size:10px; color:#5a6278;">{label}</div><div class="stat-value {css_class}">{value}</div><div style="font-size:11px; color:#5a6278;">{sub}</div></div>'

# ──────────────────────────────────────────────
#  Main Execution
# ──────────────────────────────────────────────
if "expected" not in st.session_state: st.session_state.expected = 30

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.session_state.expected = st.number_input("Expected count", value=st.session_state.expected)
    refresh_int = st.slider("Refresh (sec)", 2, 30, 5)

placeholder = st.empty()

while True:
    df = fetch_data()
    metrics = compute_metrics(df, st.session_state.expected)
    now_str = datetime.now(IST).strftime("%I:%M:%S %p") # IST Time
    curr_subj, curr_range = get_current_subject()
    
    with placeholder.container():
        st.markdown(header_html(now_str), unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(stat_card_html("TOTAL SCANS", metrics["total"], "sv-green", "All history"), unsafe_allow_html=True)
        c2.markdown(stat_card_html("UNIQUE PRESENT", metrics["unique"], "sv-blue", "Today"), unsafe_allow_html=True)
        c3.markdown(stat_card_html("CURRENT SUBJECT", curr_subj, "sv-purple", curr_range), unsafe_allow_html=True)
        c4.markdown(stat_card_html("ABSENT", metrics["absent"], "sv-red", f"Target: {st.session_state.expected}"), unsafe_allow_html=True)

        if not df.empty:
            latest = df.iloc[0]
            st.markdown(f'<div class="last-scan-banner"><div class="live-dot"></div><div><div style="font-size:10px; color:#00e5a0;">LATEST SCAN</div><div style="font-weight:600;">{latest.get("name", latest.get("uid"))}</div></div><div style="margin-left:auto; font-family:monospace;">{latest["time"].strftime("%H:%M:%S")}</div></div>', unsafe_allow_html=True)

        st.markdown("### Live Feed")
        if not df.empty:
            display_df = df.copy()
            display_df["Time"] = display_df["time"].dt.strftime("%H:%M:%S")
            st.dataframe(display_df[["name", "uid", "Time"]].head(10), use_container_width=True)
        else:
            st.write("No data found.")

    time.sleep(refresh_int)