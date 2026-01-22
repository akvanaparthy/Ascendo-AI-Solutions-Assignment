import streamlit as st
import pandas as pd
import os
import sys
import time
import json
import threading
import warnings
import glob

from crew_setup import run_pipeline
from agents.shared_state import shared_state
from utils.live_logger import live_logger
from config.model_config import (
    get_available_models, save_model_config, load_model_config,
    get_model_display_name, DEFAULT_MODEL
)
from config.research_config import get_research_mode, set_research_mode, COST_ESTIMATES

warnings.filterwarnings('ignore', message='.*ScriptRunContext.*')

st.set_page_config(page_title="Conference ICP Validator", page_icon="🎯", layout="wide")
st.title("🎯 Field Service Conference ICP Validator")
st.markdown("**AI-Powered Lead Qualification for Ascendo.AI**")

if 'max_companies' not in st.session_state:
    st.session_state.max_companies = 50
if 'min_confidence' not in st.session_state:
    st.session_state.min_confidence = 0.7
if 'running' not in st.session_state:
    st.session_state.running = False
if 'completed' not in st.session_state:
    st.session_state.completed = False
if 'thread_started' not in st.session_state:
    st.session_state.thread_started = False

with st.sidebar:
    st.header("⚙️ Configuration")

    st.markdown("### 📄 Input PDFs")
    input_dir = st.text_input("Input Directory", value="data/input")
    pdf_files = glob.glob(os.path.join(input_dir, '*.pdf')) if os.path.exists(input_dir) else []

    if pdf_files:
        st.success(f"✅ Found {len(pdf_files)} PDF(s)")
        for pdf in pdf_files:
            st.text(f"  • {os.path.basename(pdf)}")
    else:
        st.error(f"❌ No PDFs found in {input_dir}")

    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        st.success("✅ API Key configured")
    else:
        st.error("❌ ANTHROPIC_API_KEY not set")

    st.markdown("---")
    st.markdown("### 🤖 Model Selection")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄", help="Refresh models"):
            st.session_state.force_refresh = True

    available_models = get_available_models(force_refresh=st.session_state.get('force_refresh', False))
    if st.session_state.get('force_refresh'):
        st.session_state.force_refresh = False
        st.rerun()

    current_model = load_model_config()
    model_options = {}
    default_index = 0

    for idx, model in enumerate(available_models):
        display_text = model['display_name']
        if model.get('recommended'):
            display_text += " ⭐"
        model_options[display_text] = model['id']
        if model['id'] == current_model:
            default_index = idx

    with col1:
        selected_display = st.selectbox(
            "Model", options=list(model_options.keys()), index=default_index,
            label_visibility="collapsed"
        )

    selected_model = model_options[selected_display]

    for model in available_models:
        if model['id'] == selected_model:
            st.caption(model.get('description', ''))
            break

    if selected_model != current_model:
        save_model_config(selected_model)
        st.success(f"✅ Model: {get_model_display_name(selected_model)}")

    st.markdown("---")
    st.markdown("### ⚙️ Validation Settings")

    max_companies = st.number_input(
        "Max Companies", min_value=1, max_value=10000,
        value=st.session_state.max_companies, step=10,
        key="max_companies_widget"
    )
    st.session_state.max_companies = max_companies

    min_confidence = st.slider(
        "Min Confidence", min_value=0.0, max_value=1.0,
        value=st.session_state.min_confidence, step=0.1,
        key="min_confidence_widget"
    )
    st.session_state.min_confidence = min_confidence

    st.markdown("### 🌐 Research Mode")
    current_research_mode = get_research_mode()

    mode_display = {
        "training_data": "📚 Training Data",
        "web_search_anthropic": "🌐 Anthropic Web Search",
        "web_search_brave": "🔍 Brave Search API"
    }

    research_mode = st.radio(
        "Research Method",
        options=["training_data", "web_search_anthropic", "web_search_brave"],
        format_func=lambda x: mode_display[x],
        index=["training_data", "web_search_anthropic", "web_search_brave"].index(current_research_mode)
    )

    cost_info = COST_ESTIMATES[research_mode]
    st.caption(f"**Cost (50):** {cost_info['total_50']}")

    if research_mode == "web_search_brave":
        if os.getenv('BRAVE_API_KEY'):
            st.success("✅ Brave API configured")
        else:
            st.warning("⚠️ BRAVE_API_KEY not set")

    if research_mode != current_research_mode:
        set_research_mode(research_mode)

    st.markdown("---")

    can_run = len(pdf_files) > 0 and api_key and not st.session_state.running

    if st.button("🚀 Run Analysis", type="primary", disabled=not can_run):
        live_logger.clear()
        st.session_state.running = True
        st.session_state.completed = False
        st.session_state.thread_started = False
        st.session_state.start_time = time.time()
        st.session_state.run_input_dir = input_dir
        st.session_state.run_model = selected_model
        st.session_state.run_max_companies = max_companies
        st.session_state.run_min_confidence = min_confidence

        print(f"\n[APP] Run Analysis clicked")
        print(f"[APP] max_companies={max_companies}")
        print(f"[APP] min_confidence={min_confidence}")
        print(f"[APP] model={selected_model}")
        sys.stdout.flush()
        st.rerun()

    if st.button("🔄 Reset"):
        live_logger.clear()
        st.session_state.running = False
        st.session_state.completed = False
        st.session_state.thread_started = False
        st.rerun()

    if st.session_state.running:
        if st.button("⛔ Stop", type="secondary"):
            live_logger.cancel()
            st.session_state.running = False
            st.session_state.completed = True
            st.warning("⚠️ Stopping...")

