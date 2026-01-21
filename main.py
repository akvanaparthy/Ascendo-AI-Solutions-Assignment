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
    speaker_pdf = 'data/input/fieldservicenextwest2026pre.pdf'
    attendee_pdf = 'data/input/fieldservicenextwest2026attendees.pdf'

    missing_files = []
    if not os.path.exists(speaker_pdf):
        missing_files.append(speaker_pdf)
    if not os.path.exists(attendee_pdf):
        missing_files.append(attendee_pdf)

    if missing_files:
        print("❌ Missing input PDF files:")
        for file in missing_files:
            print(f"  • {file}")
        print("\n📌 Please place the conference PDFs in data/input/ directory")
        print("   or update the file paths in main.py")
        sys.exit(1)

    # Run the pipeline
    result = run_pipeline(speaker_pdf, attendee_pdf)

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
