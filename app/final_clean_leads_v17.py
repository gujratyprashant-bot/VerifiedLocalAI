import pandas as pd
import re

INPUT = "reports/final_clean_leads_v16.xlsx"
OUTPUT = "reports/final_clean_leads_v17.xlsx"

df = pd.read_excel(INPUT)

def clean(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x).strip())

df["business_name"] = df["business_name"].apply(clean)
df["address"] = df["address"].apply(clean)

# Remove duplicate businesses, keeping the first clean address
df = df.drop_duplicates("business_name").copy()

# Reject clearly incomplete/generic addresses
generic = {
    "mi road jaipur",
    "m.i. road, jaipur",
    "tonk road, jaipur",
    "kings road, ajmer road, jaipur",
    "station road, sindhi camp, jaipur",
    "jawahar lal nehru marg, malviya nagar, jaipur",
}

df["address_quality"] = df["address"].apply(
    lambda x: "SPECIFIC" if x.lower() not in generic else "GENERIC"
)

# Keep every business, but clearly label address quality
df["verification_status"] = "WEB_REVIEW_REQUIRED"
df["physical_verification"] = "NOT_PHYSICALLY_VERIFIED"

df = df[
    [
        "business_name",
        "address",
        "address_quality",
        "web_evidence",
        "verification_status",
        "physical_verification",
    ]
]

df.to_excel(OUTPUT, index=False)

print("=" * 70)
print("FINAL CLEAN LEADS V17")
print("=" * 70)
print()
print("Businesses:", len(df))
print()
print("ADDRESS QUALITY")
print(df["address_quality"].value_counts().to_string())
print()
print(df.to_string(index=False))
print()
print("Saved:", OUTPUT)