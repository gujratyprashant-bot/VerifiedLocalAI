import pandas as pd
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

INPUT_FILE = "data/businesses.xlsx"
OUTPUT_FILE = "reports/web_evidence.xlsx"

df = pd.read_excel(INPUT_FILE)

results = []

for _, business in df.iterrows():
    name = business["business_name"]
    website = business["website"]

    print("\n" + "=" * 60)
    print(f"🔎 {name}")

    result = {
        "business_name": name,
        "website": website,
        "https": website.startswith("https://"),
        "phone_found": False,
        "address_signal_found": False,
        "menu_signal_found": False,
        "hours_signal_found": False,
        "email_found": False,
        "evidence_score": 0,
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        response = requests.get(
            website,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True).lower()

        # Phone-number pattern
        phone_pattern = r"(?:\+91[\s-]?)?[6-9]\d{9}"
        result["phone_found"] = bool(re.search(phone_pattern, text))

        # Basic evidence signals
        address_words = ["address", "location", "jaipur", "hathroi", "ajmer road"]
        menu_words = ["menu", "restaurant", "food", "dining"]
        hours_words = ["hours", "open", "timing", "breakfast", "lunch", "dinner"]
        
        result["address_signal_found"] = any(word in text for word in address_words)
        result["menu_signal_found"] = any(word in text for word in menu_words)
        result["hours_signal_found"] = any(word in text for word in hours_words)

        # Email
        email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
        result["email_found"] = bool(re.search(email_pattern, text))

        # Score
        signals = [
            result["https"],
            result["phone_found"],
            result["address_signal_found"],
            result["menu_signal_found"],
            result["hours_signal_found"],
            result["email_found"],
        ]

        result["evidence_score"] = sum(signals)

        print(f"🔒 HTTPS: {'YES' if result['https'] else 'NO'}")
        print(f"📞 Phone signal: {'YES' if result['phone_found'] else 'NO'}")
        print(f"📍 Address signal: {'YES' if result['address_signal_found'] else 'NO'}")
        print(f"🍽️ Menu/food signal: {'YES' if result['menu_signal_found'] else 'NO'}")
        print(f"🕐 Hours signal: {'YES' if result['hours_signal_found'] else 'NO'}")
        print(f"📧 Email: {'YES' if result['email_found'] else 'NO'}")
        print(f"📊 Evidence score: {result['evidence_score']}/6")

    except requests.RequestException as e:
        print(f"❌ Error: {e}")

    results.append(result)

result_df = pd.DataFrame(results)
result_df.to_excel(OUTPUT_FILE, index=False)

print("\n" + "=" * 60)
print(f"✅ Evidence extraction complete")
print(f"📄 Saved: {OUTPUT_FILE}")