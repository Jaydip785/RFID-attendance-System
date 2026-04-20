import time
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
from datetime import datetime, timedelta, time as dt_time
import pytz
import plotly.express as px

# ──────────────────────────────────────────────
# 1. SETUP & MASTER DATABASE
# ──────────────────────────────────────────────
IST = pytz.timezone('Asia/Kolkata')

MASTER_STUDENTS = {
    "101": "Rahul Patil", "102": "Sneha Deshmukh", "103": "Amit Shinde",
    "104": "Priya Kulkarni", "105": "Vicky More", "106": "Anjali Gadgil", "107": "Sumit Pawar"
}

TIMETABLE = [
    (8, 0, 9, 0, "Mathematics"), (9, 0, 10, 0, "Physics"), (10, 0, 11, 0, "Chemistry"),
    (11, 20, 12, 20, "English"), (12, 20, 13, 20, "Biology"),
    (14, 0, 15, 0, "Computer Sci."), (15, 0, 16, 0, "History")
]

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            cred_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {
                "databaseURL": "https://attendance-e4940-default-rtdb.firebaseio.com/"
            })
            return True
        except Exception as e:
            st.error(f"Firebase Error: {e}")
            return False
    return True

# ──────────────────────────────────────────────
# 2. HELPER FUNCTIONS
# ──────────────────────────────────────────────
def get_ist_now(): return datetime.now(IST)

def get_greeting():
    h = get_ist_now().hour
    if h < 12: return "Good Morning ☀️", "Fresh start for a new day!"
    elif 12 <= h < 17: return "Good Afternoon 🌤️", "Mid-day energy check!"
    else: return "Good Evening 🌆", "Wrapping up the day's work."

def get_subject_for_time(t):
    if pd.isna(t): return "Free Period"
    ct = dt_time(t.hour, t.minute)
    for sh, sm, eh, em, subject in TIMETABLE:
        if dt_time(sh, sm) <= ct < dt_time(eh, em): return subject
    return "No Lecture"

def fetch_data():
    try:
        ref = db.reference("attendance")
        data = ref.get()
        if not data: return pd.DataFrame()
        df = pd.DataFrame(list(data.values()) if isinstance(data, dict) else data)
        if not df.empty and "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], errors="coerce")
            df["time"] = df["time"].dt.tz_localize('UTC').dt.tz_convert(IST)
            df["Subject"] = df["time"].apply(get_subject_for_time)
            df = df.sort_values("time", ascending=False).reset_index(drop=True)
        return df
    except: return pd.DataFrame()

# ──────────────────────────────────────────────
# 3. UI CONFIG
# ──────────────────────────────────────────────
st.set_page_config(page_title="RFID Smart Pro", layout="wide")
init_firebase()

st.markdown("""
<style>
    .stApp { background-color: #0f172a; color: #f8fafc; }
    .header-box {
        background: rgba(30, 41, 59, 0.8); backdrop-filter: blur(10px);
        padding: 20px; border-radius: 15px; border-left: 5px solid #3b82f6;
        display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;
    }
    .live-dot { height: 10px; width: 10px; background-color: #10b981; border-radius: 50%; display: inline-block; animation: blink 1.2s infinite; }
    @keyframes blink { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ Admin Panel")
    app_mode = st.selectbox("Navigation", ["Live Dashboard", "Absentee Tracker", "Timetable"])
    refresh_rate = st.slider("Update Frequency (sec)", 2, 15, 5)

# ──────────────────────────────────────────────
# 4. MAIN DASHBOARD
# ──────────────────────────────────────────────
if app_mode == "Live Dashboard":
    placeholder = st.empty()
    while True:
        df = fetch_data()
        now = get_ist_now()
        greet_t, greet_m = get_greeting()
        
        present_uids = df["uid"].unique() if not df.empty and "uid" in df.columns else []
        total_enrolled = len(MASTER_STUDENTS)
        absent_count = total_enrolled - len(present_uids)

        with placeholder.container():
            # Header
            st.markdown(f"""
            <div class="header-box">
                <div><h2 style='margin:0;'>{greet_t}</h2><p style='margin:0; opacity:0.7;'>{greet_m}</p></div>
                <div style='text-align: right;'><h2 style='margin:0; font-family: monospace;'>{now.strftime('%I:%M:%S %p')}</h2>
                <p style='margin:0;'><span class="live-dot"></span> ANALYTICS LIVE</p></div>
            </div>
            """, unsafe_allow_html=True)

            # Metrics Row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Current Lecture", get_subject_for_time(now))
            m2.metric("Total Present", f"{len(present_uids)} / {total_enrolled}")
            m3.metric("Total Absent", absent_count)
            attend_per = (len(present_uids)/total_enrolled)*100
            m4.metric("Attendance %", f"{attend_per:.1f}%")

            st.markdown("---")

            # Analytics Section
            col_left, col_right = st.columns([2, 1])

            with col_left:
                st.subheader("📈 Hourly Scanning Trend")
                if not df.empty:
                    # तासानुसार डेटा ग्रुप करा
                    df['hour'] = df['time'].dt.hour
                    hourly_data = df.groupby('hour').size().reset_index(name='Scans')
                    fig = px.area(hourly_data, x='hour', y='Scans', color_discrete_sequence=['#3b82f6'])
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No data available for trend analysis.")

            with col_right:
                st.subheader("📊 Distribution")
                fig_pie = px.pie(values=[len(present_uids), absent_count], names=['Present', 'Absent'], 
                                 color_discrete_sequence=['#10b981', '#ef4444'], hole=0.5)
                fig_pie.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=300, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True)

            # Latest Scan Highlight
            st.markdown("---")
            if not df.empty:
                latest = df.iloc[0]
                st.info(f"🚀 **Latest Activity:** {latest.get('name', 'Unknown')} scanned for **{latest.get('Subject', 'N/A')}** at {latest['time'].strftime('%I:%M %p')}")

        time.sleep(refresh_rate)

elif app_mode == "Absentee Tracker":
    # (आधीचा Absentee Tracker कोड)
    st.header("🕵️ Absentee Tracker")
    df_main = fetch_data()
    present_uids = set(df_main["uid"].unique().astype(str)) if not df_main.empty and "uid" in df_main.columns else set()
    absent_uids = set(MASTER_STUDENTS.keys()) - present_uids
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("❌ Absent Students")
        for u in absent_uids: st.error(f"{MASTER_STUDENTS[u]} ({u})")
    with c2:
        st.subheader("✅ Present Students")
        for u in present_uids: st.success(f"{MASTER_STUDENTS.get(u, 'Guest')} ({u})")

elif app_mode == "Timetable":
    st.header("📅 Schedule")
    st.table(pd.DataFrame([f"{s[0]:02d}:{s[1]:02d}-{s[2]:02d}:{s[3]:02d} | {s[4]}" for s in TIMETABLE], columns=["Schedule"]))