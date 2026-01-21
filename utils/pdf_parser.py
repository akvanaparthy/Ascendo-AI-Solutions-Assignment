"""PDF parsing utilities for conference documents"""

import fitz  # PyMuPDF
import re
from typing import List, Dict, Optional

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from PDF"""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def parse_speaker_pdf(pdf_path: str) -> List[Dict]:
    """
    Parse speaker lineup PDF.
    Pattern: Name → Job Title → Company Name
    """
    text = extract_text_from_pdf(pdf_path)
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    companies = []
    job_title_patterns = [
        r'\b(VP|Vice President|SVP|Director|Manager|Head|Chief|CEO|COO|CTO|President)\b',
    ]

    for i, line in enumerate(lines):
        # Check if line contains a job title
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in job_title_patterns):
            # Next line is likely the company
            if i + 1 < len(lines):
                company_name = lines[i + 1]
                contact_name = lines[i - 1] if i > 0 else None

                # Skip if looks like header/footer
                if len(company_name) > 3 and not company_name.isdigit():
                    companies.append({
                        'company': clean_company_name(company_name),
                        'source': 'speaker_lineup',
                        'contact_name': contact_name,
                        'contact_title': line,
                        'team_size': None,
                        'confidence': 0.8,
                        'flags': []
                    })

    return deduplicate_companies(companies)

def parse_attendee_pdf(pdf_path: str) -> List[Dict]:
    """
    Parse attendee list PDF.
    Pattern: Company Name (Team of X)
    """
    text = extract_text_from_pdf(pdf_path)
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    companies = []
    team_pattern = r'(.+?)\s*\(Team of (\d+)\)'

    for line in lines:
        # Check for team size pattern
        match = re.search(team_pattern, line, re.IGNORECASE)
        if match:
            company_name = match.group(1)
            team_size = int(match.group(2))

            companies.append({
                'company': clean_company_name(company_name),
                'source': 'attendee_list',
                'contact_name': None,
                'contact_title': None,
                'team_size': team_size,
                'confidence': 0.9,
                'flags': []
            })
        else:
            # Might be a company without team size annotation
            if len(line) > 3 and not line.isdigit() and not is_header_footer(line):
                companies.append({
                    'company': clean_company_name(line),
                    'source': 'attendee_list',
                    'contact_name': None,
                    'contact_title': None,
                    'team_size': 1,  # Default to 1 if not specified
                    'confidence': 0.6,
                    'flags': ['no_team_size_annotation']
                })

    return deduplicate_companies(companies)

def clean_company_name(name: str) -> str:
    """Clean and normalize company name"""
    # Remove extra whitespace
    name = ' '.join(name.split())

    # Remove common suffixes for matching
    suffixes = [', Inc.', ' Inc.', ', LLC', ' LLC', ' Corp.', ' Corporation', ' Ltd.']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]

    return name.strip()

def is_header_footer(text: str) -> bool:
    """Check if text is likely a header or footer"""
    header_footer_keywords = [
        'page', 'conference', 'agenda', 'speaker', 'attendee',
        'field service', 'schedule', 'workshop', 'keynote'
    ]
    return any(keyword in text.lower() for keyword in header_footer_keywords) and len(text) < 50

def deduplicate_companies(companies: List[Dict]) -> List[Dict]:
    """Remove duplicate companies"""
    seen = {}
    for company in companies:
        name = company['company'].lower()
        if name not in seen:
            seen[name] = company
        else:
            # Merge data, prefer higher confidence
            if company['confidence'] > seen[name]['confidence']:
                seen[name] = company

    return list(seen.values())

def merge_company_lists(speaker_companies: List[Dict], attendee_companies: List[Dict]) -> List[Dict]:
    """Merge companies from both sources, preferring speaker data for contacts"""
    merged = {}

    # Add all companies
    for company in speaker_companies + attendee_companies:
        name = company['company'].lower()

        if name not in merged:
            merged[name] = company
        else:
            # Merge: prefer speaker data for contacts, attendee data for team size
            existing = merged[name]

            # Update team size if missing
            if existing['team_size'] is None and company['team_size'] is not None:
                existing['team_size'] = company['team_size']

            # Update contacts if missing
            if existing['contact_name'] is None and company['contact_name'] is not None:
                existing['contact_name'] = company['contact_name']
                existing['contact_title'] = company['contact_title']

            # Update source
            if existing['source'] != company['source']:
                existing['source'] = 'both'

            # Take higher confidence
            existing['confidence'] = max(existing['confidence'], company['confidence'])

    return list(merged.values())
