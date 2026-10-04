import pandas as pd
import re

INPUT = "reports/classified_sources.xlsx"
OUTPUT = "reports/business_candidates.xlsx"

df = pd.read_excel(INPUT)

candidates = []

def add_candidate(name, source_title, source_url, source_type):
    name = re.sub(r"\s+", " ", str(name)).strip()
    name = name.strip(" -|#")

    if not name:
        return

    bad = [
        "restaurants in jaipur",
        "the best restaurants",
        "restaurant card",
        "chapters",
        "location",
        "welcome to jaipur",
        "more",
    ]

    if name.lower() in bad:
        return

    candidates.append({
        "business_name": name,
        "city": "Jaipur",
        "source_title": source_title,
        "source_url": source_url,
        "source_type": source_type
    })


for _, row in df.iterrows():

    title = str(row.get("title", ""))
    url = str(row.get("url", ""))
    source_type = str(row.get("source_type", ""))
    content = str(row.get("source_content", ""))

    # Official first-party pages
    if source_type == "OFFICIAL_FIRST_PARTY":

        matches = re.findall(
            r"##\s+([^\n]+)",
            content
        )

        for name in matches:
            add_candidate(
                name,
                title,
                url,
                source_type
            )

    # YouTube / social pages
    elif source_type == "SOCIAL_OR_VIDEO":

        matches = re.findall(
            r"(?:\d{1,2}:\d{2})\s+([A-Za-z0-9][A-Za-z0-9 &'().\-\[\]]{2,80})",
            content
        )

        for name in matches:
            add_candidate(
                name,
                title,
                url,
                source_type
            )

    # Directory / article pages
    else:

        matches = re.findall(
            r"Restaurant Card#+\s*([^\n]+)",
            content,
            flags=re.IGNORECASE
        )

        for name in matches:
            add_candidate(
                name,
                title,
                url,
                source_type
            )

        matches = re.findall(
            r"##\s+([^\n]+)",
            content
        )

        for name in matches:
            add_candidate(
                name,
                title,
                url,
                source_type
            )


out = pd.DataFrame(candidates)

if out.empty:
    print("No candidates extracted.")
    raise SystemExit()

out["normalized_name"] = (
    out["business_name"]
    .str.lower()
    .str.replace(r"[^a-z0-9]+", " ", regex=True)
    .str.strip()
)

out = out.drop_duplicates(
    subset=["normalized_name", "source_type"]
)

source_counts = (
    out.groupby("normalized_name")["source_url"]
    .nunique()
    .rename("source_count")
)

out = out.merge(
    source_counts,
    on="normalized_name",
    how="left"
)

out = out.sort_values(
    ["source_count", "business_name"],
    ascending=[False, True]
)

out.to_excel(OUTPUT, index=False)

print()
print("BUSINESS CANDIDATES")
print("===================")

print(
    out[
        [
            "business_name",
            "source_type",
            "source_count"
        ]
    ].to_string(index=False)
)

print()
print(f"Total candidate records: {len(out)}")
print(f"Unique businesses: {out['normalized_name'].nunique()}")
print()
print(f"Saved: {OUTPUT}")
