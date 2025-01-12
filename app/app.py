import streamlit as st
import pandas as pd
import os
import glob
from loguru import logger

from pdf2image import convert_from_bytes
from dotenv import load_dotenv
import streamlit_shadcn_ui as ui

from ocr_helper import collecting_pdf_encoded_images, extract_from_encoding, add_metadata
from fuzzy_match_helper import create_select_voter_records, get_matched_name_address

# setting up logger for benchmarking, comment in to write logs to data/logs/benchmark_logs.log
logger.remove()
# logger.add("data/logs/benchmark_logs.log", rotation="10 MB", level="INFO")

# loading environmental variables
if not os.getenv("GITHUB_ACTIONS"):
    load_dotenv('.env', override=True)

# define your open AI API key here; Remember this is a personal notebook! Don't push your API key to the remote repo
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BALLOT_ICON = "app/petition_check.png"
UPLOADED_FILENAME = "ballot.pdf"

##
# DELETE TEMPORARY FILES
##

def wipe_all_temp_files():
    """Wipes all temporary files and resets session state"""
    try:
        # Clear temp_ocr_images directory
        temp_files = [file.path for file in os.scandir('./temp_ocr_images') if file.name != '.gitkeep']
        for file in temp_files:
            os.remove(file)
            
        # Reset session state for data
        if 'voter_records_df' in st.session_state:
            del st.session_state.voter_records_df
        if 'processed_results' in st.session_state:
            del st.session_state.processed_results
            
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
st.header("Ballot Initiative - Signature Verification")
st.caption("Automated signature verification for ballot initiatives")
st.markdown("<hr style='height:3px;border:none;color:#0066cc;background-color:#0066cc;'/>", unsafe_allow_html=True)