if st.session_state.running:
    st.header("📊 Pipeline Progress")
    st.caption(f"Settings: {st.session_state.get('run_max_companies', 50)} companies | {get_research_mode()} mode")

    progress_bar = st.progress(0)
    status_text = st.empty()

    col1, col2, col3 = st.columns(3)
    with col1:
        extraction_status = st.empty()
        extraction_status.info("⏳ Agent 1: Waiting...")
    with col2:
        validation_status = st.empty()
        validation_status.info("⏳ Agent 2: Waiting...")
    with col3:
        completion_status = st.empty()
        completion_status.info("⏳ Pipeline: Running...")

    st.header("📋 Live Activity Log")
    log_stats = st.empty()
    log_container = st.container(height=400)

    if not st.session_state.thread_started:
        st.session_state.thread_started = True

        run_input_dir = st.session_state.get('run_input_dir', 'data/input')
        run_model = st.session_state.get('run_model', None)
        run_min_confidence = st.session_state.get('run_min_confidence', 0.7)
        run_max_companies = st.session_state.get('run_max_companies', 50)

        def run_pipeline_thread(input_dir, model, min_conf, max_comp):
            try:
                print(f"\n[THREAD] Starting pipeline thread")
                print(f"[THREAD] input_dir={input_dir}")
                print(f"[THREAD] model={model}")
                print(f"[THREAD] min_confidence={min_conf}")
                print(f"[THREAD] max_companies={max_comp}")
                sys.stdout.flush()

                result = run_pipeline(input_dir, model, min_conf, max_comp)
                live_logger.set_completed(result=result)
                print(f"\n[THREAD] Pipeline completed successfully")
                sys.stdout.flush()
            except Exception as e:
                print(f"\n[THREAD] Pipeline error: {e}")
                sys.stdout.flush()
                live_logger.set_completed(error=str(e))

        thread = threading.Thread(
            target=run_pipeline_thread,
            args=(run_input_dir, run_model, run_min_confidence, run_max_companies),
            daemon=True
        )
        thread.start()

    logs = live_logger.get_formatted_logs()
    all_logs = live_logger.get_logs()
    stats = live_logger.get_stats()

    with log_container:
        if logs:
            st.code(logs, language="log")
        else:
            st.text("Waiting for logs...")

    log_stats.caption(f"**Events:** {stats['total_events']} | **API Calls:** {stats['api_calls']} | **Duration:** {stats['duration']:.1f}s")

    agent1_logs = [l for l in all_logs if l['agent'] == 'agent1']
    agent2_logs = [l for l in all_logs if l['agent'] == 'agent2']

    if agent1_logs:
        last = agent1_logs[-1]
        if 'COMPLETE' in last['action'] or 'Complete' in last['action']:
            extraction_status.success("✅ Agent 1: Complete")
        else:
            extraction_status.info(f"🔄 Agent 1: {last['action']}")

    if agent2_logs:
        last = agent2_logs[-1]
        if 'VALIDATING' in last['action']:
            validation_status.info(f"🔄 {last['details'].split(':')[0] if ':' in last['details'] else last['action']}")
        elif 'COMPLETE' in last['action'] or 'Complete' in last['action']:
            validation_status.success("✅ Agent 2: Complete")
        else:
            validation_status.info(f"🔄 Agent 2: {last['action']}")

    if agent2_logs:
        status_text.text("Phase 2/2: ICP Validation")
        progress_bar.progress(min(50 + len(agent2_logs), 95))
    elif agent1_logs:
        status_text.text("Phase 1/2: PDF Extraction")
        progress_bar.progress(min(10 + len(agent1_logs) * 5, 50))
    else:
        status_text.text("Starting...")
        progress_bar.progress(5)

    if live_logger.is_completed():
        error = live_logger.get_error()
        if error:
            st.error(f"❌ Error: {error}")
            completion_status.error("❌ Pipeline: Error")
        else:
            extraction_status.success("✅ Agent 1: Complete")
            validation_status.success("✅ Agent 2: Complete")
            completion_status.success("✅ Pipeline: Done!")
            progress_bar.progress(100)
            status_text.text("Analysis complete!")

        st.session_state.completed = True
        st.session_state.running = False
        st.session_state.thread_started = False
        time.sleep(0.5)
        st.rerun()
    else:
        time.sleep(0.5)
        st.rerun()

