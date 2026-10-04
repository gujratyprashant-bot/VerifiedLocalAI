import pandas as pd
import re
from difflib import SequenceMatcher

INPUT = "reports/strict_evidence_v2.xlsx"
OUTPUT = "reports/address_consensus.xlsx"

df = pd.read_excel(INPUT)

df = df[
    df["strict_address"].notna()
    & (df["strict_address"].astype(str).str.strip() != "")
].copy()

def norm(s):
    s = str(s).lower()

    # Remove obvious noise
    s = re.sub(r"\b(direction|copy|report an error|dropdown|view in map)\b", " ", s)

    # Common Indian address abbreviations
    replacements = {
        "road": "rd",
        "street": "st",
        "marg": "rd",
        "circle": "cir",
        "number": "no",
        "no.": "no",
    }

    for a, b in replacements.items():
        s = re.sub(r"\b" + re.escape(a) + r"\b", b, s)

    # Keep useful address tokens
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    return s


def tokens(s):
    return set(norm(s).split())


def similarity(a, b):
    ta = tokens(a)
    tb = tokens(b)

    if not ta or not tb:
        return 0

    # Jaccard token similarity
    jaccard = len(ta & tb) / len(ta | tb)

    # Sequence similarity
    seq = SequenceMatcher(None, norm(a), norm(b)).ratio()

    return round((jaccard * 0.7) + (seq * 0.3), 3)


def pincode(s):
    m = re.search(r"\b\d{6}\b", str(s))
    return m.group(0) if m else ""


rows = []

for business, group in df.groupby("business_name"):

    records = group.to_dict("records")

    # Build clusters using address similarity
    clusters = []

    for r in records:
        placed = False

        for cluster in clusters:
            sim = similarity(
                r["strict_address"],
                cluster[0]["strict_address"]
            )

            pin1 = pincode(r["strict_address"])
            pin2 = pincode(cluster[0]["strict_address"])

            # Same pincode is a strong signal
            if sim >= 0.48 or (pin1 and pin2 and pin1 == pin2 and sim >= 0.25):
                cluster.append(r)
                placed = True
                break

        if not placed:
            clusters.append([r])

    # Score each cluster
    for i, cluster in enumerate(clusters, start=1):

        addresses = [x["strict_address"] for x in cluster]

        unique_urls = set(
            str(x["url"]).strip().lower()
            for x in cluster
            if str(x["url"]).strip()
        )

        relevance_values = [
            float(x["entity_relevance"])
            for x in cluster
            if pd.notna(x["entity_relevance"])
        ]

        strong_relevance = sum(x >= 2 for x in relevance_values)

        pins = [
            pincode(x)
            for x in addresses
            if pincode(x)
        ]

        common_pin = ""
        if pins:
            common_pin = max(set(pins), key=pins.count)

        source_count = len(unique_urls)
        evidence_count = len(cluster)

        # Consensus score
        score = 0

        score += min(source_count, 3) * 20
        score += min(strong_relevance, 3) * 10

        if evidence_count >= 2:
            score += 15

        if common_pin:
            score += 10

        score = min(score, 100)

        if source_count >= 2 and evidence_count >= 2 and score >= 60:
            status = "LIKELY_WEB_CONSENSUS"
        elif evidence_count >= 2:
            status = "WEAK_CONSENSUS"
        else:
            status = "SINGLE_SOURCE"

        rows.append({
            "business_name": business,
            "cluster_id": i,
            "representative_address": addresses[0],
            "evidence_count": evidence_count,
            "unique_sources": source_count,
            "strong_relevance_sources": strong_relevance,
            "pincode": common_pin,
            "consensus_score": score,
            "status": status,
            "all_addresses": " || ".join(addresses)
        })


out = pd.DataFrame(rows)

out = out.sort_values(
    ["business_name", "consensus_score"],
    ascending=[True, False]
)

out.to_excel(OUTPUT, index=False)

print("=" * 50)
print("ADDRESS CONSENSUS ENGINE")
print("=" * 50)
print()
print("Businesses:", out["business_name"].nunique())
print("Address clusters:", len(out))
print()
print("Status:")
print(out["status"].value_counts().to_string())
print()
print("TOP RESULTS")
print(
    out[
        [
            "business_name",
            "representative_address",
            "evidence_count",
            "unique_sources",
            "consensus_score",
            "status"
        ]
    ].to_string(index=False)
)
print()
print("Saved:", OUTPUT)
