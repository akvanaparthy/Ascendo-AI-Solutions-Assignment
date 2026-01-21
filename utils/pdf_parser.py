"""PDF parsing utilities for conference documents - Flexible for any PDF format"""

import fitz  # PyMuPDF
import re
import os
from typing import List, Dict, Optional

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from PDF"""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def parse_generic_pdf(pdf_path: str) -> List[Dict]:
    """
    Parse any conference PDF - looks for companies with flexible patterns.
    Works for agenda, speaker list, attendee list, etc.
    """
    text = extract_text_from_pdf(pdf_path)
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    pdf_filename = os.path.basename(pdf_path)
    companies = []

    # Pattern 1: Job title followed by company (common in agendas/speaker lists)
    job_title_patterns = [
        r'\b(VP|Vice President|SVP|EVP|Director|Manager|Head|Chief|CEO|COO|CTO|CFO|President|Chairman|Founder)\b',
    ]

    for i, line in enumerate(lines):
        # Skip obvious headers/footers
        if is_header_footer(line):
            continue

        # Pattern 1: Job title → Company pattern
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in job_title_patterns):
            # Next line likely contains company
            if i + 1 < len(lines):
                potential_company = lines[i + 1]
                if is_valid_company_name(potential_company):
                    contact_name = lines[i - 1] if i > 0 and is_person_name(lines[i - 1]) else None

                    companies.append({
                        'company': clean_company_name(potential_company),
                        'source_pdf': pdf_filename,
                        'role': 'speaker',  # Has job title = likely speaker
                        'contact_name': contact_name,
                        'contact_title': line,
                        'team_size': None,
                        'confidence': 0.85,
                        'flags': []
                    })

        # Pattern 2: Company with team size (common in attendee lists)
        team_match = re.search(r'(.+?)\s*\(Team of (\d+)\)', line, re.IGNORECASE)
        if team_match:
            company_name = team_match.group(1)
            team_size = int(team_match.group(2))

            if is_valid_company_name(company_name):
                companies.append({
                    'company': clean_company_name(company_name),
                    'source_pdf': pdf_filename,
                    'role': 'attendee',
                    'contact_name': None,
                    'contact_title': None,
                    'team_size': team_size,
                    'confidence': 0.95,
                    'flags': []
                })

        # Pattern 3: Standalone company names (less confident)
        elif is_valid_company_name(line) and len(line) > 5:
            # Check if this might be a company (not already captured)
            if not any(c['company'].lower() == clean_company_name(line).lower() for c in companies):
                companies.append({
                    'company': clean_company_name(line),
                    'source_pdf': pdf_filename,
                    'role': 'attendee',  # Default to attendee if unclear
                    'contact_name': None,
                    'contact_title': None,
                    'team_size': 1,
                    'confidence': 0.6,
                    'flags': ['extracted_standalone']
                })

    return deduplicate_companies(companies)

def is_valid_company_name(text: str) -> bool:
    """Check if text looks like a valid company name"""
    if not text or len(text) < 3:
        return False

    # Skip if all numbers or special chars
    if text.isdigit() or re.match(r'^[\W_]+$', text):
        return False

    # Skip common non-company words
    skip_words = [
        'page', 'agenda', 'schedule', 'conference', 'workshop',
        'keynote', 'session', 'break', 'lunch', 'dinner', 'welcome',
        'opening', 'closing', 'panel', 'discussion', 'q&a', 'networking'
    ]
    if text.lower() in skip_words:
        return False

    # Skip if it's just a job title
    if re.match(r'^(VP|Director|Manager|CEO|COO|CTO|President|Chief)$', text, re.IGNORECASE):
        return False

    return True

def is_person_name(text: str) -> bool:
    """Heuristic to check if text looks like a person's name"""
    if not text or len(text) < 3:
        return False

    # Check if it has 2-4 words (typical for names)
    words = text.split()
    if len(words) < 2 or len(words) > 4:
        return False

    # Check if words start with capital letters
    if not all(word[0].isupper() for word in words if word):
        return False

    # Check if it contains common name suffixes
    name_suffixes = ['Jr.', 'Sr.', 'III', 'IV', 'Ph.D', 'MD']
    has_suffix = any(suffix in text for suffix in name_suffixes)

    return len(words) >= 2 or has_suffix

def clean_company_name(name: str) -> str:
    """Clean and normalize company name"""
    # Remove extra whitespace
    name = ' '.join(name.split())

    # Remove common suffixes for matching
    suffixes = [', Inc.', ' Inc.', ', LLC', ' LLC', ' Corp.', ' Corporation', ' Ltd.', ' Limited']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]

    return name.strip()

def is_header_footer(text: str) -> bool:
    """Check if text is likely a header or footer"""
    if len(text) > 100:  # Too long to be header/footer
        return False

    header_footer_keywords = [
        'page', 'agenda', 'schedule', 'day 1', 'day 2', 'day 3',
        'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
        'am ', 'pm ', 'copyright', '©', 'all rights reserved'
    ]

    text_lower = text.lower()

    # Check for page numbers
    if re.match(r'^\d+$', text) or re.match(r'^page \d+', text_lower):
        return True

    # Check for time stamps
    if re.match(r'^\d{1,2}:\d{2}', text):
        return True

    return any(keyword in text_lower for keyword in header_footer_keywords) and len(text) < 50

def deduplicate_companies(companies: List[Dict]) -> List[Dict]:
    """Remove duplicate companies within same PDF"""
    seen = {}
    for company in companies:
        name = company['company'].lower()
        if name not in seen:
            seen[name] = company
        else:
            # Keep higher confidence entry
            if company['confidence'] > seen[name]['confidence']:
                seen[name] = company

    return list(seen.values())

def merge_all_companies(all_companies: List[Dict]) -> List[Dict]:
    """
    Merge companies from multiple PDFs.
    If same company appears in multiple PDFs, combine the information.
    """
    merged = {}

    for company in all_companies:
        name = company['company'].lower()

        if name not in merged:
            # First time seeing this company
            merged[name] = company.copy()
            merged[name]['source_pdfs'] = [company['source_pdf']]
            merged[name]['roles'] = [company['role']]
        else:
            # Company exists - merge data
            existing = merged[name]

            # Add new PDF source if different
            if company['source_pdf'] not in existing['source_pdfs']:
                existing['source_pdfs'].append(company['source_pdf'])

            # Add new role if different
            if company['role'] not in existing['roles']:
                existing['roles'].append(company['role'])

            # Update team size if we find a better value
            if company.get('team_size') and (not existing.get('team_size') or company['team_size'] > existing['team_size']):
                existing['team_size'] = company['team_size']

            # Update contact info if missing
            if not existing.get('contact_name') and company.get('contact_name'):
                existing['contact_name'] = company['contact_name']
                existing['contact_title'] = company['contact_title']

            # Take higher confidence
            existing['confidence'] = max(existing['confidence'], company['confidence'])

            # Merge flags
            for flag in company.get('flags', []):
                if flag not in existing.get('flags', []):
                    existing.setdefault('flags', []).append(flag)

    # Convert lists to readable strings
    for company in merged.values():
        company['source_pdf'] = ', '.join(company['source_pdfs'])
        company['role'] = ', '.join(sorted(set(company['roles'])))
        del company['source_pdfs']
        del company['roles']

    return list(merged.values())
