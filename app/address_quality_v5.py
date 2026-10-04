import pandas as pd
import re

INPUT = "reports/clean_address_v4.xlsx"
OUTPUT = "reports/address_quality_v5.xlsx"

df = pd.read_excel(INPUT)

def norm(s):
    s = str(s).lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def score_address(row):

    addr = norm(row.get("clean_address", ""))
    business = norm(row.get("business_name", ""))
    title = norm(row.get("title", ""))

    if not addr:
        return 0, "NO_ADDRESS"

    score = 0
    reasons = []

    # Jaipur
    if re.search(r"\bjaipur\b", addr):
        score += 2
        reasons.append("jaipur")

    # Pincode
    if re.search(r"\b[1-9]\d{5}\b", addr):
        score += 3
        reasons.append("pincode")

    # Road/location terms
    if re.search(
        r"\b(road|rd|marg|nagar|bazar|bazaar|chowk|"
        r"colony|market|circle|phatak|camp|bagh|vihar|"
        r"plaza|palace|complex|crossing)\b",
        addr
    ):
        score += 2
        reasons.append("location")

    # Building/shop/plot number
    if re.search(
        r"\b(shop|plot|house|flat|unit|floor|"
        r"khasra|no\.?|number)\s*[\w./-]*\d+",
        addr
    ) or re.search(r"^\d{1,5}[,\s]", addr):
        score += 2
        reasons.append("number")

    # Business name appears in address
    business_tokens = [
        x for x in re.findall(r"[a-z]{4,}", business)
        if x not in {
            "restaurant", "kitchen", "coffee", "bar",
            "jaipur", "since", "road"
        }
    ]

    if business_tokens:
        matches = sum(x in addr for x in business_tokens)

        if matches >= 2:
            score += 2
            reasons.append("business_match")
        elif matches == 1:
            score += 1
            reasons.append("business_match")

    # Strong contamination signals
    bad_patterns = [
        r"\breviews?\b",
        r"\brating\b",
        r"\btripadvisor\b",
        r"\bzomato\b",
        r"\bswiggy\b",
        r"\brequest reservation\b",
        r"\border online\b",
        r"\bdelivery\b",
        r"\bambience\b",
        r"\bdelicious food\b",
        r"\bpopular food destination\b",
        r"\bis a restaurant\b",
        r"\bis best for\b",
        r"\bwell known for\b",
        r"\bfigure[- ]art\b",
    ]

    bad = []

    for p in bad_patterns:
        if re.search(p, addr):
            bad.append(p)

    if bad:
        score -= min(5, len(bad) * 2)
        reasons.append("contamination")

    # Too long usually means paragraph/snippet leakage
    words = addr.split()

    if len(words) > 22:
        score -= 3
        reasons.append("too_long")

    # Very short generic locations
    if len(words) <= 3:
        score -= 1
        reasons.append("too_short")

    # Classification
    if score >= 6:
        quality = "STRONG_ADDRESS"
    elif score >= 3:
        quality = "POSSIBLE_ADDRESS"
    else:
        quality = "REJECT"

    return score, quality, ", ".join(reasons)


results = []

for _, row in df.iterrows():

    score, quality, reasons = score_address(row)

    results.append({
        "business_name": row.get("business_name", ""),
        "title": row.get("title", ""),
        "url": row.get("url", ""),
        "entity_relevance": row.get("entity_relevance", ""),
        "clean_address": row.get("clean_address", ""),
        "pincode": row.get("pincode", ""),
        "address_score": score,
        "quality": quality,
        "reasons": reasons
    })

out = pd.DataFrame(results)

out.to_excel(OUTPUT, index=False)

print("=" * 65)
print("ADDRESS QUALITY V5")
print("=" * 65)
print()
print("Rows:", len(out))
print()
print("Quality:")
print(out["quality"].value_counts().to_string())
print()
print("Businesses with STRONG evidence:",
      out[out["quality"] == "STRONG_ADDRESS"]["business_name"].nunique())
print()
print("Businesses with POSSIBLE evidence:",
      out[out["quality"] == "POSSIBLE_ADDRESS"]["business_name"].nunique())
print()
print("STRONG ADDRESS SAMPLE")
print(
    out[out["quality"] == "STRONG_ADDRESS"][
        [
            "business_name",
            "clean_address",
            "pincode",
            "address_score"
        ]
    ].head(80).to_string(index=False)
)
print()
print("Saved:", OUTPUT)
