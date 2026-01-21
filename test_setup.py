"""Test setup and verify all components work"""

import sys
import os

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    try:
        from crewai import Crew, Agent, Task, Process
        print("[OK] CrewAI imports")
    except Exception as e:
        print(f"[FAIL] CrewAI import: {e}")
        return False

    try:
        from anthropic import Anthropic
        print("[OK] Anthropic import")
    except Exception as e:
        print(f"[FAIL] Anthropic import: {e}")
        return False

    try:
        import fitz  # PyMuPDF
        print("[OK] PyMuPDF import")
    except Exception as e:
        print(f"[FAIL] PyMuPDF import: {e}")
        return False

    try:
        import pandas as pd
        print("[OK] Pandas import")
    except Exception as e:
        print(f"[FAIL] Pandas import: {e}")
        return False

    try:
        import streamlit as st
        print("[OK] Streamlit import")
    except Exception as e:
        print(f"[FAIL] Streamlit import: {e}")
        return False

    return True

def test_project_structure():
    """Test project structure"""
    print("\nTesting project structure...")
    required_dirs = ['agents', 'config', 'utils', 'data/input', 'data/output']
    all_exist = True

    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"[OK] {dir_path}/ exists")
        else:
            print(f"[FAIL] {dir_path}/ missing")
            all_exist = False

    return all_exist

def test_env_file():
    """Test .env file"""
    print("\nTesting environment...")
    if os.path.exists('.env'):
        print("[OK] .env file exists")
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            print("[OK] ANTHROPIC_API_KEY is set")
            return True
        else:
            print("[WARN] ANTHROPIC_API_KEY not found in .env")
            print("       Add: ANTHROPIC_API_KEY=your_key_here")
            return False
    else:
        print("[WARN] .env file not found")
        print("       Create .env file with: ANTHROPIC_API_KEY=your_key_here")
        return False

def test_pdf_files():
    """Test for PDF files"""
    print("\nTesting input PDFs...")
    speaker_pdf = 'data/input/fieldservicenextwest2026pre.pdf'
    attendee_pdf = 'data/input/fieldservicenextwest2026attendees.pdf'

    pdfs_exist = True
    if os.path.exists(speaker_pdf):
        print(f"[OK] {speaker_pdf} exists")
    else:
        print(f"[WARN] {speaker_pdf} not found")
        pdfs_exist = False

    if os.path.exists(attendee_pdf):
        print(f"[OK] {attendee_pdf} exists")
    else:
        print(f"[WARN] {attendee_pdf} not found")
        pdfs_exist = False

    if not pdfs_exist:
        print("       Place conference PDFs in data/input/")

    return pdfs_exist

def test_module_imports():
    """Test custom module imports"""
    print("\nTesting custom modules...")
    try:
        from agents.extractor_agent import create_extractor_agent
        from agents.validator_agent import create_validator_agent
        from agents.shared_state import shared_state
        from utils.event_logger import event_logger
        from config.icp_criteria import ICP_CRITERIA
        print("[OK] All custom modules import")
        return True
    except Exception as e:
        print(f"[FAIL] Module import: {e}")
        return False

def main():
    print("=" * 60)
    print("SETUP VERIFICATION TEST")
    print("=" * 60)

    results = {
        'imports': test_imports(),
        'structure': test_project_structure(),
        'env': test_env_file(),
        'pdfs': test_pdf_files(),
        'modules': test_module_imports()
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = all(results.values())

    for test_name, passed in results.items():
        status = "PASS" if passed else "NEEDS ATTENTION"
        print(f"{test_name.upper()}: [{status}]")

    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED - Ready to run!")
        print("\nRun the application:")
        print("  CLI: python main.py")
        print("  Dashboard: streamlit run app.py")
    else:
        print("[ATTENTION] SOME TESTS FAILED - Please fix issues above")
        print("\nCommon fixes:")
        print("  1. Create .env file: copy .env.example to .env")
        print("  2. Add API key: ANTHROPIC_API_KEY=your_key")
        print("  3. Place PDFs in data/input/")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