elif st.session_state.completed:
    st.header("📈 Results Summary")

    if os.path.exists('data/output/validated_companies.csv'):
        df = pd.read_csv('data/output/validated_companies.csv')

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", len(df))
        with col2:
            high = len(df[df['icp_score'] >= 75])
            st.metric("High Fit", high, f"{high/len(df)*100:.0f}%")
        with col3:
            med = len(df[(df['icp_score'] >= 50) & (df['icp_score'] < 75)])
            st.metric("Medium", med)
        with col4:
            low = len(df[df['icp_score'] < 50])
            st.metric("Low", low)

        st.header("📊 Distribution")
        col1, col2 = st.columns(2)
        with col1:
            st.bar_chart(df['fit_level'].value_counts())
        with col2:
            bins = pd.cut(df['icp_score'], bins=[0, 25, 50, 75, 100], labels=['0-25', '26-50', '51-75', '76-100'])
            st.bar_chart(bins.value_counts().sort_index())

        st.header("🎯 Top 10 Priority")
        cols = ['company', 'industry', 'icp_score', 'fit_level', 'recommended_action']
        cols = [c for c in cols if c in df.columns]
        st.dataframe(df.nlargest(10, 'icp_score')[cols], hide_index=True)

        if 'industry' in df.columns:
            st.header("🏭 Industries")
            st.bar_chart(df['industry'].value_counts().head(10))

        st.header("📋 Full Results")
        display_cols = ['company', 'source', 'industry', 'icp_score', 'fit_level', 'recommended_action']
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[display_cols], hide_index=True)

        st.header("💾 Export")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 Download CSV", df.to_csv(index=False), "validated_companies.csv", "text/csv")
        with col2:
            log_file, _ = live_logger.save_to_file()
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    st.download_button("📥 Download Logs", f.read(), os.path.basename(log_file), "text/plain")

        if 'start_time' in st.session_state:
            st.info(f"⏱️ Time: {time.time() - st.session_state.start_time:.1f}s")
    else:
        st.error("❌ Results not found")

else:
    st.info("""
    👋 **Welcome!** This tool uses AI agents to:
    1. 🔍 **Extract** companies from conference PDFs
    2. 🎯 **Validate** against Ascendo.AI's ICP
    3. 📊 **Score** and rank (0-100)
    4. 💡 **Generate** talking points

    Place PDFs in `data/input/` and click **Run Analysis**.
    """)
