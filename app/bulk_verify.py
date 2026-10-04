import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:5000"
API_URL = BASE_URL + "/api/verify"
INPUT_FILE = Path("reports/final_clean_leads_v17.xlsx")
OUTPUT_FILE = Path("reports/bulk_verification.xlsx")

def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()

def extract_section(soup, heading_text):
    heading = soup.find(
        lambda tag: tag.name in ("h2", "h3", "h4")
        and heading_text.lower() in clean_text(tag.get_text(" ", strip=True)).lower()
    )
    if not heading:
        return ""
    parts = []
    for node in heading.find_all_next():
        if node is heading:
            continue
        if node.name in ("h2", "h3", "h4"):
            break
        text = clean_text(node.get_text(" ", strip=True))
        if text and text not in parts:
            parts.append(text)
    return " ".join(parts)

def verify_business(name):
    response = requests.post(
        API_URL,
        json={"query": name},
        timeout=180,
    )
    response.raise_for_status()

    report = response.json()

    if "error" in report:
        raise RuntimeError(report["error"])

    conflicts = report.get("conflicts") or []

    return {
        "business_name": report.get("name", name),
        "status": report.get("status", ""),
        "score": report.get("score", ""),
        "address": report.get("address", ""),
        "phone": report.get("phone", ""),
        "hours": report.get("hours", ""),
        "conflict_detected": "YES" if conflicts else "NO",
        "assessment": report.get("assessment", ""),
    }

def main():
    if not INPUT_FILE.exists():
        print(f"ERROR: {INPUT_FILE} not found.")
        sys.exit(1)

    try:
        requests.get(BASE_URL, timeout=10)
    except Exception:
        print("ERROR: Flask app is not running.")
        print("Start it first with: python app/web_app.py")
        sys.exit(1)

    df = pd.read_excel(INPUT_FILE)

    if "business_name" not in df.columns:
        print("ERROR: final_leads.xlsx must contain a business_name column.")
        sys.exit(1)

    names = [
        clean_text(x)
        for x in df["business_name"].tolist()
        if clean_text(x)
    ]

    results = []
    total = len(names)

    print(f"Bulk verification started: {total} businesses")

    for i, name in enumerate(names, 1):
        print(f"[{i}/{total}] Verifying: {name}")
        try:
            result = verify_business(name)
            results.append(result)
            print(
                f"    {result['status']} | {result['score']}% | "
                f"conflict={result['conflict_detected']}"
            )
        except Exception as e:
            results.append({
                "business_name": name,
                "status": "ERROR",
                "score": "",
                "address": "",
                "phone": "",
                "hours": "",
                "conflict_detected": "",
                "assessment": str(e),
            })
            print(f"    ERROR: {e}")

        time.sleep(1)

    out = pd.DataFrame(results)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_excel(OUTPUT_FILE, index=False)

    print()
    print("DONE")
    print(f"Saved: {OUTPUT_FILE}")
    print(f"Businesses processed: {len(results)}")

if __name__ == "__main__":
    main()
