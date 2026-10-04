import pandas as pd
import re
from urllib.parse import urlparse

INPUT = "reports/evidence_with_source_type.xlsx"
OUTPUT = "reports/quality_verified_evidence.xlsx"

df = pd.read_excel(INPUT).fillna("")

SOURCE_WEIGHTS = {
    "OFFICIAL_FIRST_PARTY": 5,
    "DIRECTORY": 3,
    "LIST_ARTICLE": 2,
    "SOCIAL_OR_VIDEO": 1,
    "OTHER": 1
}

DIRECTORY_DOMAINS = [
    "zomato.com",
    "tripadvisor.com",
    "tripadvisor.in",
    "swiggy.com",
    "eazydiner.com",
    "dineout.co.in"
]

SOCIAL_DOMAINS = [
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "facebook.com"
]

def normalize_text(text):
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def domain(url):
    try:
        return urlparse(str(url)).netloc.lower().replace("www.", "")
    except:
        return ""

def business_tokens(name):
    words = normalize_text(name).split()

    # Ignore extremely generic words
    stop = {
        "restaurant",
        "restaurants",
        "hotel",
        "jaipur",
        "bar",
        "cafe",
        "the"
    }

    return set(x for x in words if len(x) >= 3 and x not in stop)

def entity_score(business, url, evidence_text=""):
    tokens = business_tokens(business)

    combined = normalize_text(
        str(url) + " " + str(evidence_text)
    )

    if not tokens:
        return 0

    matches = sum(
        1 for token in tokens
        if token in combined
    )

    return round(matches / len(tokens), 2)

def quality_label(source_type, entity_score_value):

    base = SOURCE_WEIGHTS.get(source_type, 1)

    if source_type == "OFFICIAL_FIRST_PARTY":
        if entity_score_value >= 0.5:
            return "HIGH"

        return "REVIEW"

    if source_type == "DIRECTORY":
        if entity_score_value >= 0.5:
            return "MEDIUM"

        return "LOW"

    if source_type in ["LIST_ARTICLE", "SOCIAL_OR_VIDEO"]:
        if entity_score_value >= 0.5:
            return "LOW_MEDIUM"

        return "LOW"

    return "LOW"


rows = []

for _, r in df.iterrows():

    business = str(r["business_name"])
    url = str(r["source_url"])
    source_type = str(r["source_type"])

    # Combine extracted fields to evaluate entity relevance
    evidence_text = " ".join([
        str(r.get("phone", "")),
        str(r.get("address", "")),
        str(r.get("hours", "")),
        str(r.get("email", ""))
    ])

    score = entity_score(
        business,
        url,
        evidence_text
    )

    quality = quality_label(
        source_type,
        score
    )

    rows.append({
        "business_name": business,
        "field_phone": r.get("phone", ""),
        "field_address": r.get("address", ""),
        "field_hours": r.get("hours", ""),
        "field_email": r.get("email", ""),
        "source_type": source_type,
        "source_domain": domain(url),
        "entity_match_score": score,
        "source_quality": quality,
        "source_url": url
    })


out = pd.DataFrame(rows)

out.to_excel(
    OUTPUT,
    index=False
)

print()
print("==============================")
print("QUALITY VERIFIED EVIDENCE")
print("==============================")
print()

print("Evidence records:", len(out))
print("Businesses:", out["business_name"].nunique())

print()
print("Source quality:")
print(
    out["source_quality"]
    .value_counts()
    .to_string()
)

print()
print("Entity match:")
print(
    out["entity_match_score"]
    .value_counts()
    .sort_index()
    .to_string()
)

print()
print("Saved:", OUTPUT)
