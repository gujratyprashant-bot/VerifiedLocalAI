import pandas as pd
import re

INPUT = "reports/contextual_evidence.xlsx"
OUTPUT = "reports/normalized_evidence.xlsx"

df = pd.read_excel(INPUT).fillna("")

def normalize_phone(text):
    text = str(text)

    matches = re.findall(
        r"(?:\+?91[\s\-]?)?(?:\d[\s\-]?){10,12}",
        text
    )

    numbers = []

    for m in matches:
        digits = re.sub(r"\D", "", m)

        if digits.startswith("91") and len(digits) > 10:
            digits = digits[-10:]

        if len(digits) == 10:
            numbers.append(digits)

    return "|".join(sorted(set(numbers)))


def normalize_email(text):
    text = str(text).lower()

    matches = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    return "|".join(sorted(set(matches)))


def normalize_hours(text):
    text = str(text).lower()

    # Keep a compact normalized representation.
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9:,\-\s]", "", text)

    return text.strip()[:300]


def normalize_address(text):
    text = str(text).lower()

    # Remove obvious labels.
    text = re.sub(
        r"\b(address|located at|location|situated at)\b\s*:?",
        " ",
        text
    )

    # Normalize common punctuation/spacing.
    text = re.sub(r"[^a-z0-9,\-\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()[:400]


def extract(field, text):

    if not text:
        return ""

    if field == "phone":
        return normalize_phone(text)

    if field == "email":
        return normalize_email(text)

    if field == "hours":
        return normalize_hours(text)

    if field == "address":
        return normalize_address(text)

    return ""


rows = []

for _, r in df.iterrows():

    base = {
        "business_name": r["business_name"],
        "title": r["title"],
        "url": r["url"],
        "title_match": r["title_match"],
        "content_match": r["content_match"]
    }

    for field in ["phone", "address", "hours", "email"]:

        snippet = str(
            r.get(field + "_snippet", "")
        ).strip()

        base[field + "_raw"] = snippet

        base[field + "_normalized"] = extract(
            field,
            snippet
        )

    rows.append(base)


out = pd.DataFrame(rows)

out.to_excel(
    OUTPUT,
    index=False
)

print()
print("==============================")
print("NORMALIZED EVIDENCE")
print("==============================")
print()

print("Records:", len(out))
print("Businesses:", out["business_name"].nunique())

for field in ["phone", "address", "hours", "email"]:

    column = field + "_normalized"

    usable = (
        out[column]
        .astype(str)
        .str.strip()
        .ne("")
        .sum()
    )

    print(
        f"{field.title()} values extracted: {usable}"
    )

print()
print("Saved:", OUTPUT)
