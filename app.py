"""Streamlit Dashboard for Conference ICP Validator"""

import streamlit as st
import pandas as pd
from crew_setup import run_pipeline
from agents.shared_state import shared_state
from utils.event_logger import event_logger
import os
import time

st.set_page_config(
    page_title="Conference ICP Validator",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Field Service Conference ICP Validator")
st.markdown("**AI-Powered Lead Qualification for Ascendo.AI**")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")

    st.markdown("### 📄 Input PDFs")
    input_dir = st.text_input(
        "Input Directory",
        value="data/input"
    )

    # Check for PDFs in directory
    import glob
    pdf_files = glob.glob(os.path.join(input_dir, '*.pdf')) if os.path.exists(input_dir) else []

    if pdf_files:
        st.success(f"✅ Found {len(pdf_files)} PDF(s)")
        for pdf in pdf_files:
            st.text(f"  • {os.path.basename(pdf)}")
    else:
        st.error(f"❌ No PDFs found in {input_dir}")

    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        st.success("✅ API Key configured")
    else:
        st.error("❌ ANTHROPIC_API_KEY not set")
        st.markdown("Add to `.env` file")

    st.markdown("---")

    # Run button
    can_run = len(pdf_files) > 0 and api_key
    if st.button("🚀 Run Analysis", type="primary", disabled=not can_run):
        st.session_state.running = True
        st.session_state.start_time = time.time()
        st.session_state.input_dir = input_dir

    if st.button("🔄 Reset"):
        st.session_state.running = False
        st.session_state.completed = False
        st.rerun()

# Main content
if st.session_state.get('running'):
    # Progress section
    st.header("📊 Pipeline Progress")

    # Create placeholders
    progress_bar = st.progress(0)
    status_text = st.empty()

    col1, col2, col3 = st.columns(3)

    with col1:
        extraction_status = st.empty()
    with col2:
        validation_status = st.empty()
    with col3:
        completion_status = st.empty()

    # Agent communication log
    st.header("💬 Agent Communication")
    comm_log = st.empty()

    # Run pipeline with progress updates
    with st.spinner("Agents working..."):
        # Start extraction
        extraction_status.info("🔄 Agent 1: Extracting companies...")
        status_text.text("Phase 1/2: PDF Data Extraction")
        progress_bar.progress(10)

        comm_log.code("Starting PDF extraction...")

        try:
            # Run the actual pipeline
            input_dir = st.session_state.get('input_dir', 'data/input')
            result = run_pipeline(input_dir)

            extraction_status.success("✅ Agent 1: Extraction complete")
            progress_bar.progress(50)

            # Show extraction stats
            if 'extraction' in result:
                stats = result['extraction'].get('stats', {})
                comm_log.code(f"""[Agent 1] Extraction complete
  • Total companies: {stats.get('total', 0)}
  • High confidence: {stats.get('high_confidence', 0)}
  • Flagged for review: {stats.get('flagged', 0)}

[Agent 2] Starting ICP validation...""")

            validation_status.info("🔄 Agent 2: Validating ICP fit...")
            status_text.text("Phase 2/2: ICP Validation")
            progress_bar.progress(75)

            # Validation complete
            validation_status.success("✅ Agent 2: Validation complete")
            progress_bar.progress(100)
            completion_status.success("✅ Pipeline Complete!")
            status_text.text("Analysis complete!")

            # Show communication summary
            if 'validation' in result:
                stats = result['validation'].get('stats', {})
                comm_log.code(f"""[Agent 2] Validation complete
  • Companies validated: {stats.get('total', 0)}
  • Data enrichments: {stats.get('enrichments', 0)}
  • Quality resolutions: {stats.get('resolutions', 0)}

[Agent 2 → Agent 1] Shared {stats.get('enrichments', 0)} data enrichments""")

            st.session_state.completed = True
            st.session_state.running = False

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.session_state.running = False

    # Force rerun to show results
    if st.session_state.get('completed'):
        st.rerun()

elif st.session_state.get('completed'):
    # Results section
    st.header("📈 Results Summary")

    if os.path.exists('data/output/validated_companies.csv'):
        df = pd.read_csv('data/output/validated_companies.csv')

        # Metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Companies", len(df))
        with col2:
            high_fit = len(df[df['icp_score'] >= 75])
            st.metric("High Fit", high_fit, f"{high_fit/len(df)*100:.0f}%")
        with col3:
            medium_fit = len(df[(df['icp_score'] >= 50) & (df['icp_score'] < 75)])
            st.metric("Medium Fit", medium_fit, f"{medium_fit/len(df)*100:.0f}%")
        with col4:
            low_fit = len(df[df['icp_score'] < 50])
            st.metric("Low Fit", low_fit, f"{low_fit/len(df)*100:.0f}%")

        # Visualizations
        st.header("📊 ICP Fit Distribution")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Fit Level Breakdown")
            fit_counts = df['fit_level'].value_counts()
            st.bar_chart(fit_counts)

        with col2:
            st.subheader("Score Distribution")
            # Create score bins
            score_bins = pd.cut(df['icp_score'], bins=[0, 25, 50, 75, 100], labels=['0-25', '26-50', '51-75', '76-100'])
            score_counts = score_bins.value_counts().sort_index()
            st.bar_chart(score_counts)

        # Top priority accounts
        st.header("🎯 Top 10 Priority Accounts")
        top10_columns = ['company', 'industry', 'icp_score', 'fit_level', 'team_size', 'recommended_action']
        top10_columns = [col for col in top10_columns if col in df.columns]
        top10 = df.nlargest(10, 'icp_score')[top10_columns]
        st.dataframe(top10, use_container_width=True, hide_index=True)

        # Agent collaboration insights
        st.header("🤝 Agent Collaboration Insights")

        col1, col2 = st.columns(2)

        with col1:
            enrichments = len(shared_state.data.get('enrichments', []))
            st.metric("Data Enrichments", enrichments,
                     help="Times Agent 2 added missing data to Agent 1's records")

        with col2:
            resolutions = len(shared_state.data.get('resolutions', []))
            st.metric("Quality Resolutions", resolutions,
                     help="Ambiguous entries resolved by Agent 2")

        # Industry breakdown
        if 'industry' in df.columns:
            st.header("🏭 Industry Breakdown")
            industry_counts = df['industry'].value_counts().head(10)
            st.bar_chart(industry_counts)

        # Full dataset
        st.header("📋 Full Results")
        # Filter columns to display
        display_columns = ['company', 'source', 'industry', 'icp_score', 'fit_level',
                          'team_size', 'recommended_action', 'has_field_service']
        display_columns = [col for col in display_columns if col in df.columns]
        st.dataframe(df[display_columns], use_container_width=True, hide_index=True)

        # Download button
        st.header("💾 Export")
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Full CSV",
            data=csv,
            file_name="validated_companies.csv",
            mime="text/csv"
        )

        # Execution time
        if 'start_time' in st.session_state:
            elapsed = time.time() - st.session_state.start_time
            st.info(f"⏱️ Total execution time: {elapsed:.1f} seconds")

    else:
        st.error("❌ Results file not found")

