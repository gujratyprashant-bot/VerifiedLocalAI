import pandas as pd

INPUT = "reports/evidence_extraction.xlsx"
SOURCES = "reports/targeted_sources.xlsx"
OUTPUT = "reports/evidence_with_source_type.xlsx"

evidence = pd.read_excel(INPUT)
sources = pd.read_excel(SOURCES)

sources["source_url"] = sources["url"].astype(str).str.strip()
evidence["source_url"] = evidence["source_url"].astype(str).str.strip()

# Source type from targeted source discovery
source_types = (
    sources[
        ["source_url", "business_name"]
    ]
    .drop_duplicates("source_url")
)

def classify_domain(url):
    url = str(url).lower()

    official = [
        "tajhotels.com",
        "ihcltata.com",
        "hotelkalyan.com",
        "oberoihotels.com",
        "itchotels.com",
        "marriott.com",
        "hyatt.com",
        "radissonhotels.com",
        "hilton.com",
    ]

    directories = [
        "zomato.com",
        "tripadvisor.com",
        "tripadvisor.in",
        "swiggy.com",
        "eazydiner.com",
        "dineout.co.in",
    ]

    social = [
        "youtube.com",
        "youtu.be",
        "instagram.com",
        "facebook.com",
    ]

    if any(x in url for x in official):
        return "OFFICIAL_FIRST_PARTY"

    if any(x in url for x in directories):
        return "DIRECTORY"

    if any(x in url for x in social):
        return "SOCIAL_OR_VIDEO"

    return "OTHER"


evidence["source_type"] = evidence["source_url"].apply(
    classify_domain
)

evidence.to_excel(
    OUTPUT,
    index=False
)

print()
print("==============================")
print("SOURCE TYPES ADDED")
print("==============================")

print(evidence["source_type"].value_counts().to_string())

print()
print("Saved:", OUTPUT)
