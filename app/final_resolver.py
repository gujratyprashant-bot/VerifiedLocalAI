import pandas as pd
import re

INPUT = "reports/contextual_evidence.xlsx"
OUTPUT = "reports/final_web_verification.xlsx"

df = pd.read_excel(INPUT).fillna("")

FIELDS = {
    "phone": "phone_snippet",
    "address": "address_snippet",
    "hours": "hours_snippet",
    "email": "email_snippet"
}

SOURCE_WEIGHTS = {
    "OFFICIAL_FIRST_PARTY": 5,
    "DIRECTORY": 3,
    "LIST_ARTICLE": 2,
    "SOCIAL_OR_VIDEO": 1,
    "OTHER": 1
}

def norm(text):
    text = str(text).lower()
    return re.sub(r"[^a-z0-9]", "", text)

def field_value(snippet):
    return norm(snippet)

def relevance_score(title_match, content_match):
    scores = {
        "EXACT": 1.0,
        "ALL_TOKENS": 0.9,
        "PARTIAL": 0.5,
        "NONE": 0.0
    }

    return max(
        scores.get(title_match, 0),
        scores.get(content_match, 0)
    )

def source_score(source_type):
    return SOURCE_WEIGHTS.get(source_type, 1)

def classify_field(group, snippet_column):

    evidence = []

    for _, r in group.iterrows():

        snippet = str(r.get(snippet_column, "")).strip()

        if not snippet:
            continue

        relevance = relevance_score(
            r.get("title_match", ""),
            r.get("content_match", "")
        )

        if relevance == 0:
            continue

        source_type = str(r.get("source_type", "OTHER"))

        value = field_value(snippet)

        if not value:
            continue

        score = source_score(source_type) * relevance

        evidence.append({
            "value": value,
            "snippet": snippet,
            "source_type": source_type,
            "url": r.get("url", ""),
            "relevance": relevance,
            "score": score
        })

    if not evidence:
        return {
            "status": "NO_EVIDENCE",
            "best": "",
            "score": 0,
            "sources": "",
            "evidence": ""
        }

    grouped = {}

    for e in evidence:
        grouped.setdefault(e["value"], []).append(e)

    rankings = []

    for value, items in grouped.items():

        total_score = sum(x["score"] for x in items)

        has_first_party = any(
            x["source_type"] == "OFFICIAL_FIRST_PARTY"
            for x in items
        )

        rankings.append({
            "value": value,
            "items": items,
            "score": total_score,
            "first_party": has_first_party
        })

    rankings.sort(
        key=lambda x: (
            x["first_party"],
            x["score"]
        ),
        reverse=True
    )

    winner = rankings[0]

    distinct = len(rankings)

    if distinct == 1:

        if winner["first_party"]:
            status = "SUPPORTED_BY_FIRST_PARTY"
        elif len(winner["items"]) >= 2:
            status = "SUPPORTED_BY_SECONDARY"
        else:
            status = "SINGLE_RELEVANT_SOURCE"

    else:

        if winner["first_party"]:
            status = "FIRST_PARTY_VS_SECONDARY"

        else:
            status = "UNRESOLVED_CONFLICT"

    source_types = sorted(
        set(x["source_type"] for x in winner["items"])
    )

    snippets = []

    for x in winner["items"][:3]:

        snippets.append(
            f"[{x['source_type']}] {x['snippet']}"
        )

    return {
        "status": status,
        "best": winner["items"][0]["snippet"],
        "score": round(winner["score"], 2),
        "sources": ", ".join(source_types),
        "evidence": "\n".join(snippets)
    }


results = []

for business, group in df.groupby("business_name"):

    row = {
        "business_name": business
    }

    statuses = []

    for field, snippet_column in FIELDS.items():

        result = classify_field(
            group,
            snippet_column
        )

        row[field + "_status"] = result["status"]
        row[field + "_score"] = result["score"]
        row[field + "_sources"] = result["sources"]
        row[field + "_evidence"] = result["evidence"]

        statuses.append(result["status"])

    # Overall status
    if "FIRST_PARTY_VS_SECONDARY" in statuses:
        overall = "REVIEW_FIRST_PARTY_CONFLICT"

    elif "UNRESOLVED_CONFLICT" in statuses:
        overall = "UNRESOLVED_CONFLICT"

    elif "SUPPORTED_BY_FIRST_PARTY" in statuses:
        overall = "WEB_SUPPORTED"

    elif "SUPPORTED_BY_SECONDARY" in statuses:
        overall = "SECONDARY_SUPPORTED"

    elif "SINGLE_RELEVANT_SOURCE" in statuses:
        overall = "SINGLE_SOURCE"

    else:
        overall = "INSUFFICIENT_WEB_EVIDENCE"

    row["overall_status"] = overall

    # Ground verification intentionally remains separate.
    row["ground_verification"] = "NOT_PHYSICALLY_VERIFIED"

    results.append(row)


out = pd.DataFrame(results)

out.to_excel(
    OUTPUT,
    index=False
)

print()
print("==============================")
print("FINAL WEB VERIFICATION")
print("==============================")
print()

print("Businesses:", len(out))

print()
print("Overall status:")
print(
    out["overall_status"]
    .value_counts()
    .to_string()
)

print()
print("Ground verification:")
print(
    out["ground_verification"]
    .value_counts()
    .to_string()
)

print()
print("Saved:", OUTPUT)
