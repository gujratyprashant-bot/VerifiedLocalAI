import pandas as pd
import re

INPUT = "reports/evidence_extraction.xlsx"
OUTPUT = "reports/verification_comparison.xlsx"

df = pd.read_excel(INPUT)

FIELDS = ["phone", "address", "hours", "email"]


def normalize(value, field):
    if pd.isna(value):
        return ""

    value = str(value).lower().strip()

    if not value:
        return ""

    if field == "phone":
        # Keep digits only
        digits = re.sub(r"\D", "", value)

        # Normalize Indian +91 numbers
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]

        return digits

    if field == "email":
        return value.strip()

    # General text normalization
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


records = []

for business, group in df.groupby("business_name"):

    for field in FIELDS:

        values = []

        for _, row in group.iterrows():

            raw = row.get(field, "")
            normalized = normalize(raw, field)

            if normalized:
                values.append({
                    "value": raw,
                    "normalized": normalized,
                    "url": row.get("source_url", ""),
                    "domain": row.get("domain", "")
                })

        if not values:
            records.append({
                "business_name": business,
                "field": field,
                "value": "",
                "source_count": 0,
                "status": "MISSING",
                "source_domains": ""
            })
            continue

        # Count normalized values
        counts = {}

        for item in values:
            key = item["normalized"]

            if key not in counts:
                counts[key] = {
                    "count": 0,
                    "domains": set(),
                    "raw": item["value"]
                }

            counts[key]["count"] += 1

            domain = str(item["domain"]).strip()

            if domain:
                counts[key]["domains"].add(domain)

        # Sort by evidence count
        ranked = sorted(
            counts.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )

        unique_values = len(ranked)

        for normalized_value, info in ranked:

            count = info["count"]

            if unique_values == 1 and count >= 2:
                status = "MATCH"

            elif unique_values == 1 and count == 1:
                status = "SINGLE_SOURCE"

            else:
                status = "CONFLICT"

            records.append({
                "business_name": business,
                "field": field,
                "value": info["raw"],
                "source_count": count,
                "status": status,
                "source_domains": ", ".join(
                    sorted(info["domains"])
                )
            })


out = pd.DataFrame(records)

# -------------------------------------------------
# Business-level summary
# -------------------------------------------------

summary = []

for business, group in out.groupby("business_name"):

    statuses = group["status"].tolist()

    if "CONFLICT" in statuses:
        overall = "CONFLICT_PRESENT"

    elif all(
        s in ["MATCH", "MISSING"]
        for s in statuses
    ) and "MATCH" in statuses:
        overall = "CONSISTENT_EVIDENCE"

    elif "SINGLE_SOURCE" in statuses:
        overall = "PARTIAL_EVIDENCE"

    else:
        overall = "INSUFFICIENT_EVIDENCE"

    summary.append({
        "business_name": business,
        "overall_status": overall
    })


summary_df = pd.DataFrame(summary)

# Add overall status to every field row
out = out.merge(
    summary_df,
    on="business_name",
    how="left"
)

# Save both sheets
with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
    out.to_excel(
        writer,
        sheet_name="Field_Evidence",
        index=False
    )

    summary_df.to_excel(
        writer,
        sheet_name="Business_Summary",
        index=False
    )

print()
print("==============================")
print("VERIFICATION COMPARISON DONE")
print("==============================")

print()
print("Businesses:", len(summary_df))
print()
print(summary_df["overall_status"].value_counts().to_string())

print()
print("Saved:", OUTPUT)
