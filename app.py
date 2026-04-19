import time
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
from datetime import datetime, time

from collections import Counter

# ──────────────────────────────────────────────
#  TIMETABLE CONFIG  ← edit your subjects here
#  Format: (start_hour, start_min, end_hour, end_min, "Subject Name")
# ──────────────────────────────────────────────
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
    ct = time(t.hour, t.minute)
    for sh, sm, eh, em, subject in TIMETABLE:
        if time(sh, sm) <= ct < time(eh, em):
            return subject
    return "—"

def get_current_subject() -> tuple:
    now = datetime.now()
    ct  = time(now.hour, now.minute)
    for sh, sm, eh, em, subject in TIMETABLE:
        if time(sh, sm) <= ct < time(eh, em):
            return subject, f"{sh:02d}:{sm:02d} – {eh:02d}:{em:02d}"
    return "No Class", "Outside schedule"

# ──────────────────────────────────────────────
#  Firebase Init
# ──────────────────────────────────────────────
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        # Streamlit secrets directly dictionary mhanun vapra
        cred_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://attendance-e4940-default-rtdb.firebaseio.com/"
        })
init_firebase()

# ──────────────────────────────────────────────
#  Page Config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="RFID Live Attendance",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
#  Custom CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: #0a0c0f !important;
    color: #e8ecf4 !important;
}
.stApp { background-color: #0a0c0f !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }

.rfid-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 32px;
    background: #111318;
    border-bottom: 1px solid #222730;
    position: relative; overflow: hidden;
    margin-bottom: 24px;
}
.rfid-header::before {
    content: ''; position: absolute;
    top: 0; left: -100%; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #00e5a0, transparent);
    animation: scan 3s linear infinite;
}
@keyframes scan { to { left: 100%; } }

