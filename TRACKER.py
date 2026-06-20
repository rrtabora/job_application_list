import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

# Page layout setup
st.set_page_config(page_title="Europa Job Tracker", layout="wide")
st.title("💼 Live Job Application Tracker Dashboard")

# --- CONNECT TO GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_live_data():
    try:
        df = conn.read(ttl=0) 
        df = df.dropna(how='all')
        
        if 'Company' in df.columns:
            df = df[df['Company'].notna() & (df['Company'] != "")]
        else:
            return pd.DataFrame(columns=[
                'Company', 'URL of Job Description', 'Role', 'Country', 
                'Date of Application', 'Running Time', 'Stage', 'Notes'
            ])
        
        stage_mapping = {
            'Application Sent': 'Application Sent', 'Declined': 'Declined',
            'Interviewing': 'Interview', 'Interview': 'Interview',
            'Offer': 'Accepted', 'Accepted': 'Accepted'
        }
        df['Stage'] = df['Stage'].map(stage_mapping).fillna('Application Sent')
        df['Role'] = df['Role'].fillna('Not Specified').replace('', 'Not Specified')
        df['Country'] = df['Country'].fillna('Not Specified').replace('', 'Not Specified')
        df['URL of Job Description'] = df['URL of Job Description'].fillna('')
        df['Notes'] = df['Notes'].fillna('')
        return df
    except Exception as e:
        st.error(f"Error reading from Google Sheet: {e}")
        return pd.DataFrame(columns=['Company', 'URL of Job Description', 'Role', 'Country', 'Date of Application', 'Running Time', 'Stage', 'Notes'])

# Fetch live tracking data
df = load_live_data()

# --- DYNAMIC RUNNING TIME CALCULATION ---
today = pd.to_datetime(datetime.today().date())
parsed_dates = pd.to_datetime(df['Date of Application'], errors='coerce')
df['Running Time'] = (today - parsed_dates).dt.days.fillna(0).astype(int)
df.loc[df['Stage'].isin(['Accepted', 'Declined']), 'Running Time'] = 0

# --- METRICS SECTION ---
st.header("📊 Key Metrics")
col1, col2, col3, col4 = st.columns(4)
total_apps = len(df)
active_apps = len(df[df['Stage'] == 'Application Sent'])
interview_apps = len(df[df['Stage'] == 'Interview'])
accepted_apps = len(df[df['Stage'] == 'Accepted'])
declined_apps = len(df[df['Stage'] == 'Declined'])
decline_rate = int((declined_apps / total_apps * 100)) if total_apps > 0 else 0

with col1: st.metric("Total Applications", total_apps)
with col2: st
