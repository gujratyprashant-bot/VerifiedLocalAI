import pandas as pd

INPUT = "reports/evidence_with_source_type.xlsx"
OUTPUT = "reports/conflict_evidence.xlsx"

df = pd.read_excel(INPUT).fillna("")

fields = ["phone", "address", "hours", "email"]

def clean(v):
    return str(v).strip()

rows = []

for business, group in df.groupby("business_name"):

    for field in fields:

        evidence = []

        for _, r in group.iterrows():
            value = clean(r.get(field, ""))

            if not value:
                continue

            evidence.append({
                "business_name": business,
                "field": field,
                "value": value,
                "source_type": r["source_type"],
                "url": r["source_url"]
            })

        if len(evidence) < 2:
            continue

        # Different normalized values
        normalized = set()

        for e in evidence:
            v = e["value"].lower()
            v = "".join(c for c in v if c.isalnum())
            normalized.add(v)

        if len(normalized) > 1:

            for e in evidence:
                rows.append({
                    "business_name": e["business_name"],
                    "field": e["field"],
                    "value": e["value"],
                    "source_type": e["source_type"],
                    "url": e["url"]
                })


out = pd.DataFrame(rows)

if out.empty:
    print("No conflicts found.")
else:
    out.to_excel(OUTPUT, index=False)

    print()
    print("==============================")
    print("CONFLICT EVIDENCE REPORT")
    print("==============================")
    print()
    print("Conflict evidence rows:", len(out))
    print("Businesses affected:", out["business_name"].nunique())
    print()
    print("By field:")
    print(out["field"].value_counts().to_string())
    print()
    print("By source type:")
    print(out["source_type"].value_counts().to_string())
    print()
    print("Saved:", OUTPUT)
