"""PDF parsing utilities for conference documents.

Why this exists
---------------
The original project parsed PDFs by doing `page.get_text()` and then scanning lines.
For the provided WBR PDFs this produces a lot of junk (marketing copy, navigation chrome)
and it also misses the key structure needed to link *people -> company*.

This version is layout-aware using PyMuPDF:

- Attendee List PDF:
  Extract short text blocks on the *company list pages* and parse
  `Company (Team of N)` when present.

- Agenda PDF:
  Extract speaker cards from the "SPEAKER LINEUP" pages using font metadata:
    * Name lines are "Medium"
    * Title lines are "Light"
    * Company lines are "Bold"
    * The "NEW" tag is stripped

Backwards compatibility
-----------------------
- `parse_generic_pdf()` still exists and is used by the rest of your repo.
- `merge_all_companies()` still returns one row per company and preserves
  `contact_name/contact_title`, but it now also adds `contacts: [...]` so you
  don't lose multiple speaker attendees from the same company.
"""

from __future__ import annotations

import builtins
import os
import re
from collections import Counter
from typing import Dict, List, Tuple

import fitz  # PyMuPDF


# -----------------------------
# Normalization helpers
# -----------------------------
def _norm(text: str) -> str:
    return " ".join((text or "").replace("\u00a0", " ").replace("\t", " ").split())


def _strip_new_tag(text: str) -> str:
    """Remove trailing NEW tag used in the agenda speaker lineup."""
    text = _norm(text)
    return re.sub(r"\s+\bNEW\b\s*$", "", text, flags=re.IGNORECASE).strip()