# Sidebar with improved styling
with st.sidebar:
    # Add a logo (replace with your own logo path)
    # add_logo(BALLOT_ICON)

    # st.logo(BALLOT_ICON)
    
    st.markdown("# 📋 Automated Petition Signature Validation")
    
    tabs = st.tabs(["ℹ️ About", "🎯 Motivation", "📝 Instructions"])
    
    with tabs[0]:
        st.markdown("""
        <div class="info-box">
        This tool helps verify voter signatures on ballot initiative petitions by comparing them 
        against official voter records. It streamlines the signature verification process 
        and helps ensure the integrity of ballot initiatives.
        </div>
        """, unsafe_allow_html=True)
    
    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            st.error("Current Challenges")
            st.markdown("""
            - ⏰ Time-consuming
            - ❌ Prone to errors
            - 📊 Resource-intensive
            """)
        with col2:
            st.success("Our Solution")
            st.markdown("""
            - ⚡ Efficient
            - ✅ Accurate
            - 🔍 Transparent
            """)
    
    with tabs[2]:
        st.markdown("### Step-by-Step Guide")
        with st.expander("1️⃣ Upload Voter Records", expanded=True):
            st.markdown("""
            - CSV format required
            - Must include:
              - First_Name
              - Last_Name
              - Address details
              - WARD
            """)
        
        with st.expander("2️⃣ Upload Signatures", expanded=True):
            st.markdown("""
            - PDF format only
            - Clear, legible scans
            - One signature per line
            """)
        
        with st.expander("3️⃣ Process & Review", expanded=True):
            st.markdown("""
            - Click 'Process Files'
            - Review matches
            - Export results
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

with col1:
    st.markdown("""
    #### 📄 Voter Records
    Upload your CSV file containing voter registration data.
    Required columns: First_Name, Last_Name, Street details, WARD
    """)
    
    voter_records = st.file_uploader(
        "Choose CSV file",
        type=['csv'],
        key="voter_records",
        help="Upload a CSV file containing voter registration data"
    )
    
    # Process voter records when uploaded
    if voter_records is not None:
        try:
            df = pd.read_csv(voter_records, dtype=str)
            full_name_address_df = create_select_voter_records(df)


            required_columns = ["First_Name", "Last_Name", "Street_Number", 
                             "Street_Name", "Street_Type", "Street_Dir_Suffix", "WARD"]
            
            # Verify required columns
            if not all(col in df.columns for col in required_columns):
                st.error("Missing required columns in CSV file")
            else:
                # Create necessary columns
                df['Full Name'] = df["First_Name"] + ' ' + df['Last_Name']
                df['Full Address'] = df["Street_Number"] + " " + df["Street_Name"] + " " + \
                                   df["Street_Type"] + " " + df["Street_Dir_Suffix"]
                df['Full Name and Full Address'] = df["Full Name"] + ' ' + df["Full Address"]
                
                st.session_state.voter_records_df = df
                st.success("✅ Voter records loaded successfully!")
                
                # Display preview
                with st.expander("Preview Voter Records"):
                    st.dataframe(df.head(), use_container_width=True)
                    st.caption(f"Total records: {len(df):,}")
                
        except Exception as e:
            st.error(f"Error loading voter records: {str(e)}")

with col2:
    st.markdown("""
    #### ✍️ Petition Signatures
    Upload your PDF file containing petition pages with signatures. Ensure these have the printed name and address of the voter. 
    """)
    
    signatures = st.file_uploader(
        "Choose PDF file",
        type=['pdf'],
        key="signatures",
        help="Upload a PDF containing scanned signature pages"
    )
    
    # Process PDF when uploaded
    if signatures is not None:
        try:
            # with st.status("Processing PDF...", expanded=True) as status:
            # Create temp directory if it doesn't exist
            os.makedirs('temp_ocr_images', exist_ok=True)
            
            # Save PDF to temp directory
            pdf_bytes = signatures.read()
            pdf_path = os.path.join('temp_ocr_images', UPLOADED_FILENAME)
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
        
            # Convert first page to image for preview
            preview_image = convert_from_bytes(pdf_bytes, first_page=1, last_page=1)[0]
            num_pages = len(convert_from_bytes(pdf_bytes))

            st.success("✅ Petition signatures loaded successfully!")
            
            # Display preview
            with st.expander("Preview Petition Signatures"):

                # Show preview without expander
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
        process_button = st.button("🚀 Process Files", type="primary", use_container_width=True)
        if process_button:
            with st.spinner("Matching records..."):
                # try:
                matching_bar = st.progress(0, text="Performing Name Match")
                matched_list = []
                
                # Get list of all .jpg files in temp_ocr_images directory
                pdf_full_path = glob.glob(os.path.join('temp_ocr_images',UPLOADED_FILENAME))[0]

                # encoded images
                encoded_images = collecting_pdf_encoded_images(pdf_full_path)
                
                full_data_list = []
                for page_no, encoding in enumerate(encoded_images):
                    print(f"Processing Page {page_no+1} of {len(encoded_images)}")
                    ocr_data = extract_from_encoding(encoding)
                    ocr_data = add_metadata(ocr_data, page_no, UPLOADED_FILENAME)
                    # full_data_list +=ocr_data

                    for dict_ in ocr_data:
                        temp_dict = {k: v for k, v in dict_.items()}
                        if temp_dict['Name'] == '':
                            continue
                        temp_dict['OCR Name'] = dict_['Name'].title()
                        temp_dict['OCR Address'] = dict_['Address']
                        temp_dict['OCR Ward'] = dict_['Ward']

                        # get matched name and address
                        high_score_list = get_matched_name_address(ocr_name=temp_dict['OCR Name'], 
                                                                    ocr_address=temp_dict['OCR Address'], 
                                                                    select_voter_records=full_name_address_df)
                        
                        matched_name, matched_address, net_score, _ = high_score_list[0]
                        if matched_name == '':
                            continue

                        temp_dict["Matched Name"] = matched_name
                        temp_dict["Matched Address"] = matched_address
                        temp_dict["Match Score"] = net_score
                        temp_dict["Valid"] = net_score >= 85.0

                        matched_list.append(temp_dict)
                    
                    full_data_list.append(temp_dict)
                    
                    matching_bar.progress((page_no+1)/len(encoded_images), 
                                        text=f"Matching OCR Names - page {page_no+1} of {len(encoded_images)}")
                
                # Store results in session state
                st.session_state.processed_results = pd.DataFrame(
                    matched_list, 
                    columns=["OCR Name", "OCR Address", "Matched Name", "Matched Address", "Match Score", "Valid", "Date", "Page Number", "Row Number", "Filename"]
                )
                
                # Clear progress bar
                matching_bar.empty()
                    
                # except Exception as e:
                #     st.error(f"Error during processing: {str(e)}")

# Display results if available
if st.session_state.get('processed_results') is not None:
    st.markdown("### Results")
    tabs = st.tabs(["📊 Data Table", "📈 Statistics"])
    
    with tabs[0]:
        edited_df = st.data_editor(
            st.session_state.processed_results,
            use_container_width=True,
            hide_index=True
        )
    
    with tabs[1]:
        results_df = st.session_state.processed_results
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
                title="Success Rate",
                content=f"{(sum(results_df['Valid'])/len(results_df))*100:.1f}%",
                description="Match success rate"
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
