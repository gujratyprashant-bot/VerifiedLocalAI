import pandas as pd
from collections import Counter

INPUT = "reports/evidence_with_source_type.xlsx"
OUTPUT = "reports/weighted_verification.xlsx"

df = pd.read_excel(INPUT).fillna("")

WEIGHTS = {
    "OFFICIAL_FIRST_PARTY": 5,
    "DIRECTORY": 3,
    "LIST_ARTICLE": 2,
    "SOCIAL_OR_VIDEO": 1,
    "OTHER": 1
}

def norm(value, field):
    s = str(value).strip().lower()

    if not s:
        return ""

    if field == "phone":
        digits = "".join(c for c in s if c.isdigit())
        if digits.startswith("91") and len(digits) > 10:
            digits = digits[-10:]
        return digits

    if field == "email":
        return s

    return "".join(c for c in s if c.isalnum())

def field_result(group, field):
    values = []

    for _, row in group.iterrows():
        raw = row.get(field, "")
        value = norm(raw, field)

        if value:
            values.append({
                "value": value,
                "raw": str(raw),
                "type": row["source_type"],
                "weight": WEIGHTS.get(row["source_type"], 1),
                "url": row["source_url"]
            })

    if not values:
        return "NO_EVIDENCE", "", "", 0

    scores = Counter()

    for item in values:
        scores[item["value"]] += item["weight"]

    ranked = scores.most_common()

    winner = ranked[0][0]
    winner_score = ranked[0][1]

    types = sorted(
        set(x["type"] for x in values),
        key=lambda x: WEIGHTS.get(x, 1),
        reverse=True
    )

    winner_items = [x for x in values if x["value"] == winner]
    display_value = winner_items[0]["raw"]

    official_support = any(
        x["value"] == winner and
        x["type"] == "OFFICIAL_FIRST_PARTY"
        for x in values
    )

    distinct_values = len(scores)

    if distinct_values == 1:
        if official_support:
            status = "SUPPORTED_BY_FIRST_PARTY"
        elif len(values) >= 2:
            status = "SUPPORTED_BY_SECONDARY"
        else:
            status = "SINGLE_SOURCE"

    else:
        if official_support:
            status = "FIRST_PARTY_CONFLICT"
        else:
            status = "CONFLICTING_SOURCES"

    source_summary = ", ".join(types)

    return status, display_value, source_summary, winner_score


results = []

fields = ["phone", "address", "hours", "email"]

for business, group in df.groupby("business_name"):

    row = {
        "business_name": business
    }

    statuses = []

    for field in fields:
        status, value, sources, score = field_result(group, field)

        row[field + "_status"] = status
        row[field + "_best_value"] = value
        row[field + "_source_types"] = sources
        row[field + "_weighted_score"] = score

        statuses.append(status)

    if "FIRST_PARTY_CONFLICT" in statuses:
        overall = "FIRST_PARTY_REQUIRES_REVIEW"
        note = "A first-party source exists, but another source disagrees."

    elif "CONFLICTING_SOURCES" in statuses:
        overall = "CONFLICTING_SOURCES"
        note = "Multiple secondary sources contain different values."

    elif "SUPPORTED_BY_FIRST_PARTY" in statuses:
        overall = "FIRST_PARTY_SUPPORTED"
        note = "Available evidence supports at least one field from a first-party source."

    elif "SUPPORTED_BY_SECONDARY" in statuses:
        overall = "SECONDARY_SUPPORTED"
        note = "Evidence is supported by multiple secondary sources."

    elif "SINGLE_SOURCE" in statuses:
        overall = "SINGLE_SOURCE_ONLY"
        note = "Evidence currently comes from only one source."

    else:
        overall = "INSUFFICIENT_EVIDENCE"
        note = "Not enough usable evidence was extracted."

    row["overall_status"] = overall
    row["resolution_note"] = note

    results.append(row)


out = pd.DataFrame(results)

out.to_excel(OUTPUT, index=False)

print()
print("==============================")
print("WEIGHTED VERIFICATION")
print("==============================")
print()
print("Businesses:", len(out))
print()
print(out["overall_status"].value_counts().to_string())
print()
print("Saved:", OUTPUT)