.brand { display: flex; align-items: center; gap: 12px; }
.brand-icon {
    width: 40px; height: 40px; border-radius: 10px;
    background: #0a2a1e; border: 1px solid rgba(0,229,160,.3);
    display: flex; align-items: center; justify-content: center; font-size: 20px;
}
.brand-name { font-size: 18px; font-weight: 600; letter-spacing: -.3px; color: #e8ecf4; }
.brand-sub  { font-size: 11px; color: #5a6278; font-family: 'Space Mono', monospace; letter-spacing: .5px; }
.hdr-right  { display: flex; align-items: center; gap: 16px; }
.clock-chip { font-family: 'Space Mono', monospace; font-size: 13px; color: #5a6278; }
.live-pill  {
    display: flex; align-items: center; gap: 7px;
    background: rgba(0,229,160,.1); border: 1px solid rgba(0,229,160,.25);
    border-radius: 99px; padding: 5px 14px;
    font-size: 12px; font-weight: 500; color: #00e5a0;
    font-family: 'Space Mono', monospace; letter-spacing: .5px;
}
.live-dot {
    width: 7px; height: 7px; border-radius: 50%; background: #00e5a0;
    animation: pulse 1.4s ease-in-out infinite;
}
@keyframes pulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(0,229,160,.4); }
    50%      { box-shadow: 0 0 0 5px rgba(0,229,160,0); }
}

.stat-card {
    background: #111318; border: 1px solid #222730;
    border-radius: 14px; padding: 18px 20px;
    transition: border-color .2s; min-height: 110px;
}
.stat-card:hover { border-color: rgba(255,255,255,.15); }
.stat-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.stat-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #5a6278; }
.stat-icon  { font-size: 16px; }
.stat-value    { font-family: 'Space Mono', monospace; font-size: 26px; font-weight: 700; line-height: 1.1; }
.stat-value-sm { font-family: 'Space Mono', monospace; font-size: 17px; font-weight: 700; line-height: 1.3; }
.sv-green  { color: #00e5a0; }
.sv-blue   { color: #00aaff; }
.sv-purple { color: #a78bfa; }
.sv-red    { color: #ff4d6d; }
.stat-sub  { font-size: 11px; color: #5a6278; margin-top: 6px; font-family: 'Space Mono', monospace; }

.last-scan-banner {
    margin: 0 32px 20px;
    border-radius: 12px;
    background: rgba(0,229,160,.06); border: 1px solid rgba(0,229,160,.2);
    padding: 12px 18px; display: flex; align-items: center; gap: 14px;
}
.ls-dot   { width: 10px; height: 10px; border-radius: 50%; background: #00e5a0;
            animation: pulse 1.4s ease-in-out infinite; flex-shrink: 0; }
.ls-label { font-size: 10px; text-transform: uppercase; letter-spacing: .8px;
            color: #00e5a0; font-weight: 600; font-family: 'Space Mono', monospace; }
.ls-name  { font-size: 15px; font-weight: 600; color: #e8ecf4; margin-top: 2px; }
.ls-meta  { font-family: 'Space Mono', monospace; font-size: 12px; color: #5a6278; margin-left: auto; }
.ls-subject {
    font-size: 11px; font-weight: 600; font-family: 'Space Mono', monospace;
    color: #a78bfa; background: rgba(167,139,250,.1);
    border: 1px solid rgba(167,139,250,.25);
    border-radius: 99px; padding: 2px 10px; flex-shrink: 0;
}

.section-hdr {
    display: flex; align-items: center; justify-content: space-between;
    margin: 0 32px 10px;
}
.section-title { font-size: 13px; font-weight: 600; color: #e8ecf4; }
.section-pill  {
    font-family: 'Space Mono', monospace; font-size: 11px; color: #5a6278;
    background: #181c22; padding: 3px 10px;
    border-radius: 99px; border: 1px solid #222730;
}

.subject-wrap { margin: 0 32px 24px; border: 1px solid #222730; border-radius: 14px; padding: 14px 20px; background: #0a0c0f; }
.subject-row  { display: flex; align-items: center; gap: 10px; margin-bottom: 7px; }
.subject-lbl  { font-size: 12px; color: #e8ecf4; width: 130px; flex-shrink: 0;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.subject-track { flex: 1; height: 8px; background: #181c22; border-radius: 4px; overflow: hidden; }
.subject-fill     { height: 100%; border-radius: 4px; background: #a78bfa; }
.subject-fill-dim { height: 100%; border-radius: 4px; background: rgba(167,139,250,.25); }
.subject-cnt  { font-family: 'Space Mono', monospace; font-size: 11px; color: #5a6278; width: 28px; text-align: right; }

[data-testid="stDataFrame"] { border: none !important; }
[data-testid="column"] { padding: 0 6px !important; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
#  Session state
# ──────────────────────────────────────────────
if "expected" not in st.session_state:
    st.session_state.expected = 30

# ──────────────────────────────────────────────
#  Firebase fetch
# ──────────────────────────────────────────────
def fetch_data() -> pd.DataFrame:
    ref  = db.reference("attendance")
    data = ref.get()
    if not data:
        return pd.DataFrame()
    records = list(data.values()) if isinstance(data, dict) else data
    df = pd.DataFrame(records)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df = df.sort_values("time", ascending=False).reset_index(drop=True)
    return df

# ──────────────────────────────────────────────
#  Metrics
# ──────────────────────────────────────────────
def compute_metrics(df: pd.DataFrame, expected: int) -> dict:
    if df.empty:
        return dict(total=0, unique=0, absent=expected, subject_dist={})

    total  = len(df)
    uid_col = "uid" if "uid" in df.columns else ("name" if "name" in df.columns else None)
    unique  = df[uid_col].nunique() if uid_col else total
    absent  = max(0, expected - unique)

    subject_dist = {}
    if "time" in df.columns:
        subjects = df["time"].dropna().apply(get_subject_for_time)
        subject_dist = dict(Counter(subjects))
        subject_dist.pop("—", None)

    return dict(total=total, unique=unique, absent=absent, subject_dist=subject_dist)

# ──────────────────────────────────────────────
#  HTML builders
# ──────────────────────────────────────────────
def header_html(now: str) -> str:
    return f"""
    <div class="rfid-header">
      <div class="brand">
        <div class="brand-icon">📡</div>
        <div>
          <div class="brand-name">RFID Attendance</div>
          <div class="brand-sub">LIVE SYSTEM · FIREBASE RT</div>
        </div>
      </div>
      <div class="hdr-right">
        <div class="clock-chip">{now}</div>
        <div class="live-pill"><div class="live-dot"></div>SCANNING</div>
      </div>
    </div>"""

def stat_card_html(label, value, css_class, icon, sub, small=False) -> str:
    val_cls = "stat-value-sm" if small else "stat-value"
    return f"""
    <div class="stat-card">
      <div class="stat-top">
        <div class="stat-label">{label}</div>
        <div class="stat-icon">{icon}</div>
      </div>
      <div class="{val_cls} {css_class}">{value}</div>
      <div class="stat-sub">{sub}</div>
    </div>"""

def last_scan_html(name, scan_time, subject) -> str:
    return f"""
    <div class="last-scan-banner">
      <div class="ls-dot"></div>
      <div>
        <div class="ls-label">Last scan detected</div>
        <div class="ls-name">{name}</div>
      </div>
      <div class="ls-subject">{subject}</div>
      <div class="ls-meta">{scan_time}</div>
    </div>"""

def subject_bars_html(subject_dist: dict, top_subject: str) -> str:
    if not subject_dist:
        return "<div style='padding:16px;color:#5a6278;font-size:13px'>No subject data yet.</div>"
    max_val  = max(subject_dist.values(), default=1)
    sorted_s = sorted(subject_dist.items(), key=lambda x: x[1], reverse=True)
    rows = ""
    for subj, cnt in sorted_s:
        pct      = round((cnt / max_val) * 100)
        fill_cls = "subject-fill" if subj == top_subject else "subject-fill-dim"
        rows += f"""
        <div class="subject-row">
          <div class="subject-lbl">{subj}</div>
          <div class="subject-track"><div class="{fill_cls}" style="width:{pct}%"></div></div>
          <div class="subject-cnt">{cnt}</div>
        </div>"""
    return f'<div class="subject-wrap">{rows}</div>'

def build_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "time" in out.columns:
        out["Subject"]  = out["time"].apply(lambda t: get_subject_for_time(t) if pd.notna(t) else "—")
        out["Time"]     = out["time"].dt.strftime("%H:%M:%S")

    cols   = []
    rename = {}
    if "name" in out.columns: cols.append("name");  rename["name"] = "Name"
    if "uid"  in out.columns: cols.append("uid");   rename["uid"]  = "UID"
    if "Subject" in out.columns: cols.append("Subject")
    if "Time"    in out.columns: cols.append("Time")

    out = out[cols].rename(columns=rename)
    out.index = range(len(out), 0, -1)
    return out

# ──────────────────────────────────────────────
#  Sidebar
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.session_state.expected = st.number_input(
        "Expected headcount", min_value=1, max_value=1000,
        value=st.session_state.expected, step=1,
    )
    st.markdown("---")
    refresh_interval = st.slider("Refresh interval (sec)", 2, 30, 5)
    st.markdown("---")
    st.markdown("### 🕐 Today's Timetable")
    for sh, sm, eh, em, subj in TIMETABLE:
        st.markdown(f"`{sh:02d}:{sm:02d}–{eh:02d}:{em:02d}` &nbsp; {subj}", unsafe_allow_html=True)

# ──────────────────────────────────────────────
#  Main render loop
# ──────────────────────────────────────────────
placeholder = st.empty()

while True:
    df      = fetch_data()
    metrics = compute_metrics(df, st.session_state.expected)
    now     = datetime.now().strftime("%H:%M:%S")

    curr_subj, curr_range = get_current_subject()
    subject_dist = metrics["subject_dist"]
    top_subject  = max(subject_dist, key=subject_dist.get) if subject_dist else "—"
    top_count    = subject_dist.get(top_subject, 0)

    with placeholder.container():

        # Header
        st.markdown(header_html(now), unsafe_allow_html=True)

        # Stat cards
        col1, col2, col3, col4 = st.columns(4, gap="small")

        with col1:
            st.markdown(stat_card_html(
                "Total Scans", metrics["total"], "sv-green", "📡", "All time"
            ), unsafe_allow_html=True)

        with col2:
            st.markdown(stat_card_html(
                "Unique Present", metrics["unique"], "sv-blue", "👤", "Distinct IDs"
            ), unsafe_allow_html=True)

        with col3:
            is_small = len(curr_subj) > 10
            st.markdown(stat_card_html(
                "Current Subject", curr_subj, "sv-purple", "📚", curr_range, small=is_small
            ), unsafe_allow_html=True)

        with col4:
            st.markdown(stat_card_html(
                "Absent Today", metrics["absent"], "sv-red", "⚠",
                f"Expected: {st.session_state.expected}"
            ), unsafe_allow_html=True)

        # Last scan banner
        if not df.empty:
            latest  = df.iloc[0]
            ls_name = latest.get("name") or latest.get("uid") or "Unknown"
            ls_time = latest["time"].strftime("%H:%M:%S") if pd.notna(latest.get("time")) else "—"
            ls_subj = get_subject_for_time(latest["time"]) if pd.notna(latest.get("time")) else "—"
            st.markdown(last_scan_html(ls_name, ls_time, ls_subj), unsafe_allow_html=True)

        # Subject distribution chart
        top_label = f"Top: {top_subject} ({top_count})" if top_subject != "—" else "No data"
        st.markdown(f"""
        <div class="section-hdr">
          <div class="section-title">Scans by subject</div>
          <div class="section-pill">{top_label}</div>
        </div>""", unsafe_allow_html=True)
        st.markdown(subject_bars_html(subject_dist, top_subject), unsafe_allow_html=True)

        # Live feed table
        table_df = build_table(df)
        count    = len(table_df)
        st.markdown(f"""
        <div class="section-hdr">
          <div class="section-title">Live scan feed</div>
          <div class="section-pill">{count} records</div>
        </div>""", unsafe_allow_html=True)

        if table_df.empty:
            st.info("No scan records found in Firebase.")
        else:
            st.dataframe(
                table_df,
                use_container_width=True,
                height=min(420, 36 + 35 * count),
            )

    time.sleep(refresh_interval)