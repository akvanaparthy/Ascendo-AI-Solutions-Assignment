"""Streamlit Dashboard for Conference ICP Validator"""

import streamlit as st
import pandas as pd
from crew_setup import run_pipeline
from agents.shared_state import shared_state
from utils.event_logger import event_logger
from utils.live_logger import live_logger
from config.model_config import (
    get_available_models,
    save_model_config,
    load_model_config,
    get_model_display_name,
    DEFAULT_MODEL
)
from config.research_config import get_research_mode, set_research_mode, COST_ESTIMATES
import os
import time
import json
import threading
import warnings

# Suppress Streamlit thread warnings
warnings.filterwarnings('ignore', message='.*ScriptRunContext.*')

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

    # Model selection
    st.markdown("### 🤖 Model Selection")

    # Refresh models button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh", help="Fetch latest models from API"):
            st.session_state.force_refresh = True

    # Get available models
    force_refresh = st.session_state.get('force_refresh', False)
    available_models = get_available_models(force_refresh=force_refresh)
    if force_refresh:
        st.session_state.force_refresh = False
        st.rerun()

    # Current selected model
    current_model = load_model_config()

    # Create dropdown options
    model_options = {}
    default_index = 0

    for idx, model in enumerate(available_models):
        display_text = model['display_name']
        if model.get('recommended'):
            display_text += " ⭐"
        model_options[display_text] = model['id']

        if model['id'] == current_model:
            default_index = idx

    # Model selector
    with col1:
        selected_display = st.selectbox(
            "Select Claude Model",
            options=list(model_options.keys()),
            index=default_index,
            help="Choose which Claude model to use for validation",
            label_visibility="collapsed"
        )

    selected_model = model_options[selected_display]

    # Show model description
    for model in available_models:
        if model['id'] == selected_model:
            st.caption(model.get('description', ''))
            break

    # Show cache info
    import os as os_check
    if os_check.path.exists('config/models_cache.json'):
        try:
            with open('config/models_cache.json', 'r') as f:
                cache = json.load(f)
                cached_time = cache.get('cached_at', 'unknown')
                if cached_time != 'unknown':
                    from datetime import datetime
                    cached_dt = datetime.fromisoformat(cached_time)
                    st.caption(f"Models cached: {cached_dt.strftime('%Y-%m-%d %H:%M')}")
        except:
            pass

    # Save model selection
    if selected_model != current_model:
        save_model_config(selected_model)
        st.success(f"✅ Model updated to {get_model_display_name(selected_model)}")

    st.markdown("---")

    # Validation settings
    st.markdown("### ⚙️ Validation Settings")

    max_companies = st.number_input(
        "Max Companies to Validate",
        min_value=10,
        max_value=10000,
        value=50,
        step=10,
        help="Limit validation to first N companies (saves time and API costs)"
    )

    min_confidence = st.slider(
        "Min Confidence",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="Skip companies below this confidence score"
    )

    # Research mode selector
    st.markdown("### 🌐 Research Mode")

    current_research_mode = get_research_mode()

    research_mode = st.radio(
        "Company Research Method",
        options=["training_data", "web_search"],
        format_func=lambda x: "📚 Training Data (Fast, Cheaper)" if x == "training_data" else "🌐 Web Search (Accurate, Slower)",
        index=0 if current_research_mode == "training_data" else 1,
        help="Choose how to research companies"
    )

    # Show cost estimates
    cost_info = COST_ESTIMATES[research_mode]
    st.caption(f"**Cost:** {cost_info['per_company']} per company")
    st.caption(f"{cost_info['description']}")

    # Update research mode if changed
    if research_mode != current_research_mode:
        set_research_mode(research_mode)
        mode_name = "Web Search" if research_mode == "web_search" else "Training Data"
        st.success(f"✅ Research mode: {mode_name}")

    st.markdown("---")

    # Run button
    can_run = len(pdf_files) > 0 and api_key
    if st.button("🚀 Run Analysis", type="primary", disabled=not can_run):
        st.session_state.running = True
        st.session_state.start_time = time.time()
        st.session_state.input_dir = input_dir
        st.session_state.selected_model = selected_model
        st.session_state.max_companies = max_companies
        st.session_state.min_confidence = min_confidence

    if st.button("🔄 Reset"):
        st.session_state.running = False
        st.session_state.completed = False
        if 'pipeline_thread' in st.session_state:
            del st.session_state.pipeline_thread
        if 'pipeline_started' in st.session_state:
            del st.session_state.pipeline_started
        live_logger.clear()  # Clear logs and reset cancelled flag
        st.rerun()

    if st.session_state.get('running'):
        if st.button("⛔ Stop", type="secondary"):
            live_logger.cancel()
            st.session_state.running = False
            # Clean up thread state
            if 'pipeline_thread' in st.session_state:
                del st.session_state.pipeline_thread
            if 'pipeline_started' in st.session_state:
                del st.session_state.pipeline_started
            st.warning("⚠️ Stopping pipeline... (may take a few seconds to complete current API call)")

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

    # Live logs section
    st.header("📋 Live Activity Log")
    log_stats = st.empty()
    # Use container with fixed height for scrolling
    log_container = st.container(height=400)

    # Clear previous logs
    if 'pipeline_started' not in st.session_state:
        live_logger.clear()
        st.session_state.pipeline_started = True

    # Run pipeline in background thread if not started
    if 'pipeline_thread' not in st.session_state:
        def run_pipeline_thread():
            try:
                input_dir = st.session_state.get('input_dir', 'data/input')
                selected_model = st.session_state.get('selected_model', load_model_config())
                max_companies = st.session_state.get('max_companies', 50)
                min_confidence = st.session_state.get('min_confidence', 0.7)
                result = run_pipeline(input_dir, selected_model, min_confidence, max_companies)
                st.session_state.pipeline_result = result
                st.session_state.pipeline_error = None
            except Exception as e:
                st.session_state.pipeline_error = str(e)
                st.session_state.pipeline_result = None
            finally:
                st.session_state.pipeline_completed = True

        thread = threading.Thread(target=run_pipeline_thread, daemon=True)
        thread.start()
        st.session_state.pipeline_thread = thread
        st.session_state.pipeline_completed = False

    # Show live logs
    logs = live_logger.get_formatted_logs()
    all_logs = live_logger.get_logs()

    if logs:
        with log_container:
            st.code(logs, language="log")
        stats = live_logger.get_stats()
        log_stats.caption(f"**Events:** {stats['total_events']} | **Actual API Calls:** {stats['api_calls']} | **Duration:** {stats['duration']:.1f}s")

    # Update status indicators dynamically based on logs
    agent1_logs = [l for l in all_logs if l['agent'] == 'agent1']
    agent2_logs = [l for l in all_logs if l['agent'] == 'agent2']

    if agent1_logs:
        last_agent1 = agent1_logs[-1]
        if 'EXTRACTION_COMPLETE' in last_agent1['action'] or 'PDF_PARSED' in last_agent1['action']:
            extraction_status.success("✅ Agent 1: Extraction complete")
        else:
            extraction_status.info(f"🔄 Agent 1: {last_agent1['action'].replace('_', ' ').title()}")

    if agent2_logs:
        last_agent2 = agent2_logs[-1]
        if 'VALIDATING_COMPANY' in last_agent2['action']:
            validation_status.info(f"🔄 Agent 2: {last_agent2['details'].split(':')[0]}")
        elif 'START_VALIDATION' in last_agent2['action']:
            validation_status.info("🔄 Agent 2: Starting validation...")
        else:
            validation_status.info(f"🔄 Agent 2: {last_agent2['action'].replace('_', ' ').title()}")
    else:
        validation_status.info("⏳ Agent 2: Waiting...")

    # Update status text
    if agent2_logs:
        status_text.text("Phase 2/2: ICP Validation")
        progress = min(50 + len(agent2_logs), 95)
        progress_bar.progress(progress)
    elif agent1_logs:
        status_text.text("Phase 1/2: PDF Data Extraction")
        progress = min(10 + len(agent1_logs) * 5, 50)
        progress_bar.progress(progress)
    else:
        status_text.text("Starting...")
        progress_bar.progress(5)

    # Check if pipeline completed
    if st.session_state.get('pipeline_completed'):
        if st.session_state.get('pipeline_error'):
            st.error(f"❌ Error: {st.session_state.pipeline_error}")
        else:
            extraction_status.success("✅ Agent 1: Extraction complete")
            validation_status.success("✅ Agent 2: Validation complete")
            completion_status.success("✅ Pipeline Complete!")
            progress_bar.progress(100)
            status_text.text("Analysis complete!")

        st.session_state.completed = True
        st.session_state.running = False
        st.session_state.pop('pipeline_thread', None)
        st.session_state.pop('pipeline_started', None)
        st.rerun()
    else:
        # Auto-refresh every 0.5 seconds for smoother updates
        time.sleep(0.5)
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
        st.dataframe(top10, width='stretch', hide_index=True)

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
        st.dataframe(df[display_columns], width='stretch', hide_index=True)

        # Download button
        st.header("💾 Export")
        col1, col2 = st.columns(2)

        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download Results CSV",
                data=csv,
                file_name="validated_companies.csv",
                mime="text/csv"
            )

        with col2:
            # Save logs and provide download
            log_file, json_file = live_logger.save_to_file()
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            st.download_button(
                label="📥 Download Session Logs",
                data=log_content,
                file_name=os.path.basename(log_file),
                mime="text/plain"
            )

        # Activity log viewer
        st.header("📋 Session Activity Log")
        with st.expander("View Full Log", expanded=False):
            stats = live_logger.get_stats()
            st.write(f"**Total Events:** {stats['total_events']} | "
                    f"**API Calls:** {stats['api_calls']} | "
                    f"**Errors:** {stats['errors']} | "
                    f"**Duration:** {stats['duration']:.1f}s")
            st.code(live_logger.get_formatted_logs(), language="log")

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
