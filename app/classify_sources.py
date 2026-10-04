import pandas as pd
from urllib.parse import urlparse

INPUT = "reports/discovered_sources.xlsx"
OUTPUT = "reports/classified_sources.xlsx"

df = pd.read_excel(INPUT)

def classify(row):
    url = str(row.get("url", "")).lower()
    title = str(row.get("title", "")).lower()

    domain = urlparse(url).netloc.replace("www.", "")

    # First-party / official business or hotel source
    official_domains = [
        "tajhotels.com",
        "ihcltata.com",
    ]

    if any(d in domain for d in official_domains):
        return "OFFICIAL_FIRST_PARTY"

    # Directories
    directory_domains = [
        "zomato.com",
        "tripadvisor.in",
        "tripadvisor.com",
        "swiggy.com",
        "eazydiner.com",
        "dineout.co.in",
    ]

    if any(d in domain for d in directory_domains):
        return "DIRECTORY"

    # Social/video
    social_domains = [
        "youtube.com",
        "youtu.be",
        "instagram.com",
        "facebook.com",
        "tiktok.com",
    ]

    if any(d in domain for d in social_domains):
        return "SOCIAL_OR_VIDEO"

    # Articles / list pages
    article_words = [
        "best restaurants",
        "restaurants in",
        "places to eat",
        "guide",
        "top restaurants",
        "legendary",
        "where to eat",
    ]

    if any(word in title for word in article_words):
        return "LIST_ARTICLE"

    return "OTHER"


df["source_type"] = df.apply(classify, axis=1)

df.to_excel(OUTPUT, index=False)

print("\nSource classification:")
print(df["source_type"].value_counts().to_string())

print("\nDetailed:")
print(df[["title", "url", "source_type"]].to_string(index=False))

print(f"\nSaved: {OUTPUT}")
