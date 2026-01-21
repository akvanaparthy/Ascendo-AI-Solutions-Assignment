"""Main CLI entry point for Conference ICP Validator"""

from crew_setup import run_pipeline
from utils.event_logger import event_logger
from agents.shared_state import shared_state
import pandas as pd
import os
import sys

def main():
    """Main execution function"""

    # Check for input PDFs
    input_dir = 'data/input'
    import glob
    pdf_files = glob.glob(os.path.join(input_dir, '*.pdf'))

    if not pdf_files:
        print("❌ No PDF files found in data/input/")
        print("\n📌 Please place conference PDFs in data/input/ directory")
        print("   Supported: Any conference PDFs (agenda, speakers, attendees, etc.)")
        print("\n   Examples:")
        print("   - conference_agenda.pdf")
        print("   - speaker_list.pdf")
        print("   - attendee_roster.pdf")
        sys.exit(1)

    print(f"✓ Found {len(pdf_files)} PDF file(s) to process:")
    for pdf in pdf_files:
        print(f"  • {os.path.basename(pdf)}")
    print()

    # Run the pipeline
    result = run_pipeline(input_dir)

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