else:
    # Welcome screen
    st.info("""
    👋 **Welcome!** This tool uses AI agents to:

    1. 🔍 **Extract** companies from ANY conference PDFs
    2. 🎯 **Validate** each against Ascendo.AI's ICP
    3. 📊 **Score** and rank by fit (0-100)
    4. 💡 **Generate** talking points for sales team

    **How it works:**
    - **Agent 1 (Data Collector):** Scans ALL PDFs in input folder, extracts companies with roles (speaker/attendee)
    - **Agent 2 (ICP Analyst):** Validates each company using Claude API, scores fit, generates insights
    - **Collaboration:** Agents share data and enrich each other's work

    **Flexible PDF Support:**
    - Works with ANY conference PDFs (agenda, speaker list, attendee roster, etc.)
    - Automatically detects speakers vs attendees based on content
    - Merges data from multiple PDFs intelligently

    Place your conference PDFs in the input directory and click "Run Analysis" to start.
    """)

    # Instructions
    st.header("📌 Setup Instructions")
    st.markdown("""
    1. **Place PDFs** in `data/input/` directory
       - ANY conference PDFs work (agenda, speakers, attendees, etc.)
       - Multiple PDFs are automatically merged
    2. **Set API Key** in `.env` file: `ANTHROPIC_API_KEY=your_key`
    3. **Click Run** in the sidebar

    **Supported PDF Formats:**
    - Speaker/agenda PDFs (Name → Job Title → Company)
    - Attendee lists (Company names with or without team sizes)
    - Mixed format PDFs
    """)

    # Sample output preview
    with st.expander("📊 See Sample Output"):
        st.markdown("""
        The tool generates a CSV with these columns:
        - Company name
        - Industry classification
        - ICP score (0-100)
        - Fit level (High/Medium/Low)
        - Recommended action
        - Talking points
        - Team size and contacts
        """)
