import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

INPUT_FILE = "data/businesses.xlsx"
OUTPUT_FILE = "reports/web_verification.xlsx"

df = pd.read_excel(INPUT_FILE)

results = []

for _, business in df.iterrows():
    name = business["business_name"]
    website = business["website"]

    print("\n" + "=" * 60)
    print(f"🔎 Checking: {name}")
    print(f"🌐 Website: {website}")

    result = {
        "business_name": name,
        "website": website,
        "website_reachable": False,
        "http_status": None,
        "page_title": None,
        "page_text_length": 0,
        "web_confidence": "Low",
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        response = requests.get(
            website,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        result["http_status"] = response.status_code

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.get_text(strip=True) if soup.title else ""
        text = soup.get_text(" ", strip=True)

        result["page_title"] = title
        result["page_text_length"] = len(text)

        if response.ok and len(text) > 500:
            result["website_reachable"] = True
            result["web_confidence"] = "High"
            print("✅ Website verified")

        elif response.ok:
            result["website_reachable"] = True
            result["web_confidence"] = "Medium"
            print("⚠️ Website reachable, but limited content")

        else:
            print("❌ Website returned an error")

    except requests.RequestException as e:
        print(f"❌ Website check failed: {e}")

    results.append(result)

result_df = pd.DataFrame(results)

result_df.to_excel(OUTPUT_FILE, index=False)

print("\n" + "=" * 60)
print(f"✅ Verification finished")
print(f"📄 Report saved to: {OUTPUT_FILE}")