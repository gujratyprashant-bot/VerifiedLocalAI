import pandas as pd
import re

INPUT = "reports/classified_sources.xlsx"
OUTPUT = "reports/business_candidates_clean.xlsx"

df = pd.read_excel(INPUT)

candidates = []

def clean_name(name):
    name = str(name)

    # Remove obvious extraction artifacts
    name = re.sub(r"\[\.\.\.\].*$", "", name)
    name = re.sub(r"\[\.\.\.\].*$", "", name)
    name = re.sub(r"\bphone-icon\b.*$", "", name, flags=re.I)
    name = re.sub(r"\bMORE\b.*$", "", name, flags=re.I)
    name = re.sub(r"\bRestaurant Card\b.*$", "", name, flags=re.I)

    name = re.sub(r"\s+", " ", name).strip()
    name = name.strip(" -|#[]")

    return name


def looks_like_business(name):
    n = name.lower().strip()

    if len(n) < 3 or len(n) > 100:
        return False

    # Obvious non-business text
    bad_exact = {
        "features",
        "great for",
        "neighborhood",
        "location",
        "chapters",
        "other restaurants to try in jaipur",
        "jaipur legendary places",
        "welcome to jaipur",
        "final thoughts",
        "more",
    }

    if n in bad_exact:
        return False

    bad_phrases = [
        "final thoughts",
        "other restaurants to try",
        "restaurant card",
        "asiaindiajaipur",
        "phone-icon",
        "the city's distinct",
        "hard to rate restaurants",
    ]

    if any(x in n for x in bad_phrases):
        return False

    # Sentences are usually article text, not names
    if len(n.split()) > 12:
        return False

    # Reject obvious timestamp/metadata
    if re.match(r"^\d+$", n):
        return False

    return True


def add_candidate(name, row):
    name = clean_name(name)

    if not looks_like_business(name):
        return

    candidates.append({
        "business_name": name,
        "city": "Jaipur",
        "source_title": str(row.get("title", "")),
        "source_url": str(row.get("url", "")),
        "source_type": str(row.get("source_type", ""))
    })


for _, row in df.iterrows():

    source_type = str(row.get("source_type", ""))
    content = str(row.get("source_content", ""))

    # -------------------------------------------------
    # OFFICIAL FIRST-PARTY
    # -------------------------------------------------
    if source_type == "OFFICIAL_FIRST_PARTY":

        # Only headings, but clean them carefully
        matches = re.findall(
            r"##\s+([^\n]+)",
            content
        )

        for name in matches:
            add_candidate(name, row)

    # -------------------------------------------------
    # SOCIAL / VIDEO
    # -------------------------------------------------
    elif source_type == "SOCIAL_OR_VIDEO":

        matches = re.findall(
            r"(?:\d{1,2}:\d{2})\s+([A-Za-z0-9][A-Za-z0-9 &'().\-\[\]]{2,80})",
            content
        )

        for name in matches:
            add_candidate(name, row)

    # -------------------------------------------------
    # DIRECTORY
    # -------------------------------------------------
    elif source_type == "DIRECTORY":

        # Zomato restaurant cards
        matches = re.findall(
            r"Restaurant Card#+\s*([^\n]+)",
            content,
            flags=re.I
        )

        for name in matches:
            add_candidate(name, row)

    # -------------------------------------------------
    # LIST ARTICLES
    # -------------------------------------------------
    elif source_type == "LIST_ARTICLE":

        # Markdown headings are much safer than arbitrary text
        matches = re.findall(
            r"##\s+([^\n]+)",
            content
        )

        for name in matches:
            add_candidate(name, row)

        # Also capture common "#### business name" patterns
        matches = re.findall(
            r"####\s+([^\n]+)",
            content
        )

        for name in matches:
            add_candidate(name, row)


# -------------------------------------------------
# Build dataframe
# -------------------------------------------------

out = pd.DataFrame(candidates)

if out.empty:
    print("No candidates extracted.")
    raise SystemExit()

# Normalize
out["normalized_name"] = (
    out["business_name"]
    .str.lower()
    .str.replace(r"[^a-z0-9]+", " ", regex=True)
    .str.strip()
)

# Remove exact normalized duplicates
out = out.drop_duplicates(
    subset=["normalized_name"]
)

# Quality flags
def quality(row):
    name = row["business_name"]
    source_type = row["source_type"]

    score = 0

    if source_type == "OFFICIAL_FIRST_PARTY":
        score += 3
    elif source_type == "DIRECTORY":
        score += 2
    elif source_type == "LIST_ARTICLE":
        score += 1
    elif source_type == "SOCIAL_OR_VIDEO":
        score += 1

    if 3 <= len(name.split()) <= 8:
        score += 1

    return score


out["extraction_score"] = out.apply(quality, axis=1)

out = out.sort_values(
    ["extraction_score", "business_name"],
    ascending=[False, True]
)

out.to_excel(
    OUTPUT,
    index=False
)

print()
print("CLEAN BUSINESS CANDIDATES")
print("=========================")

print(
    out[
        [
            "business_name",
            "source_type",
            "extraction_score"
        ]
    ].to_string(index=False)
)

print()
print("Total candidates:", len(out))
print("Saved:", OUTPUT)