def clean_company_name(name: str) -> str:
    """Light normalization; keep internal punctuation (e.g., ASML/Cymer)."""
    name = _strip_new_tag(name).strip(" ,")
    name = re.sub(r"\s*&\s*", " & ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


# -----------------------------
# Validators / filters
# -----------------------------
def is_person_name(text: str) -> bool:
    """Heuristic: 2–4 capitalized tokens, no commas/digits."""
    text = _norm(text)
    if not text or len(text) < 4 or len(text) > 60:
        return False
    if "," in text:
        return False
    if re.search(r"\d", text):
        return False

    words = text.split()
    if len(words) < 2 or len(words) > 4:
        return False

    bad = {
        "agenda", "speaker", "lineup", "register", "now", "about", "jump", "to",
        "day", "am", "pm",
    }
    if builtins.any(w.lower() in bad for w in words):
        return False

    return builtins.all(re.match(r"^[A-Z][A-Za-z'\-\.]*$", w) for w in words)


def is_valid_company_name(text: str) -> bool:
    """Very lightweight company check (mostly for fallbacks)."""
    t = clean_company_name(text)
    if not t or len(t) < 2 or len(t) > 90:
        return False
    if re.fullmatch(r"\d+(\.\d+)?%?", t):
        return False
    return True


def is_header_footer(text: str) -> bool:
    """Filter obvious conference chrome / marketing lines."""
    t = _norm(text).lower()
    if not t:
        return True
    if "fieldserviceusa.wbresearch.com" in t:
        return True
    if "register now" in t or "jump to" in t:
        return True
    if "sponsorship" in t and "now open" in t:
        return True
    if "request a quote" in t:
        return True
    if len(t) > 140:
        return True
    if re.fullmatch(r"\d+", t):
        return True
    return False


# -----------------------------
# PyMuPDF layout helpers
# -----------------------------
def _dominant_font(line: Dict) -> str:
    fonts = [s.get("font", "") for s in line.get("spans", []) if (s.get("text") or "").strip()]
    if not fonts:
        return ""
    return Counter(fonts).most_common(1)[0][0]


def _line_text(line: Dict) -> str:
    return _norm("".join(s.get("text", "") for s in line.get("spans", [])))


def _is_company_font(font: str) -> bool:
    """Agenda PDF uses Bold/XBold fonts for company lines."""
    f = (font or "").lower()
    return ("bold" in f) and ("light" not in f)


def _dedupe_records(rows: List[Dict]) -> List[Dict]:
    """Deduplicate *records* by (company, contact, title, role)."""
    seen = set()
    out = []
    for r in rows:
        key = (
            (r.get("company") or "").lower().strip(),
            (r.get("contact_name") or "").lower().strip(),
            (r.get("contact_title") or "").lower().strip(),
            (r.get("role") or "").lower().strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


# -----------------------------
# Parsers (layout-aware)
# -----------------------------
def parse_attendee_list_pdf(pdf_path: str) -> List[Dict]:
    """Extract companies (+ optional team size) from attendee list PDFs."""
    doc = fitz.open(pdf_path)
    pdf_filename = os.path.basename(pdf_path)
    results: List[Dict] = []

    for page_index in range(doc.page_count):
        page = doc[page_index]
        page_text = page.get_text()
        team_cnt = page_text.lower().count("team of")
        blocks = page.get_text("blocks")

        # In the provided attendee PDF, the real company list pages match this signature.
        if team_cnt < 5 and len(blocks) < 40:
            continue

        for _, _, _, _, block_text, *_ in blocks:
            if len(block_text) > 200:
                continue

            for raw_line in block_text.splitlines():
                line = _norm(raw_line)
                if not line or is_header_footer(line):
                    continue

                low = line.lower()
                if builtins.any(k in low for k in ["sponsorship", "speaking", "exhibition", "now open"]):
                    continue

                m = re.match(r"^(.*?)\s*\(Team of\s*(\d+)\)\s*$", line, flags=re.IGNORECASE)
                if m:
                    company = clean_company_name(m.group(1))
                    team_size = int(m.group(2))
                    confidence = 0.95
                else:
                    company = clean_company_name(line)
                    team_size = 1
                    confidence = 0.90

                if re.fullmatch(r"\d+(\.\d+)?%?", company):
                    continue
                if len(company) < 2 or len(company) > 80:
                    continue

                results.append(
                    {
                        "company": company,
                        "source_pdf": pdf_filename,
                        "role": "attendee",
                        "contact_name": None,
                        "contact_title": None,
                        "team_size": team_size,
                        "confidence": confidence,
                        "flags": [],
                        "source_page": page_index + 1,
                    }
                )

    doc.close()
    return deduplicate_companies(results)


def parse_agenda_speaker_lineup_pdf(pdf_path: str) -> List[Dict]:
    """Extract speaker cards from agenda speaker lineup pages (font-aware)."""
    doc = fitz.open(pdf_path)
    pdf_filename = os.path.basename(pdf_path)
    results: List[Dict] = []

    for page_index in range(doc.page_count):
        page = doc[page_index]
        page_text = page.get_text()
        if "SPEAKER LINEUP" not in page_text and "VOICES OF THE NEXT ERA" not in page_text:
            continue

        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            lines = block.get("lines", [])
            if not lines:
                continue

            line_items: List[Tuple[str, str]] = []
            for ln in lines:
                t = _line_text(ln)
                if not t:
                    continue
                f = _dominant_font(ln)
                line_items.append((t, f))

            if len(line_items) < 3:
                continue

            combined = " ".join(t for t, _ in line_items).lower()
            if builtins.any(k in combined for k in ["fieldserviceusa.wbresearch.com", "register now", "jump to", "about"]):
                continue

            name = line_items[0][0]
            if not is_person_name(name):
                continue

            company_parts: List[str] = []
            j = len(line_items) - 1
            while j >= 1:
                t, font = line_items[j]
                if t.upper() == "NEW":
                    j -= 1
                    continue
                if _is_company_font(font):
                    company_parts.insert(0, _strip_new_tag(t))
                    j -= 1
                else:
                    break

            if not company_parts:
                company_parts = [_strip_new_tag(line_items[-1][0])]
                j = len(line_items) - 2

            company = clean_company_name(" ".join(company_parts))

            title_parts = [t for t, _ in line_items[1 : j + 1] if t.upper() != "NEW"]
            title = _norm(" ".join(title_parts)) if title_parts else None

            results.append(
                {
                    "company": company,
                    "source_pdf": pdf_filename,
                    "role": "speaker",
                    "contact_name": _norm(name),
                    "contact_title": title,
                    "team_size": None,
                    "confidence": 0.90,
                    "flags": [],
                    "source_page": page_index + 1,
                }
            )

    doc.close()
    return _dedupe_records(results)


def parse_agenda_schedule_lines(pdf_path: str) -> List[Dict]:
    """Secondary extraction: schedule pages sometimes list 'Name, Title, Company'."""
    doc = fitz.open(pdf_path)
    pdf_filename = os.path.basename(pdf_path)
    results: List[Dict] = []

    for page_index in range(doc.page_count):
        page = doc[page_index]
        text = page.get_text()

        if "AGENDA" not in text and "Day" not in text and " AM" not in text and " PM" not in text:
            continue

        for raw in text.splitlines():
            line = _norm(raw)
            if not line or is_header_footer(line):
                continue
            if line.count(",") < 2:
                continue

            first = line.find(",")
            last = line.rfind(",")
            if last == first:
                continue

            name = _norm(line[:first])
            company = clean_company_name(line[last + 1 :])
            title = _norm(line[first + 1 : last])

            if not is_person_name(name):
                continue
            if len(company) < 2 or len(company) > 80:
                continue

            results.append(
                {
                    "company": company,
                    "source_pdf": pdf_filename,
                    "role": "speaker",
                    "contact_name": name,
                    "contact_title": title or None,
                    "team_size": None,
                    "confidence": 0.75,
                    "flags": ["schedule_line_parse"],
                    "source_page": page_index + 1,
                }
            )

    doc.close()
    return _dedupe_records(results)


# -----------------------------
# Dispatcher (used by the repo)
# -----------------------------
def parse_conference_pdf(pdf_path: str) -> List[Dict]:
    filename = os.path.basename(pdf_path).lower()

    if "attendee" in filename:
        return parse_attendee_list_pdf(pdf_path)

    if "agenda" in filename or "speaker" in filename:
        results: List[Dict] = []
        results.extend(parse_agenda_speaker_lineup_pdf(pdf_path))
        results.extend(parse_agenda_schedule_lines(pdf_path))
        return _dedupe_records(results)

    return parse_text_fallback(pdf_path)


def parse_generic_pdf(pdf_path: str) -> List[Dict]:
    """Backwards-compatible entry point used by the rest of the repo."""
    return parse_conference_pdf(pdf_path)


# -----------------------------
# Fallback parser (minimal)
# -----------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    parts = [p.get_text() for p in doc]
    doc.close()
    return "\n".join(parts)


def parse_text_fallback(pdf_path: str) -> List[Dict]:
    text = extract_text_from_pdf(pdf_path)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    pdf_filename = os.path.basename(pdf_path)
    results: List[Dict] = []

    for ln in lines:
        if is_header_footer(ln):
            continue
        m = re.match(r"^(.*?)\s*\(Team of\s*(\d+)\)\s*$", ln, flags=re.IGNORECASE)
        if m:
            results.append(
                {
                    "company": clean_company_name(m.group(1)),
                    "source_pdf": pdf_filename,
                    "role": "attendee",
                    "contact_name": None,
                    "contact_title": None,
                    "team_size": int(m.group(2)),
                    "confidence": 0.85,
                    "flags": ["fallback_team_size"],
                }
            )

    return deduplicate_companies(results)


# -----------------------------
# Deduping / merging
# -----------------------------
def deduplicate_companies(companies: List[Dict]) -> List[Dict]:
    """Deduplicate attendee-style company rows (case-insensitive company key)."""
    seen: Dict[str, Dict] = {}
    for c in companies:
        key = (c.get("company") or "").lower().strip()
        if not key:
            continue

        if key not in seen:
            seen[key] = c
            continue

        existing = seen[key]
        existing["confidence"] = max(existing.get("confidence", 0), c.get("confidence", 0))

        if c.get("team_size"):
            existing["team_size"] = max(existing.get("team_size") or 0, c.get("team_size") or 0) or existing.get("team_size")

        ex_flags = set(existing.get("flags", []))
        for fl in c.get("flags", []):
            ex_flags.add(fl)
        existing["flags"] = sorted(ex_flags)

    return list(seen.values())


def merge_all_companies(all_companies: List[Dict]) -> List[Dict]:
    """Merge across PDFs; preserve *multiple* contacts per company."""
    merged: Dict[str, Dict] = {}

    for c in all_companies:
        company = clean_company_name(c.get("company") or "")
        if not company:
            continue
        key = company.lower()

        if key not in merged:
            merged[key] = {
                "company": company,
                "source_pdfs": set(),
                "roles": set(),
                "team_size": c.get("team_size"),
                "confidence": c.get("confidence", 0),
                "flags": set(c.get("flags", [])),
                "contacts": [],  # list[{name,title,source_pdf}]
            }

        m = merged[key]
        if c.get("source_pdf"):
            m["source_pdfs"].add(c["source_pdf"])
        if c.get("role"):
            m["roles"].add(c["role"])

        if c.get("team_size"):
            m["team_size"] = max(m.get("team_size") or 0, c.get("team_size") or 0) or m.get("team_size")

        m["confidence"] = max(m.get("confidence", 0), c.get("confidence", 0))

        for fl in c.get("flags", []):
            m["flags"].add(fl)

        if c.get("contact_name"):
            contact = {
                "name": _norm(c["contact_name"]),
                "title": _norm(c.get("contact_title") or "") or None,
                "source_pdf": c.get("source_pdf"),
            }
            if not builtins.any(
                (ct.get("name", "").lower() == contact["name"].lower())
                and ((ct.get("title") or "").lower() == (contact.get("title") or "").lower())
                for ct in m["contacts"]
            ):
                m["contacts"].append(contact)

    out: List[Dict] = []
    for m in merged.values():
        m["source_pdf"] = ", ".join(sorted(m["source_pdfs"]))
        m["role"] = ", ".join(sorted(set(m["roles"])))
        m["flags"] = sorted(m["flags"])
        del m["source_pdfs"]
        del m["roles"]

        # Backwards compatibility
        if m["contacts"]:
            m["contact_name"] = m["contacts"][0]["name"]
            m["contact_title"] = m["contacts"][0].get("title")
        else:
            m["contact_name"] = None
            m["contact_title"] = None

        out.append(m)

    return out
