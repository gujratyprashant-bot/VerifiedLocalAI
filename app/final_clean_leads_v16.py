import pandas as pd
import re

INPUT = "reports/address_final_v8.xlsx"
OUTPUT = "reports/final_clean_leads_v16.xlsx"

df = pd.read_excel(INPUT)

def clean_address(x):
    if pd.isna(x):
        return ""
    x = str(x).lower().strip()
    x = re.sub(r"\s+", " ", x)
    x = x.replace(" |", "")
    return x

df["address"] = df["representative_address"].apply(clean_address)

# Remove obvious junk/contaminated addresses
bad_words = [
    "desserts", "beverages.", "average price", "per person",
    "no description", "dropdown", "request reservation",
    "open now", "more st", "best street"
]

def valid_address(x):
    if not x:
        return False
    if any(w in x for w in bad_words):
        return False
    return len(x) >= 8

df = df[df["address"].apply(valid_address)].copy()

# Prefer cleaner, more specific addresses
def address_score(x):
    score = 0
    if "jaipur" in x:
        score += 2
    if any(w in x for w in ["road", "marg", "bazar", "nagar", "circle", "chaupar"]):
        score += 2
    if re.search(r"\b\d+\b", x):
        score += 2
    if len(x) >= 30:
        score += 1
    return score

df["address_score"] = df["address"].apply(address_score)

# Keep best address per business
df = (
    df.sort_values(["business_name", "address_score"], ascending=[True, False])
      .drop_duplicates("business_name")
)

df["verification_status"] = "WEB_REVIEW_REQUIRED"
df["physical_verification"] = "NOT_PHYSICALLY_VERIFIED"

final = df[
    ["business_name", "address", "web_evidence",
     "verification_status", "physical_verification"]
].copy()

final.to_excel(OUTPUT, index=False)

print("=" * 70)
print("FINAL CLEAN LEADS V16")
print("=" * 70)
print()
print("Usable businesses:", len(final))
print()
print(final.to_string(index=False))
print()
print("Saved:", OUTPUT)