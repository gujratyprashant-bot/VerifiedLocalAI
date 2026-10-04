import pandas as pd
import re

INPUT = "reports/verification_v13.xlsx"
OUTPUT = "reports/final_business_dataset_v14.xlsx"

df = pd.read_excel(INPUT)

# Businesses that are clearly not suitable as restaurant/business leads
REMOVE = {
    "JAWAHAR KALA KENDRA",
}

# Normalize display names
NAME_FIX = {
    "Café White Sage": "Cafe White Sage",
    "bar palladio": "Bar Palladio",
    "rawat misthan bhandar": "Rawat Misthan Bhandar",
    "steam, taj rambagh palace": "Steam, Taj Rambagh Palace",
}

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def norm_phone(x):
    s = re.sub(r"\D", "", clean(x))
    if s.startswith("91") and len(s) >= 12:
        s = s[-10:]
    if len(s) == 10 and s[0] in "6789":
        return s
    return ""

def clean_address(x):
    x = clean(x)
    if not x:
        return ""

    x = re.sub(r"\s+", " ", x)

    # Remove obvious extraction noise
    bad = [
        "order online",
        "book a table",
        "reviews",
        "rating",
        "open now",
        "closed",
        "phone",
        "call",
    ]

    low = x.lower()

    for b in bad:
        if b in low:
            return ""

    return x.strip(" -|,")

def confidence(row):

    overall = clean(row["overall_status"])
    address = clean(row["address_status"])
    hours = clean(row["hours_status"])

    if overall == "CONFLICT":
        return "LOW"

    if (
        address == "SINGLE_SOURCE"
        and hours == "SINGLE_SOURCE"
    ):
        return "MEDIUM"

    if (
        address == "SINGLE_SOURCE"
        or hours == "SINGLE_SOURCE"
    ):
        return "LOW_MEDIUM"

    if overall == "SINGLE_SOURCE":
        return "LOW_MEDIUM"

    return "LOW"

def verification_status(row):

    overall = clean(row["overall_status"])

    if overall == "CONFLICT":
        return "REQUIRES_REVIEW"

    if overall == "SINGLE_SOURCE":
        return "SINGLE_SOURCE_ONLY"

    if overall == "NO_EVIDENCE":
        return "INSUFFICIENT_EVIDENCE"

    return "WEB_EVIDENCE_ONLY"

rows = []

for _, r in df.iterrows():

    name = clean(
        r["business_name"]
    )

    if name in REMOVE:
        continue

    name = NAME_FIX.get(
        name,
        name
    )

    address = clean_address(
        r["address"]
    )

    phone = norm_phone(
        r["phone"]
    )

    rows.append({
        "business_name": name,

        "phone": phone,

        "address": address,

        "hours": clean(
            r["hours"]
        ),

        "phone_status": clean(
            r["phone_status"]
        ),

        "address_status": clean(
            r["address_status"]
        ),

        "hours_status": clean(
            r["hours_status"]
        ),

        "verification_status":
            verification_status(r),

        "confidence":
            confidence(r),

        "physical_verification":
            "NOT_PHYSICALLY_VERIFIED",

        "overall_web_status":
            clean(r["overall_status"])
    })

out = pd.DataFrame(rows)

# Remove exact duplicate businesses after name cleanup
out = out.drop_duplicates(
    subset=["business_name"],
    keep="first"
)

out = out.sort_values(
    by=[
        "verification_status",
        "business_name"
    ]
)

out.to_excel(
    OUTPUT,
    index=False
)

print("=" * 70)
print("FINAL BUSINESS DATASET V14")
print("=" * 70)

print()
print("Businesses retained:", len(out))

print()
print("VERIFICATION STATUS")
print(
    out["verification_status"]
    .value_counts()
    .to_string()
)

print()
print("CONFIDENCE")
print(
    out["confidence"]
    .value_counts()
    .to_string()
)

print()
print("PHYSICAL VERIFICATION")
print(
    out["physical_verification"]
    .value_counts()
    .to_string()
)

print()
print("FINAL BUSINESSES")
print(
    out[
        [
            "business_name",
            "address",
            "phone",
            "verification_status",
            "confidence"
        ]
    ].to_string(index=False)
)

print()
print("Saved:", OUTPUT)
