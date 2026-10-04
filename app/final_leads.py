import pandas as pd

INPUT = "reports/final_clean_leads_v17.xlsx"
OUTPUT = "reports/final_leads.xlsx"

df = pd.read_excel(INPUT)

# Final usable leads: specific addresses only
df = df[df["address_quality"] == "SPECIFIC"].copy()

# Remove duplicate business names
df = df.drop_duplicates("business_name")

df["verification_status"] = "WEB_REVIEW_REQUIRED"
df["physical_verification"] = "NOT_PHYSICALLY_VERIFIED"

df = df[
    [
        "business_name",
        "address",
        "web_evidence",
        "verification_status",
        "physical_verification",
    ]
]

df.to_excel(OUTPUT, index=False)

print("=" * 70)
print("FINAL LEADS")
print("=" * 70)
print()
print("Usable businesses:", len(df))
print()
print(df.to_string(index=False))
print()
print("Saved:", OUTPUT)