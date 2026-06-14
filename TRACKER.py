import streamlit as st
import pandas as pd
from datetime import datetime

# Path to your existing data file
FILE_NAME = "Europa - Sheet3.csv"

def load_data():
    try:
        # Load the CSV and drop completely empty formatting artifacts at the bottom
        df = pd.read_csv(FILE_NAME)
        df = df.dropna(how='all')
        df = df[df['Company'].notna()]
        
        # Standardize stages to your preferred four options
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
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            'Company', 'URL of Job Description', 'Role', 'Country', 
            'Date of Application', 'Running Time', 'Stage', 'Notes'
        ])

# Load data into session state so edits persist
if 'df' not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# Page layout setup
st.set_page_config(page_title="Europa Job Tracker", layout="wide")
st.title("💼 Job Application Tracker Dashboard")

# --- METRICS SECTION ---
st.header("📊 Key Metrics")
col1, col2, col3, col4 = st.columns(4)

total_apps = len(df)
active_apps = len(df[df['Stage'] == 'Application Sent'])
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
    
    submit = st.form_submit_with_button = st.form_submit_button("Log Application")

    if submit:
        if company:
            final_role = role if role else "Not Specified"
            new_row = {
                'Company': company,
                'URL of Job Description': url,
                'Role': final_role,
                'Country': country,
                'Date of Application': date_app.strftime('%m/%d/%Y'),
                'Running Time': 0,
                'Stage': stage,
                'Notes': notes
            }
            updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            updated_df.to_csv(FILE_NAME, index=False)
            st.session_state.df = updated_df
            st.success(f"Successfully added {final_role} at {company}!")
            st.rerun()
        else:
            st.error("Please fill out at least the 'Company Name' field.")

st.markdown("---")

# --- FILTER & EDIT DATA ---
st.header("🔍 Edit & View Applications")
st.info("💡 **Tip:** Double-click on any cell in the **Stage** column to pick a new status from the dropdown list. Click **Save Table Changes** below when done.")

# Filters
allowed_stages = ["Application Sent", "Interview", "Accepted", "Declined"]
stage_filter = st.multiselect("Filter table view by Stage", options=allowed_stages, default=allowed_stages)
search_query = st.text_input("Search by Company, Role, or Country")

# We apply a temporary filter view, but we want to map edits back to the master dataframe indices
filtered_df = df[df['Stage'].isin(stage_filter)]

if search_query:
    filtered_df = filtered_df[
        filtered_df['Company'].str.contains(search_query, case=False, na=False) |
        filtered_df['Role'].str.contains(search_query, case=False, na=False) |
        filtered_df['Country'].str.contains(search_query, case=False, na=False)
    ]

# Use data_editor to allow inline editing of the Stage dropdown
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
        # Make tracking indices and static metadata non-editable to avoid accidents
        "Company": st.column_config.Column(disabled=True),
        "Date of Application": st.column_config.Column(disabled=True),
        "Running Time": st.column_config.Column(disabled=True),
    },
    hide_index=True,
    use_container_width=True,
    key="table_editor"
)

# Save Button for Edits
if st.button("💾 Save Table Changes", type="primary"):
    # Merge edits back into master data using the unique dataframe indexes
    df.update(edited_table)
    df.to_csv(FILE_NAME, index=False)
    st.session_state.df = df
    st.success("Changes saved successfully to your CSV file!")
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