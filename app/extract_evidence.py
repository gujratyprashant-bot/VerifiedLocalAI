import pandas as pd
import re
from urllib.parse import urlparse

INPUT = "reports/targeted_sources.xlsx"
OUTPUT = "reports/evidence_extraction.xlsx"

df = pd.read_excel(INPUT)

def clean_text(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def extract_phone(text):
    patterns = [
        r"\+91[\s\-]?\d{5}[\s\-]?\d{5}",
        r"\+91[\s\-]?\d{3,5}[\s\-]?\d{3,5}[\s\-]?\d{3,5}",
        r"\b0\d{2,4}[\s\-]?\d{6,8}\b",
        r"\b\d{10}\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)

    return ""


def extract_email(text):
    match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    return match.group(0) if match else ""


def extract_address(text):
    patterns = [
        r"(?:address|located at|location)\s*[:\-]?\s*([^.\n]{20,180})",
        r"(?:MI Road|M\.I Road|C Scheme|Bani Park|Amer Road|Ajmer Road|Tonk Road|Malviya Nagar|Raja Park)[^.\n]{0,150}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)

        if match:
            return clean_text(match.group(1) if match.lastindex else match.group(0))

    return ""


def extract_hours(text):
    patterns = [
        r"(?:open|opening hours|hours|timings|timing)[^.\n]{0,120}",
        r"\b\d{1,2}(?::\d{2})?\s*(?:AM|PM)\s*(?:to|-|–)\s*\d{1,2}(?::\d{2})?\s*(?:AM|PM)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)

        if match:
            return clean_text(match.group(0))

    return ""


def get_domain(url):
    try:
        return urlparse(str(url)).netloc.replace("www.", "").lower()
    except:
        return ""


records = []

for _, row in df.iterrows():

    business = clean_text(row.get("business_name"))
    title = clean_text(row.get("title"))
    url = clean_text(row.get("url"))
    content = clean_text(row.get("content"))

    combined = f"{title} {content}"

    phone = extract_phone(combined)
    email = extract_email(combined)
    address = extract_address(combined)
    hours = extract_hours(combined)
    domain = get_domain(url)

    records.append({
        "business_name": business,
        "source_title": title,
        "source_url": url,
        "domain": domain,
        "phone": phone,
        "address": address,
        "hours": hours,
        "email": email,
        "evidence_text_length": len(content),
    })


out = pd.DataFrame(records)

out.to_excel(
    OUTPUT,
    index=False
)

print()
print("==============================")
print("EVIDENCE EXTRACTION COMPLETE")
print("==============================")

print("Evidence records:", len(out))
print("Businesses:", out["business_name"].nunique())

print()
print("PHONE FOUND:", (out["phone"] != "").sum())
print("ADDRESS FOUND:", (out["address"] != "").sum())
print("HOURS FOUND:", (out["hours"] != "").sum())
print("EMAIL FOUND:", (out["email"] != "").sum())

print()
print("Saved:", OUTPUT)
