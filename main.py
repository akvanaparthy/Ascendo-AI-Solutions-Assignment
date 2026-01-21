"""Main CLI entry point for Conference ICP Validator"""

import sys
import os
import signal

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from crew_setup import run_pipeline
from utils.event_logger import event_logger
from agents.shared_state import shared_state
from config.model_config import load_model_config, get_model_display_name
from config.research_config import set_research_mode, get_research_mode
from utils.live_logger import live_logger
import pandas as pd
import argparse

# Signal handler for Ctrl+C
def signal_handler(sig, frame):
    print("\n\n⚠️ Interrupt received (Ctrl+C). Stopping gracefully...")
    live_logger.cancel()
    print("⏳ Waiting for current operation to complete...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def main():
    """Main execution function"""

    parser = argparse.ArgumentParser(description='Conference ICP Validator')
    parser.add_argument('--max-companies', type=int, default=None,
                       help='Limit validation to first N companies (default: all)')
    parser.add_argument('--min-confidence', type=float, default=0.7,
                       help='Skip companies below this confidence (default: 0.7)')
    parser.add_argument('--research-mode', type=str,
                       choices=['training_data', 'web_search_anthropic', 'web_search_brave'],
                       default=None,
                       help='Research mode: training_data | web_search_anthropic | web_search_brave')
    args = parser.parse_args()

    # Set research mode if specified
    if args.research_mode:
        set_research_mode(args.research_mode)

    # Check for input PDFs
    input_dir = 'data/input'
    import glob
    pdf_files = glob.glob(os.path.join(input_dir, '*.pdf'))

    if not pdf_files:
        print("[X] No PDF files found in data/input/")
        print("\nPlease place conference PDFs in data/input/ directory")
        print("   Supported: Any conference PDFs (agenda, speakers, attendees, etc.)")
        print("\n   Examples:")
        print("   - conference_agenda.pdf")
        print("   - speaker_list.pdf")
        print("   - attendee_roster.pdf")
        sys.exit(1)

    print(f"[OK] Found {len(pdf_files)} PDF file(s) to process:")
    for pdf in pdf_files:
        print(f"  - {os.path.basename(pdf)}")

    # Show selected model
    current_model = load_model_config()
    print(f"[OK] Using model: {get_model_display_name(current_model)}")

    # Show settings
    research_mode = get_research_mode()
    mode_names = {
        "training_data": "Training Data (fast)",
        "web_search_anthropic": "Anthropic Web Search (live data)",
        "web_search_brave": "Brave Search MCP (live data, free)"
    }
    print(f"[OK] Research mode: {mode_names.get(research_mode, research_mode)}")

    if args.max_companies:
        print(f"[OK] Limit: {args.max_companies} companies")
    print(f"[OK] Min confidence: {args.min_confidence}")
    print()

    # Run the pipeline
    result = run_pipeline(input_dir, current_model, args.min_confidence, args.max_companies)

    # Generate summary report
    print("\n" + "=" * 60)
    print("📈 SUMMARY REPORT")
    print("=" * 60)

    if os.path.exists('data/output/validated_companies.csv'):
        df = pd.read_csv('data/output/validated_companies.csv')

        print(f"\n📊 Overall Statistics:")
        print(f"  • Total Companies: {len(df)}")
        print(f"  • High Fit (75-100): {len(df[df['icp_score'] >= 75])}")
        print(f"  • Medium Fit (50-74): {len(df[(df['icp_score'] >= 50) & (df['icp_score'] < 75)])}")
        print(f"  • Low Fit (0-49): {len(df[df['icp_score'] < 50])}")

        print(f"\n🎯 Top 10 Priority Accounts:")
        print("-" * 60)
        top10 = df.nlargest(10, 'icp_score')[['company', 'icp_score', 'fit_level', 'recommended_action']]
        print(top10.to_string(index=False))

        # Agent communication summary
        print(f"\n💬 Agent Communication Summary:")
        print("-" * 60)
        event_logger.print_summary()

        # Industry breakdown
        if 'industry' in df.columns:
            print(f"\n🏭 Industry Breakdown:")
            industry_counts = df['industry'].value_counts().head(10)
            for industry, count in industry_counts.items():
                print(f"  • {industry}: {count} companies")

        print(f"\n✅ Full results available at: data/output/validated_companies.csv")

    else:
        print("  ❌ No results file generated")

if __name__ == "__main__":
    main()
