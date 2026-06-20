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
# Uses the secrets configured in Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

def load_live_data():
    # Read the data live from the Google Sheet
    df = conn.read(ttl=0) # ttl=0 forces an explicit reload, disabling stale cache
    df = df.dropna(how='all')
    
    if 'Company' in df.columns:
        df = df[df['Company'].notna()]
    else:
        # Fallback layout context structure if the sheet is completely empty/new
        return pd.DataFrame(columns=[
            'Company', 'URL of Job Description', 'Role', 'Country', 
            'Date of Application', 'Running Time', 'Stage', 'Notes'
        ])
    
    # Standardize stages to your preferred options
    stage_mapping = {
        'Application Sent': 'Application Sent',
        'Declined': 'Declined',
        'Interviewing': 'Interview',
        'Interview': 'Interview',
        'Offer': 'Accepted',
        'Accepted': 'Accepted'
    }
    df['Stage'] = df['Stage'].map(stage_mapping).fillna('Application Sent')
    
    # Clean up empty text values with placeholders
    df['Role'] = df['Role'].fillna('Not Specified')
    df['Country'] = df['Country'].fillna('Not Specified')
    df['URL of Job Description'] = df['URL of Job Description'].fillna('')
    df['Notes'] = df['Notes'].fillna('')
    return df

# Fetch live tracking data
df = load_live_data()

# --- DYNAMIC RUNNING TIME CALCULATION ---
today = pd.to_datetime(datetime.today().date())
parsed_dates = pd.to_datetime(df['Date of Application'], errors='coerce')

# Dynamically count days elapsed from initial Application Date up to today()
df['Running Time'] = (today - parsed_dates).dt.days.fillna(0).astype(int)

# Terminate active process counters for finished states (Accepted or Declined)
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

with col1:
    st.metric("Total Applications", total_apps)
with col2:
    st.metric("Active (Sent)", active_apps)
with col3:
    st.metric("Declined", declined_apps)
with col4:
    st.metric("Decline Rate", f"{decline_rate}%")

st.markdown("---")

# --- PIPELINE & GRAPH VISUALIZATIONS ---
st.header("🔄 Visual Pipeline Analytics")

# SANKEY DIAGRAM FLOW GENERATION (Matching image_db9ce1.png flow architecture)
if total_apps > 0:
    nodes = [
        "Total Applications",       # 0
        "Application Sent (Active)",# 1
        "Interview Stage",          # 2
        "Interview (Active)",       # 3
        "Accepted 🎉",              # 4
        "Declined ❌"                # 5
    ]
    
    flow_to_active_sent = active_apps
    flow_to_interview_stage = interview_apps + accepted_apps
    flow_to_declined = declined_apps
    
    flow_interview_to_active = interview_apps
    flow_interview_to_accepted = accepted_apps

    sources = []
    targets = []
    values = []

    # 1. Flow from Total Applications node
    if flow_to_active_sent > 0:
        sources.append(0); targets.append(1); values.append(flow_to_active_sent)
    if flow_to_interview_stage > 0:
        sources.append(0); targets.append(2); values.append(flow_to_interview_stage)
    if flow_to_declined > 0:
        sources.append(0); targets.append(5); values.append(flow_to_declined) # Branches out independently

    # 2. Flow downstream out from Interview Stage
    if flow_interview_to_active > 0:
        sources.append(2); targets.append(3); values.append(flow_interview_to_active)
    if flow_interview_to_accepted > 0:
        sources.append(2); targets.append(4); values.append(flow_interview_to_accepted)

    fig_sankey = go.Figure(data=[go.Sankey(
        node = dict(
          pad = 15,
          thickness = 20,
          line = dict(color = "black", width = 0.5),
          label = nodes,
          color = ["#3498db", "#5dade2", "#f39c12", "#f5b041", "#2ecc71", "#e74c3c"]
        ),
        link = dict(
          source = sources,
          target = targets,
          value = values,
          color = ["rgba(93, 173, 226, 0.4)", "rgba(243, 156, 18, 0.4)", "rgba(231, 76, 60, 0.3)", 
                   "rgba(245, 176, 65, 0.4)", "rgba(46, 204, 113, 0.4)"]
      ))])

    fig_sankey.update_layout(title_text="Application Flow Pipeline (Sankey Diagram)", font_size=12, height=450)
    st.plotly_chart(fig_sankey, use_container_width=True)
else:
    st.info("Add application data below to render the flow pipeline visual.")

