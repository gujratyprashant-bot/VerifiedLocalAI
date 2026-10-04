import pandas as pd
import re

INPUT = "reports/contextual_evidence.xlsx"
OUTPUT = "reports/strict_evidence.xlsx"

df = pd.read_excel(INPUT).fillna("")

def normalize(text):
    text = str(text).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def strict_address(text, business):
    text = normalize(text)

    if not text:
        return ""

    # A useful address should contain at least one
    # location indicator AND some business/location context.
    address_patterns = [
        r"(?:address)\s*[:\-]\s*([^.;\n]{10,250})",
        r"(?:located at)\s*[:\-]?\s*([^.;\n]{10,250})",
        r"(?:location)\s*[:\-]\s*([^.;\n]{10,250})",
        r"(?:situated at)\s*[:\-]?\s*([^.;\n]{10,250})",
    ]

    for pattern in address_patterns:

        m = re.search(
            pattern,
            text,
            re.I
        )

        if m:

            value = m.group(1).strip()

            # Reject extremely generic snippets.
            if len(value) >= 10:
                return value[:300]

    # Look for Indian address indicators.
    indicators = [
        "road",
        "marg",
        "nagar",
        "market",
        "circle",
        "square",
        "jaipur",
        "rajasthan",
        "lane",
        "street",
        "fort",
        "colony",
        "sector",
        "near"
    ]

    matches = []

    for indicator in indicators:

        for m in re.finditer(
            r".{0,80}\b" +
            re.escape(indicator) +
            r"\b.{0,150}",
            text,
            re.I
        ):

            snippet = m.group(0).strip()

            # Reject very short/generic snippets.
            if len(snippet) >= 30:

                matches.append(snippet)

    if not matches:
        return ""

    # Prefer snippets containing Jaipur/Rajasthan
    # or multiple address indicators.
    matches.sort(
        key=lambda x: (
            ("jaipur" in x),
            ("rajasthan" in x),
            len(x)
        ),
        reverse=True
    )

    return matches[0][:300]


def strict_hours(text):
    text = normalize(text)

    if not text:
        return ""

    patterns = [
        r"(?:opening hours|business hours|restaurant hours|timings?|hours?)\s*[:\-]\s*([^.;\n]{5,120})",
        r"(?:open(?:s)?|closed)\s+(?:from|at|daily)?\s*([^.;\n]{5,120})",
    ]

    for pattern in patterns:

        m = re.search(
            pattern,
            text,
            re.I
        )

        if m:

            value = m.group(1).strip()

            # Hours should normally contain a time signal.
            if re.search(
                r"\d{1,2}(?::\d{2})?\s*(?:am|pm)?",
                value,
                re.I
            ):
                return value[:180]

    # Fallback: detect actual time ranges.
    time_pattern = (
        r"\b\d{1,2}(?::\d{2})?\s*"
        r"(?:am|pm)"
        r"\s*(?:-|to|–|—)\s*"
        r"\d{1,2}(?::\d{2})?\s*"
        r"(?:am|pm)\b"
    )

    matches = re.findall(
        time_pattern,
        text,
        re.I
    )

    if matches:
        return " | ".join(
            sorted(set(matches))
        )[:180]

    return ""


def strict_phone(text):
    text = str(text)

    matches = re.findall(
        r"(?:\+?91[\s\-]?)?"
        r"(?:\d[\s\-]?){10,12}",
        text
    )

    values = []

    for match in matches:

        digits = re.sub(
            r"\D",
            "",
            match
        )

        if digits.startswith("91") and len(digits) > 10:
            digits = digits[-10:]

        if len(digits) == 10:
            values.append(digits)

    return "|".join(
        sorted(set(values))
    )


def strict_email(text):
    matches = re.findall(
        r"[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        str(text).lower()
    )

    return "|".join(
        sorted(set(matches))
    )


rows = []

for _, r in df.iterrows():

    business = str(r["business_name"])

    address_raw = str(
        r.get("address_snippet", "")
    )

    hours_raw = str(
        r.get("hours_snippet", "")
    )

    phone_raw = str(
        r.get("phone_snippet", "")
    )

    email_raw = str(
        r.get("email_snippet", "")
    )

    rows.append({
        "business_name": business,
        "title": r["title"],
        "url": r["url"],
        "title_match": r["title_match"],
        "content_match": r["content_match"],

        "strict_phone": strict_phone(
            phone_raw
        ),

        "strict_address": strict_address(
            address_raw,
            business
        ),

        "strict_hours": strict_hours(
            hours_raw
        ),

        "strict_email": strict_email(
            email_raw
        )
    })


out = pd.DataFrame(rows)

out.to_excel(
    OUTPUT,
    index=False
)

print()
print("==============================")
print("STRICT EVIDENCE")
print("==============================")
print()

print("Records:", len(out))
print("Businesses:", out["business_name"].nunique())

for field in [
    "strict_phone",
    "strict_address",
    "strict_hours",
    "strict_email"
]:

    count = (
        out[field]
        .astype(str)
        .str.strip()
        .ne("")
        .sum()
    )

    print(
        field,
        ":", count
    )

print()
print("Saved:", OUTPUT)
