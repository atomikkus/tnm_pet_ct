"""
TNM Staging Streamlit App
Rewritten to use standard Streamlit components and save data locally.
"""

import streamlit as st
import requests
import json
import os
import shutil
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DATA_DIR = "data"
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

# Ensure directories exist
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

st.set_page_config(page_title="TNM Staging Analyzer", layout="wide")

def save_uploaded_file(uploaded_file) -> str:
    """Save uploaded file to disk and return the path."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uploaded_file.name}"
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def save_result(original_filename: str, api_result: Dict, feedback: Dict):
    """Save the analysis result and user feedback to a JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{original_filename}.json"
    file_path = os.path.join(RESULTS_DIR, filename)
    
    data = {
        "timestamp": datetime.now().isoformat(),
        "original_filename": original_filename,
        "api_result": api_result,
        "user_feedback": feedback
    }
    
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    
    return file_path

def stage_from_pdf(file_path: str) -> Optional[Dict[str, Any]]:
    """Send PDF to API for staging."""
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/pdf")}
            response = requests.post(
                f"{API_BASE_URL}/api/v1/stage/pdf",
                files=files,
                timeout=120
            )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

import pandas as pd

def render_deep_dive(staging: Dict[str, Any]):
    """Render detailed staging information in a user-friendly format."""
    st.markdown("---")
    tnm_stage = staging.get('tnm_stage', 'N/A')
    st.subheader(f"Deep Dive Analysis - Stage {tnm_stage}")

    # Tumor (T)
    st.markdown("### Tumor (T-Stage)")
    tumor = staging.get("tumor", {})
    
    # Create a cleaner layout for Tumor details using a dictionary for display
    tumor_data = {
        "Stage": tumor.get('stage', 'N/A'),
        "Size": f"{tumor.get('tumor_size_mm', 'N/A')} mm",
        "Location": tumor.get('location', 'N/A'),
        "Invasion": ', '.join(tumor.get('invasion', [])) or 'None',
        "Nodules": ', '.join(tumor.get('separate_nodules', [])) or 'None'
    }
    
    # Display as key-value pairs in columns
    cols = st.columns(3)
    for i, (key, value) in enumerate(tumor_data.items()):
        with cols[i % 3]:
            st.markdown(f"**{key}**")
            st.write(value)
    
    if tumor.get("evidence"):
        st.info(f"**Evidence:** {tumor['evidence']}")

    st.markdown("---")

    # Nodes (N)
    st.markdown("### Lymph Nodes (N-Stage)")
    nodes = staging.get("nodes", {})
    st.write(f"**Stage:** {nodes.get('stage', 'N/A')}")
    
    involved = nodes.get("involved_nodes", [])
    if involved:
        st.write("**Involved Nodes:**")
        # Convert to DataFrame for table display
        df_nodes = pd.DataFrame(involved)
        # Select and rename columns if they exist
        cols_to_show = ['station', 'laterality', 'description']
        df_nodes = df_nodes[[c for c in cols_to_show if c in df_nodes.columns]]
        st.table(df_nodes)
    else:
        st.write("No involved nodes detected.")

    if nodes.get("evidence"):
        st.info(f"**Evidence:** {nodes['evidence']}")

    st.markdown("---")

    # Metastasis (M)
    st.markdown("### Metastasis (M-Stage)")
    metastasis = staging.get("metastasis", {})
    st.write(f"**Stage:** {metastasis.get('stage', 'N/A')}")
    
    sites = metastasis.get("metastasis_sites", [])
    if sites:
        st.write("**Metastatic Sites:**")
        # Convert to DataFrame for table display
        df_sites = pd.DataFrame(sites)
        # Select and rename columns if they exist
        cols_to_show = ['organ_system', 'location', 'description']
        df_sites = df_sites[[c for c in cols_to_show if c in df_sites.columns]]
        st.table(df_sites)
    else:
        st.write("No distant metastasis detected.")

    if metastasis.get("evidence"):
        st.info(f"**Evidence:** {metastasis['evidence']}")

def main():
    st.title("TNM Staging Analyzer")
    st.write("Upload a PET-CT radiology report (PDF) to get TNM staging.")

    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

    if uploaded_file:
        # Save file immediately
        file_path = save_uploaded_file(uploaded_file)
        st.success(f"File saved: {os.path.basename(file_path)}")

        if st.button("Analyze Report", type="primary"):
            with st.spinner("Analyzing..."):
                result = stage_from_pdf(file_path)
                
                if result:
                    st.session_state.current_result = result
                    st.session_state.current_file = os.path.basename(file_path)
                    st.session_state.feedback_submitted = False
                    # Reset deep dive state on new analysis
                    st.session_state.show_deep_dive = False

    # Display Results if available
    if "current_result" in st.session_state:
        result = st.session_state.current_result
        staging = result.get("staging", {})

        st.divider()
        st.header("Staging Results")

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("T-Stage", staging.get("tumor", {}).get("stage", "N/A"))
        col2.metric("N-Stage", staging.get("nodes", {}).get("stage", "N/A"))
        col3.metric("M-Stage", staging.get("metastasis", {}).get("stage", "N/A"))
        col4.metric("Overall Stage", staging.get("overall_stage", "N/A"))

        # Summary
        st.subheader("Summary")
        st.write(staging.get("summary", "No summary available."))

        # Deep Dive Button
        if st.button("🔍 Deep Dive Analysis"):
            st.session_state.show_deep_dive = not st.session_state.get('show_deep_dive', False)
        
        if st.session_state.get('show_deep_dive', False):
            render_deep_dive(staging)

        st.divider()
        st.header("Feedback & Correction")

        if not st.session_state.get("feedback_submitted", False):
            is_correct = st.radio("Is the staging correct?", ["Select...", "Yes", "No"], key="is_correct_radio")

            if is_correct == "Yes":
                if st.button("Submit Feedback"):
                    feedback = {"is_correct": True}
                    save_path = save_result(st.session_state.current_file, result, feedback)
                    st.session_state.feedback_submitted = True
                    st.success(f"Feedback saved to {save_path}")
                    st.rerun()

            elif is_correct == "No":
                st.write("Please provide the correct values:")
                with st.form("correction_form"):
                    c_col1, c_col2 = st.columns(2)
                    correct_t = c_col1.text_input("Correct T-Stage")
                    correct_n = c_col2.text_input("Correct N-Stage")
                    correct_m = c_col1.text_input("Correct M-Stage")
                    correct_overall = c_col2.text_input("Correct Overall Stage")
                    comments = st.text_area("Additional Comments")

                    if st.form_submit_button("Submit Correction"):
                        feedback = {
                            "is_correct": False,
                            "corrections": {
                                "t_stage": correct_t,
                                "n_stage": correct_n,
                                "m_stage": correct_m,
                                "overall_stage": correct_overall,
                                "comments": comments
                            }
                        }
                        save_path = save_result(st.session_state.current_file, result, feedback)
                        st.session_state.feedback_submitted = True
                        st.success(f"Correction saved to {save_path}")
                        st.rerun()
        else:
            st.info("✅ Feedback submitted for this report.")
            if st.button("Analyze Another Report"):
                del st.session_state.current_result
                del st.session_state.current_file
                del st.session_state.feedback_submitted
                st.rerun()

if __name__ == "__main__":
    main()
