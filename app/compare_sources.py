import pandas as pd
import re

INPUT_FILE = "data/businesses.xlsx"
OUTPUT_FILE = "reports/source_comparison.xlsx"

df = pd.read_excel(INPUT_FILE)


def normalize(value):
    if pd.isna(value):
        return ""

    value = str(value).lower().strip()

    # Remove common punctuation/spaces
    value = re.sub(r"[\s\-\(\)\.,]+", "", value)

    return value


results = []

for _, business in df.iterrows():

    name = business["business_name"]

    print("\n" + "=" * 60)
    print(f"🔎 {name}")

    # Existing structured data
    website = str(business.get("website", ""))
    phone = str(business.get("phone", ""))
    address = str(business.get("address", ""))
    hours = str(business.get("hours", ""))

    result = {
        "business_name": name,
        "website": website,
        "phone": phone,
        "address": address,
        "hours": hours,
        "phone_status": "NOT_CHECKED",
        "address_status": "NOT_CHECKED",
        "hours_status": "NOT_CHECKED",
        "overall_status": "NOT_CHECKED",
    }

    # For now, mark the primary source as AVAILABLE.
    # Independent source comparison will be plugged in next.
    if phone:
        result["phone_status"] = "AVAILABLE"

    if address:
        result["address_status"] = "AVAILABLE"

    if hours:
        result["hours_status"] = "AVAILABLE"

    available_fields = [
        result["phone_status"] == "AVAILABLE",
        result["address_status"] == "AVAILABLE",
        result["hours_status"] == "AVAILABLE",
    ]

    if all(available_fields):
        result["overall_status"] = "READY_FOR_COMPARISON"
    elif any(available_fields):
        result["overall_status"] = "PARTIAL"
    else:
        result["overall_status"] = "MISSING"

    print(f"📞 Phone: {result['phone_status']}")
    print(f"📍 Address: {result['address_status']}")
    print(f"🕐 Hours: {result['hours_status']}")
    print(f"📊 Overall: {result['overall_status']}")

    results.append(result)


output_df = pd.DataFrame(results)

output_df.to_excel(OUTPUT_FILE, index=False)

print("\n" + "=" * 60)
print("✅ Source comparison structure created")
print(f"📄 Saved: {OUTPUT_FILE}")