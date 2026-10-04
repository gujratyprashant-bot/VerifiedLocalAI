import pandas as pd
from collections import defaultdict

INPUT = "reports/normalized_evidence.xlsx"
OUTPUT = "reports/verification_results.xlsx"

df = pd.read_excel(INPUT).fillna("")

SOURCE_WEIGHT = {
    "OFFICIAL_FIRST_PARTY": 5,
    "DIRECTORY": 3,
    "LIST_ARTICLE": 2,
    "SOCIAL_OR_VIDEO": 1,
    "OTHER": 1
}

FIELDS = ["phone", "address", "hours", "email"]


def classify_field(group, field):

    column = field + "_normalized"

    evidence = []

    for _, r in group.iterrows():

        value = str(r.get(column, "")).strip()

        if not value:
            continue

        title_match = str(r.get("title_match", "NONE"))
        content_match = str(r.get("content_match", "NONE"))

        relevance = max(
            {
                "EXACT": 1.0,
                "ALL_TOKENS": 0.9,
                "PARTIAL": 0.5,
                "NONE": 0.0
            }.get(title_match, 0),
            {
                "EXACT": 1.0,
                "ALL_TOKENS": 0.9,
                "PARTIAL": 0.5,
                "NONE": 0.0
            }.get(content_match, 0)
        )

        if relevance == 0:
            continue

        source_type = str(
            r.get("source_type", "OTHER")
        )

        weight = SOURCE_WEIGHT.get(
            source_type,
            1
        )

        evidence.append({
            "value": value,
            "source_type": source_type,
            "weight": weight,
            "relevance": relevance,
            "score": weight * relevance,
            "url": r.get("url", "")
        })

    if not evidence:

        return {
            "status": "NO_EVIDENCE",
            "value": "",
            "score": 0,
            "source_types": "",
            "source_count": 0,
            "conflicting_values": 0
        }

    grouped = defaultdict(list)

    for item in evidence:
        grouped[item["value"]].append(item)

    ranked = []

    for value, items in grouped.items():

        score = sum(
            x["score"]
            for x in items
        )

        first_party = any(
            x["source_type"] ==
            "OFFICIAL_FIRST_PARTY"
            for x in items
        )

        ranked.append({
            "value": value,
            "items": items,
            "score": score,
            "first_party": first_party
        })

    ranked.sort(
        key=lambda x: (
            x["first_party"],
            x["score"],
            len(x["items"])
        ),
        reverse=True
    )

    winner = ranked[0]

    distinct = len(ranked)

    if distinct == 1:

        if winner["first_party"]:
            status = "SUPPORTED_FIRST_PARTY"

        elif len(winner["items"]) >= 2:
            status = "SUPPORTED_SECONDARY"

        else:
            status = "SINGLE_SOURCE"

    else:

        if winner["first_party"]:
            status = "FIRST_PARTY_WITH_CONFLICT"

        else:
            status = "UNRESOLVED_CONFLICT"

    source_types = sorted(
        set(
            x["source_type"]
            for x in winner["items"]
        )
    )

    return {
        "status": status,
        "value": winner["value"],
        "score": round(winner["score"], 2),
        "source_types": ", ".join(source_types),
        "source_count": len(winner["items"]),
        "conflicting_values": distinct
    }


results = []

for business, group in df.groupby(
    "business_name"
):

    row = {
        "business_name": business
    }

    statuses = []

    for field in FIELDS:

        result = classify_field(
            group,
            field
        )

        row[field + "_status"] = (
            result["status"]
        )

        row[field + "_value"] = (
            result["value"]
        )

        row[field + "_score"] = (
            result["score"]
        )

        row[field + "_sources"] = (
            result["source_types"]
        )

        row[field + "_source_count"] = (
            result["source_count"]
        )

        row[field + "_distinct_values"] = (
            result["conflicting_values"]
        )

        statuses.append(
            result["status"]
        )

    if "FIRST_PARTY_WITH_CONFLICT" in statuses:

        overall = "REVIEW_FIRST_PARTY_CONFLICT"

    elif "UNRESOLVED_CONFLICT" in statuses:

        overall = "UNRESOLVED_CONFLICT"

    elif "SUPPORTED_FIRST_PARTY" in statuses:

        overall = "WEB_SUPPORTED_FIRST_PARTY"

    elif "SUPPORTED_SECONDARY" in statuses:

        overall = "WEB_SUPPORTED_SECONDARY"

    elif "SINGLE_SOURCE" in statuses:

        overall = "SINGLE_SOURCE"

    else:

        overall = "INSUFFICIENT_EVIDENCE"

    row["overall_status"] = overall

    row["ground_verification"] = (
        "NOT_PHYSICALLY_VERIFIED"
    )

    results.append(row)


out = pd.DataFrame(results)

out.to_excel(
    OUTPUT,
    index=False
)

print()
print("==============================")
print("NORMALIZED VERIFICATION")
print("==============================")
print()

print("Businesses:", len(out))

print()
print("Overall:")
print(
    out["overall_status"]
    .value_counts()
    .to_string()
)

print()
print("Field results:")

for field in FIELDS:

    print()
    print(field.upper())

    print(
        out[field + "_status"]
        .value_counts()
        .to_string()
    )

print()
print("Saved:", OUTPUT)