# STACKED BAR CHART BY COUNTRY (ACTIVE VS INACTIVE)
st.markdown("### 🌍 Applications by Country (Active vs. Inactive)")
if not df.empty:
    chart_df = df.copy()
    
    # Map stages explicitly into binary categories
    chart_df['Status'] = chart_df['Stage'].apply(lambda x: 'Inactive (Declined)' if x == 'Declined' else 'Active (Other Stages)')
    
    # Calculate volume count distributions grouped per country location status split
    country_status_df = chart_df.groupby(['Country', 'Status']).size().reset_index(name='Application Count')
    
    fig_country = px.bar(
        country_status_df, 
        x='Country', 
        y='Application Count', 
        color='Status',
        color_discrete_map={
            'Active (Other Stages)': '#2ecc71',   # Vibrant Green
            'Inactive (Declined)': '#e74c3c'     # Muted Red
        },
        text_auto=True,
        title="Application Status Breakdown Per Country"
    )
    
    # Stack layout config sorting largest aggregate country bars left-most
    fig_country.update_layout(barmode='stack', xaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig_country, use_container_width=True)
else:
    st.info("No data available to display country chart.")

st.markdown("---")

# --- ADD NEW APPLICATION ---
st.header("➕ Add New Application")
with st.form("new_app_form", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        company = st.text_input("Company Name")
        role = st.text_input("Role (e.g., Power BI Specialist)")
    with c2:
        url = st.text_input("Job Description URL")
        country = st.text_input("Country", value="Spain")
    with c3:
        date_app = st.date_input("Date of Application", datetime.today())
        stage = st.selectbox("Stage", ["Application Sent", "Interview", "Accepted", "Declined"])
    
    notes = st.text_area("Notes")
    submit = st.form_submit_button("Log Application")

    if submit:
        if company:
            final_role = role if role else "Not Specified"
            new_row = pd.DataFrame([{
                'Company': company,
                'URL of Job Description': url,
                'Role': final_role,
                'Country': country,
                'Date of Application': date_app.strftime('%m/%d/%Y'),
                'Running Time': 0,
                'Stage': stage,
                'Notes': notes
            }])
            # Append rows natively into structural matrix and upload directly to Google Sheets
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success(f"Successfully logged {final_role} at {company} to Google Sheets!")
            st.rerun()
        else:
            st.error("Please fill out at least the 'Company Name' field.")

st.markdown("---")

# --- FILTER & EDIT DATA ---
st.header("🔍 Edit & View Applications")
st.info("💡 **Tip:** Double-click on any cell in the **Stage** column to pick a new status from the dropdown list. Click **Save Table Changes** below when done.")

allowed_stages = ["Application Sent", "Interview", "Accepted", "Declined"]
stage_filter = st.multiselect("Filter table view by Stage", options=allowed_stages, default=allowed_stages)
search_query = st.text_input("Search by Company, Role, or Country")

filtered_df = df[df['Stage'].isin(stage_filter)]

if search_query:
    filtered_df = filtered_df[
        filtered_df['Company'].str.contains(search_query, case=False, na=False) |
        filtered_df['Role'].str.contains(search_query, case=False, na=False) |
        filtered_df['Country'].str.contains(search_query, case=False, na=False)
    ]

# Display data interactive spreadsheet interface component config
edited_table = st.data_editor(
    filtered_df,
    column_config={
        "Stage": st.column_config.SelectboxColumn(
            "Stage",
            help="The current status of your application",
            width="medium",
            options=allowed_stages,
            required=True,
        ),
        "Company": st.column_config.Column(disabled=True),
        "Date of Application": st.column_config.Column(disabled=True),
        "Running Time": st.column_config.Column(disabled=True),
    },
    hide_index=True,
    use_container_width=True,
    key="table_editor"
)

# Sync manual data editor revisions permanently down to the Cloud Sheets connection target
if st.button("💾 Save Table Changes", type="primary"):
    df.update(edited_table)
    conn.update(data=df)
    st.success("Changes saved successfully to Google Sheets!")
    st.rerun()

st.markdown("---")

# --- EXPORT TO CSV SECTION ---
st.markdown("### 📥 Export Your Table")
csv_data = filtered_df.to_csv(index=False).encode('utf-8')

st.download_button(
    label="Download Current Table View as CSV",
    data=csv_data,
    file_name=f"job_applications_export_{datetime.today().strftime('%Y%m%d')}.csv",
    mime="text/csv",
    help="Click here to download your filtered tracker view"
)
