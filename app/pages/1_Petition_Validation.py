import streamlit as st
import pandas as pd
import os
import glob
from loguru import logger
import time
from pdf2image import convert_from_bytes
from dotenv import load_dotenv
import streamlit_shadcn_ui as ui
import json

from ocr_helper import collecting_pdf_encoded_images, extract_from_encoding, add_metadata, create_ocr_df
from fuzzy_match_helper import create_select_voter_records, get_matched_name_address, create_ocr_matched_df


# setting up logger for benchmarking, comment in to write logs to data/logs/benchmark_logs.log
logger.remove()
# logger.add("data/logs/benchmark_logs.log", rotation="10 MB", level="INFO")

# loading environmental variables
load_dotenv('.env', override=True)

# define your open AI API key here; Remember this is a personal notebook! Don't push your API key to the remote repo
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BALLOT_ICON = "app/petition_check.png"
UPLOADED_FILENAME = "ballot.pdf"

repo_name = 'Ballot-Initiative'
REPODIR = os.getcwd().split(repo_name)[0] + repo_name

# load config
with open('config.json', 'r') as f:
    config = json.load(f)


##
# DELETE TEMPORARY FILES
##

def wipe_all_temp_files():
    """Wipes all temporary files and resets session state"""
    try:
        # Clear temp directory
        temp_files = [file.path for file in os.scandir('./temp') if file.name != '.gitkeep']
        for file in temp_files:
            os.remove(file)
            
       # Reset session state for data and files
        if 'voter_records_df' in st.session_state:
            del st.session_state.voter_records_df
        if 'processed_results' in st.session_state:
            del st.session_state.processed_results
        if 'signature_file' in st.session_state:
            del st.session_state.signature_file
        if 'voter_records_file' in st.session_state:
            del st.session_state.voter_records_file
            
        # Instead of directly modifying file uploader states,
        # we'll use a flag to trigger a rerun
        st.session_state.clear_files = True
        
        return True
    except Exception as e:
        st.error(f"Error clearing files: {str(e)}")
        return False

##
# STREAMLIT APPLICATION
##

st.set_page_config(page_title="Petition Validation", page_icon="🗳️")

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #cce5ff;
        border: 1px solid #b8daff;
        color: #004085;
    }
    </style>
