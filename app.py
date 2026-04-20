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

# तुमच्या वर्गातील विद्यार्थ्यांची मास्टर लिस्ट
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
def get_ist_now(): 
    return datetime.now(IST)

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
            if df["time"].dt.tz is None:
                df["time"] = df["time"].dt.tz_localize('UTC').dt.tz_convert(IST)
            else:
                df["time"] = df["time"].dt.tz_convert(IST)
            df["Subject"] = df["time"].apply(get_subject_for_time)
            df = df.sort_values("time", ascending=False).reset_index(drop=True)
        return df
    except: return pd.DataFrame()

# ──────────────────────────────────────────────
# 3. UI CONFIG & CSS
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
    .clock-text { font-size: 32px; font-family: 'Courier New', Courier, monospace; font-weight: bold; color: #3b82f6; margin: 0; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ Admin Panel")
    app_mode = st.selectbox("Navigation", ["Live Dashboard", "Absentee Tracker", "Timetable"])
    refresh_rate = st.slider("Data Refresh Frequency (sec)", 2, 30, 5)
    st.info("घड्याळ दर सेकंदाला फिरेल, पण डेटा वरील सेकंदांनुसार अपडेट होईल.")

# ──────────────────────────────────────────────
# 4. MAIN APP LOGIC
# ──────────────────────────────────────────────
if app_mode == "Live Dashboard":
    header_placeholder = st.empty()
    analytics_placeholder = st.empty()
    
    # डेटा ट्रॅकिंगसाठी
    if 'last_data_update' not in st.session_state:
        st.session_state.last_data_update = 0
    if 'cached_df' not in st.session_state:
        st.session_state.cached_df = pd.DataFrame()

    while True:
        now = get_ist_now()
        
        # १. घड्याळ आणि ग्रीटिंग (दर सेकंदाला अपडेट)
        greet_t, greet_m = get_greeting()
        with header_placeholder.container():
            st.markdown(f"""
            <div class="header-box">
                <div><h2 style='margin:0;'>{greet_t}</h2><p style='margin:0; opacity:0.7;'>{greet_m}</p></div>
                <div style='text-align: right;'>
                    <p class="clock-text">{now.strftime('%I:%M:%S %p')}</p>
                    <p style='margin:0; font-size: 12px; letter-spacing: 1px;'>
                        <span class="live-dot"></span> ANALYTICS LIVE
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # २. डेटा अपडेट (केवळ refresh_rate पूर्ण झाल्यावरच)
        current_ts = time.time()
        if current_ts - st.session_state.last_data_update > refresh_rate:
            st.session_state.cached_df = fetch_data()
            st.session_state.last_data_update = current_ts

        # ३. अ‍ॅनालिटिक्स रेंडरिंग
        df = st.session_state.cached_df
        present_uids = df["uid"].unique() if not df.empty and "uid" in df.columns else []
        total_enrolled = len(MASTER_STUDENTS)
        absent_count = total_enrolled - len(present_uids)

        with analytics_placeholder.container():
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Current Lecture", get_subject_for_time(now))
            m2.metric("Total Present", f"{len(present_uids)} / {total_enrolled}")
            m3.metric("Total Absent", absent_count)
            attend_per = (len(present_uids)/total_enrolled)*100 if total_enrolled > 0 else 0
            m4.metric("Attendance %", f"{attend_per:.1f}%")

            st.markdown("---")

            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.subheader("📈 Hourly Scanning Trend")
                if not df.empty:
                    df['hour'] = df['time'].dt.hour
                    hourly_data = df.groupby('hour').size().reset_index(name='Scans')
                    fig = px.area(hourly_data, x='hour', y='Scans', color_discrete_sequence=['#3b82f6'])
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Waiting for database connection...")

            with col_right:
                st.subheader("📊 Distribution")
                fig_pie = px.pie(values=[len(present_uids), absent_count], names=['Present', 'Absent'], 
                                 color_discrete_sequence=['#10b981', '#ef4444'], hole=0.5)
                fig_pie.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=300)
                st.plotly_chart(fig_pie, use_container_width=True)

            if not df.empty:
                latest = df.iloc[0]
                st.info(f"🚀 **Latest Activity:** {latest.get('name', 'Unknown')} at {latest['time'].strftime('%I:%M:%S %p')}")

        time.sleep(1) # १ सेकंद थांबा

elif app_mode == "Absentee Tracker":
    st.header("🕵️ Absentee Tracker")
    df_main = fetch_data()
    present_uids = set(df_main["uid"].unique().astype(str)) if not df_main.empty and "uid" in df_main.columns else set()
    absent_uids = set(MASTER_STUDENTS.keys()) - present_uids
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"❌ Absent ({len(absent_uids)})")
        for u in absent_uids: st.error(f"{MASTER_STUDENTS[u]} (ID: {u})")
    with c2:
        st.subheader(f"✅ Present ({len(present_uids)})")
        for u in present_uids: st.success(f"{MASTER_STUDENTS.get(u, 'Guest')} (ID: {u})")

elif app_mode == "Timetable":
    st.header("📅 Schedule")
    st.table(pd.DataFrame([f"{s[0]:02d}:{s[1]:02d}-{s[2]:02d}:{s[3]:02d} | {s[4]}" for s in TIMETABLE], columns=["Schedule"]))