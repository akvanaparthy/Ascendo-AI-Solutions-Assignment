import sys
import os
import signal
import glob
import argparse
import pandas as pd

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from crew_setup import run_pipeline
from config.model_config import load_model_config, get_model_display_name
from config.research_config import set_research_mode, get_research_mode
from utils.live_logger import live_logger
from utils.event_logger import event_logger

def signal_handler(sig, frame):
    print("\n\n⚠️ Interrupt received. Stopping...")
    live_logger.cancel()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def main():
    parser = argparse.ArgumentParser(description='Conference ICP Validator')
    parser.add_argument('--max-companies', type=int, default=None)
    parser.add_argument('--min-confidence', type=float, default=0.7)
    parser.add_argument('--research-mode', type=str,
                       choices=['training_data', 'web_search_anthropic', 'web_search_brave'],
                       default=None)
    args = parser.parse_args()

    if args.research_mode:
        set_research_mode(args.research_mode)

    input_dir = 'data/input'
    pdf_files = glob.glob(os.path.join(input_dir, '*.pdf'))

    if not pdf_files:
        print("[X] No PDFs in data/input/")
        sys.exit(1)

    print(f"[OK] Found {len(pdf_files)} PDF(s)")
    for pdf in pdf_files:
        print(f"  - {os.path.basename(pdf)}")

    current_model = load_model_config()
    print(f"[OK] Model: {get_model_display_name(current_model)}")

    mode_names = {
        "training_data": "Training Data",
        "web_search_anthropic": "Anthropic Web Search",
        "web_search_brave": "Brave Search API"
    }
    print(f"[OK] Mode: {mode_names.get(get_research_mode(), get_research_mode())}")

    if args.max_companies:
        print(f"[OK] Limit: {args.max_companies} companies")
    print(f"[OK] Min confidence: {args.min_confidence}")
    print()

    result = run_pipeline(input_dir, current_model, args.min_confidence, args.max_companies)

    print("\n" + "=" * 60)
    print("📈 SUMMARY")
    print("=" * 60)

    if os.path.exists('data/output/validated_companies.csv'):
        df = pd.read_csv('data/output/validated_companies.csv')
        print(f"\n📊 Statistics:")
        print(f"  • Total: {len(df)}")
        print(f"  • High (75+): {len(df[df['icp_score'] >= 75])}")
        print(f"  • Medium (50-74): {len(df[(df['icp_score'] >= 50) & (df['icp_score'] < 75)])}")
        print(f"  • Low (<50): {len(df[df['icp_score'] < 50])}")

        print(f"\n🎯 Top 10:")
        print("-" * 60)
        top10 = df.nlargest(10, 'icp_score')[['company', 'icp_score', 'fit_level', 'recommended_action']]
        print(top10.to_string(index=False))

        print(f"\n💬 Agent Summary:")
        event_logger.print_summary()

        if 'industry' in df.columns:
            print(f"\n🏭 Industries:")
            for industry, count in df['industry'].value_counts().head(10).items():
                print(f"  • {industry}: {count}")

        print(f"\n✅ Results: data/output/validated_companies.csv")
    else:
        print("  ❌ No results generated")

if __name__ == "__main__":
    main()