""", unsafe_allow_html=True)

# Application Header
st.header("Petition Validation")
st.caption("Automated signature verification for ballot initiatives")
st.markdown("<hr style='height:3px;border:none;color:#0066cc;background-color:#0066cc;'/>", unsafe_allow_html=True)

start_time = None

@st.cache_data
def load_voter_records(voter_records_file):
    """Cache and process voter records file"""
    df = pd.read_csv(voter_records_file, dtype=str)
    
    # Create necessary columns
    df['Full Name'] = df["First_Name"] + ' ' + df['Last_Name']
    df['Full Address'] = df["Street_Number"] + " " + df["Street_Name"] + " " + \
                        df["Street_Type"] + " " + df["Street_Dir_Suffix"]
    return df

@st.cache_data
def load_signatures(signatures_file):
    """Cache and process signatures PDF file"""
    pdf_bytes = signatures_file.read()
    # Create temp directory if it doesn't exist
    os.makedirs('temp', exist_ok=True)
    
    # Save PDF to temp directory
    pdf_path = os.path.join('temp', UPLOADED_FILENAME)
    with open(pdf_path, 'wb') as f:
        f.write(pdf_bytes)
    
    # Convert first page for preview
    images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1,poppler_path = r'poppler-24.02.0/Library/bin')
    preview_image = images[0]
    num_pages = len(images)
    
    return pdf_bytes, preview_image, num_pages


# Sidebar with improved styling
with st.sidebar:
    
    st.markdown("### 📝 Instructions")

    with st.expander("1️⃣ Upload Voter Records", expanded=False):
        st.markdown("""
        - CSV format required
        - Must include:
            - First_Name
            - Last_Name
            - Street_Number
            - Street_Name
            - Street_Type
            - Street_Dir_Suffix
        - Download a sample of fake voter records [here](https://github.com/Civic-Tech-Ballot-Inititiave/Ballot-Initiative/blob/main/sample_data/fake_voter_records.csv)
        """)
    
    with st.expander("2️⃣ Upload Signatures", expanded=False):
        st.markdown("""
        - PDF format only
        - Clear, legible scans
        - One signature per line
        - Download a sample of fake signed petitions [here](https://github.com/Civic-Tech-Ballot-Inititiave/Ballot-Initiative/blob/main/sample_data/fake_signed_petitions_1-10.pdf)
        """)
    
    with st.expander("3️⃣ Process & Review", expanded=False):
        st.markdown("""
        - Click 'Process Files'
        - Review matches
        - Download CSV results
        """)

    with st.expander("4️⃣ Clear Files", expanded=False):
        st.markdown("""
        - Clear temporary files when done
        """)        

# Initialize session state for data storage
if 'voter_records_df' not in st.session_state:
    st.session_state.voter_records_df = None
if 'processed_results' not in st.session_state:
    st.session_state.processed_results = None


# Add this near the top of your app, after session state initialization
if 'clear_files' in st.session_state and st.session_state.clear_files:
    st.session_state.clear_files = False
    st.rerun()


# Main content area with file uploads
st.markdown("### Upload Files")
col1, col2 = st.columns(2, gap="large")

if 'voter_records_file' not in st.session_state:
    st.session_state.voter_records_file = None

with col1:
    st.markdown("""
    #### 📄 Voter Records
    Upload your CSV file containing voter registration data.
    Required columns: `First_Name`, `Last_Name`, `Street_Number`, 
                             `Street_Name`, `Street_Type`, `Street_Dir_Suffix`
    """)
    
    voter_records = st.file_uploader(
        "Choose CSV file",
        type=['csv'],
        key="voter_records",
        help="Upload a CSV file containing voter registration data",
        on_change=lambda: setattr(st.session_state, 'voter_records_file', st.session_state.voter_records)
    )
    
    # Restore file from session state if available
    if voter_records is None and st.session_state.voter_records_file is not None:
        voter_records = st.session_state.voter_records_file    

    # Process voter records when uploaded
    if voter_records is not None:
        try:
            df = load_voter_records(voter_records)
            full_name_address_df = create_select_voter_records(df)

            required_columns = ["First_Name", "Last_Name", "Street_Number", 
                             "Street_Name", "Street_Type", "Street_Dir_Suffix"]
            
            # Verify required columns
            if not all(col in df.columns for col in required_columns):
                st.error("Missing required columns in CSV file")
            else:
                st.session_state.voter_records_df = df
                st.success("✅ Voter records loaded successfully!")
                
                # Display preview
                with st.expander("Preview Voter Records"):
                    st.dataframe(df.head(), use_container_width=True)
                    st.caption(f"Total records: {len(df):,}")
                
        except Exception as e:
            st.error(f"Error loading voter records: {str(e)}")

# Initialize session state for file uploads
if 'signature_file' not in st.session_state:
    st.session_state.signature_file = None

with col2:
    st.markdown("""
    #### ✍️ Petition Signatures
    Upload your PDF file containing petition pages with signatures. Each file will be cropped to focus on the section where the signatures are located. 
    Ensure these sections have the printed name and address of the voter. 
    """)
    
    signatures = st.file_uploader(
        "Choose PDF file",
        type=['pdf'],
        key="signatures",
        help="Upload a PDF containing scanned signature pages",
        on_change=lambda: setattr(st.session_state, 'signature_file', st.session_state.signatures)        
    )
    
    # Restore file from session state if available
    if signatures is None and st.session_state.signature_file is not None:
        signatures = st.session_state.signature_file

    # Process PDF when uploaded
    if signatures is not None:
        try:
            pdf_bytes, preview_image, num_pages = load_signatures(signatures)
            st.success("✅ Petition signatures loaded successfully!")
            
            # Display preview
            with st.expander("Preview Petition Signatures"):
                st.markdown("**Preview of First Page:**")
                st.image(preview_image, width=300)
                st.caption(f"Total pages: {num_pages}")
                
        except Exception as e:
            st.error(f"Error processing ballot signatures: {str(e)}")

# Divider
st.markdown("---")

# Process Files Button
st.markdown("### Process Files")
col1, col2, col3 = st.columns([1,2,1])
with col2:
    if st.session_state.voter_records_df is None or signatures is None:
        st.warning("⚠️ Please upload both files to proceed")
    else:
        # Initialize cancel state if not exists
        if 'processing_cancelled' not in st.session_state:
            st.session_state.processing_cancelled = False
            
        # Show either process or cancel button
        if not st.session_state.get('is_processing', False):
            process_button = st.button("🚀 Process Files", type="primary", use_container_width=True)
            if process_button:
                st.session_state.is_processing = True
                st.rerun()
        else:
            if st.button("⚠️ Cancel Processing", type="secondary", use_container_width=True):
                st.session_state.processing_cancelled = True
                st.session_state.is_processing = False
                st.rerun()
                
        # Process files if in processing state
        if st.session_state.get('is_processing', False):
            start_time = time.time()
            with st.spinner("Processing signatures for validation..."):
                try:
                    matching_bar = st.progress(0, text="Loading PDF of signed petitions...")
                    
                    # Check for cancellation
                    if st.session_state.processing_cancelled:
                        st.warning("Processing cancelled by user")
                        st.session_state.is_processing = False
                        st.session_state.processing_cancelled = False
                        st.rerun()
                        
                    # Rest of your processing code...
                    pdf_full_path = glob.glob(os.path.join('temp', UPLOADED_FILENAME))[0]

                    matching_bar.progress(0.0, text="Converting PDF to images...")
                    time.sleep(2)
                    if st.session_state.processing_cancelled:
                        raise InterruptedError("Processing cancelled by user")

                    ocr_df = create_ocr_df(filedir='temp', 
                                         filename=UPLOADED_FILENAME, 
                                         st_bar=matching_bar)
                    if st.session_state.processing_cancelled:
                        raise InterruptedError("Processing cancelled by user")

                    matching_bar.progress(0.9, text="Compiling Voter Record Data")
                    time.sleep(2)
                    if st.session_state.processing_cancelled:
                        raise InterruptedError("Processing cancelled by user")

                    select_voter_records = create_select_voter_records(st.session_state.voter_records_df)
                    if st.session_state.processing_cancelled:
                        raise InterruptedError("Processing cancelled by user")

                    matching_bar.progress(0.95, text="Matching petition signatures to voter records...")
                    time.sleep(2)
                    if st.session_state.processing_cancelled:
                        raise InterruptedError("Processing cancelled by user")

                    ocr_matched_df = create_ocr_matched_df(
                        ocr_df, 
                        select_voter_records, 
                        threshold=config['BASE_THRESHOLD']
                    )
                    matching_bar.progress(1.0, text="Complete!")
                    
                    st.session_state.processed_results = ocr_matched_df
                    matching_bar.empty()
                    st.session_state.is_processing = False
                    
                except InterruptedError as e:
                    st.warning(str(e))
                    matching_bar.empty()
                except Exception as e:
                    st.error(f"Error during processing: {str(e)}")
                    st.session_state.is_processing = False

@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode("utf-8")

# Display results if available
if st.session_state.get('processed_results') is not None:
    st.markdown("### Results")
    
    # Update Valid column based on threshold
    results_df = st.session_state.processed_results.copy()
    results_df["Valid"] = results_df["Match Score"] >= config['BASE_THRESHOLD']
    
    tabs = st.tabs(["📊 Data Table", "📈 Statistics"])
    if start_time:
        processing_time = time.time() - start_time
        st.caption(f"Processing time: {processing_time:.2f} seconds")

    with tabs[0]:
        edited_df = st.data_editor(
            results_df,
            use_container_width=True,
            hide_index=True
        )

    # Update the download button to use the modified dataframe
    csv = convert_df(results_df)

    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name="validated_petition_signatures.csv",
        mime="text/csv",
    )        
    
    with tabs[1]:
        # results_df = st.session_state.processed_results
        col1, col2, col3 = st.columns(3)
        with col1:
            ui.metric_card(
                title="Total Records",
                content=len(results_df),
                description="Total signatures processed"
            )
        with col2:
            ui.metric_card(
                title="Valid Matches",
                content=sum(results_df["Valid"]),
                description="Signatures verified"
            )
        with col3:
            ui.metric_card(
                title="Percentage Valid",
                content=f"{(sum(results_df['Valid'])/len(results_df))*100:.1f}%",
                description="Percentage of signatures verified"
            )

# Add this near the bottom of your app, before the footer
st.markdown("---")
st.markdown("### Maintenance")
col1, col2, col3 = st.columns([1,2,1])
with col2:
    if st.button("🗑️ Clear All Files", type="secondary", use_container_width=True):
        with st.spinner("Clearing temporary files..."):
            if wipe_all_temp_files():
                st.session_state.clear_files = True
                st.success("✅ All temporary files cleared!")
                st.info("Please refresh the page to start over.")            

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "© 2024 Ballot Initiative Project | "
    "<a href='#'>Privacy Policy</a> | "
    "<a href='#'>Terms of Use</a>"
    "</div>", 
    unsafe_allow_html=True
)
