import pandas as pd
import re
from urllib.parse import urlparse

INPUT = "reports/targeted_sources.xlsx"
OUTPUT = "reports/clean_field_evidence_v11.xlsx"


def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def domain(url):
    try:
        return urlparse(
            clean(url)
        ).netloc.lower().replace("www.", "")
    except:
        return ""


def normalize_phone(value):

    digits = re.sub(
        r"\D",
        "",
        value
    )

    if digits.startswith("91") and len(digits) >= 12:
        digits = digits[-10:]

    if len(digits) == 10:
        if digits[0] in "6789":
            return digits

    return ""


def extract_phones(text):

    text = clean(text)

    patterns = [
        r"\+91[\s\-()]*(\d{5})[\s\-]?(\d{5})",
        r"\b91[\s\-]?(\d{5})[\s\-]?(\d{5})\b",
        r"\b([6-9]\d{4})[\s\-]?(\d{5})\b"
    ]

    found = []

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text
        ):

            value = "".join(
                match.groups()
            )

            value = normalize_phone(
                value
            )

            if value:
                found.append(value)

    return sorted(set(found))


def extract_hours(text):

    text = clean(text)

    patterns = [

        # 7:00 AM - 11:00 PM
        r"\b\d{1,2}:\d{2}\s*(?:am|pm)"
        r"\s*[-–—to]+\s*"
        r"\d{1,2}:\d{2}\s*(?:am|pm)\b",

        # 7 AM - 11 PM
        r"\b\d{1,2}\s*(?:am|pm)"
        r"\s*[-–—to]+\s*"
        r"\d{1,2}\s*(?:am|pm)\b",

        # opens at 11am
        r"\b(?:opens?|opening)\s+at\s+"
        r"\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",

        # open till 11pm
        r"\bopen\s+(?:till|until)\s+"
        r"\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",

        # monday: 10:00 am to 11:00 pm
        r"\b(?:monday|tuesday|wednesday|thursday|"
        r"friday|saturday|sunday)\s*[:\-]\s*"
        r"\d{1,2}(?::\d{2})?\s*(?:am|pm)"
        r"\s*(?:to|-)\s*"
        r"\d{1,2}(?::\d{2})?\s*(?:am|pm)\b"
    ]

    found = []

    lower = text.lower()

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            lower
        ):

            value = match.group(0)

            # Reject obvious non-hours fragments
            if len(value) > 100:
                continue

            found.append(
                re.sub(
                    r"\s+",
                    " ",
                    value
                ).strip()
            )

    return sorted(set(found))


def extract_emails(text):

    text = clean(text)

    pattern = (
        r"\b[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+\."
        r"[A-Za-z]{2,}\b"
    )

    return sorted(
        set(
            re.findall(
                pattern,
                text
            )
        )
    )


def extract_addresses(text):

    text = clean(text)

    # Keep address extraction conservative.
    patterns = [

        r"\b\d{1,5}\s*,?\s*"
        r"[A-Za-z][A-Za-z .'-]{2,50}"
        r"\s+(?:road|rd|marg|street|st)"
        r"(?:\s*,[^.\n]{0,100})?",

        r"\b(?:shop|plot|house|khasra|floor)"
        r"\s*(?:no\.?|number)?\s*\d{1,5}"
        r"(?:[^.\n]{0,120})"
        r"\b(?:jaipur|rajasthan)\b",

        r"\b(?:mi road|m\.i\. road|mirza ismail road)"
        r"(?:[^.\n]{0,80})"
        r"\bjaipur\b",

        r"\b(?:bapu bazar|nehru bazar|"
        r"station road|tonk road|"
        r"jawahar lal nehru marg|"
        r"jawahar kala kendra|"
        r"jamdoli agra road)"
        r"(?:[^.\n]{0,100})"
        r"\bjaipur\b"
    ]

    found = []

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text,
            flags=re.I
        ):

            value = re.sub(
                r"\s+",
                " ",
                match.group(0)
            ).strip()

            if len(value) < 8:
                continue

            if len(value) > 180:
                continue

            found.append(value)

    return sorted(
        set(found)
    )


def context_score(
    business,
    value,
    content
):

    business_tokens = set(
        x.lower()
        for x in re.findall(
            r"[A-Za-z]{3,}",
            business
        )
    )

    value_tokens = set(
        x.lower()
        for x in re.findall(
            r"[A-Za-z]{3,}",
            value
        )
    )

    content_lower = content.lower()

    score = 0

    # Business appears near the evidence
    for token in business_tokens:

        if token in content_lower:
            score += 1

    # Jaipur context
    if "jaipur" in value.lower():
        score += 2

    # Strong address context
    if any(
        x in value.lower()
        for x in [
            "road",
            "rd",
            "marg",
            "bazar",
            "circle",
            "nagar",
            "jaipur"
        ]
    ):
        score += 1

    return score


df = pd.read_excel(INPUT)

records = []

for _, row in df.iterrows():

    business = clean(
        row.get(
            "business_name",
            ""
        )
    )

    title = clean(
        row.get(
            "title",
            ""
        )
    )

    url = clean(
        row.get(
            "url",
            ""
        )
    )

    content = clean(
        row.get(
            "content",
            ""
        )
    )

    d = domain(url)

    phones = extract_phones(
        content
    )

    hours = extract_hours(
        content
    )

    emails = extract_emails(
        content
    )

    addresses = extract_addresses(
        content
    )

    if not phones:
        phones = [""]

    if not hours:
        hours = [""]

    if not emails:
        emails = [""]

    if not addresses:
        addresses = [""]


    max_len = max(
        len(phones),
        len(hours),
        len(emails),
        len(addresses)
    )


    for i in range(max_len):

        phone = (
            phones[i]
            if i < len(phones)
            else ""
        )

        hour = (
            hours[i]
            if i < len(hours)
            else ""
        )

        email = (
            emails[i]
            if i < len(emails)
            else ""
        )

        address = (
            addresses[i]
            if i < len(addresses)
            else ""
        )


        evidence_value = (
            address
            or phone
            or hour
            or email
        )

        records.append({

            "business_name":
                business,

            "source_title":
                title,

            "source_url":
                url,

            "domain":
                d,

            "phone":
                phone,

            "address":
                address,

            "hours":
                hour,

            "email":
                email,

            "context_score":
                context_score(
                    business,
                    evidence_value,
                    content
                ),

            "content_length":
                len(content)
        })


out = pd.DataFrame(records)

out.to_excel(
    OUTPUT,
    index=False
)


print("=" * 70)
print("CLEAN FIELD EVIDENCE V11")
print("=" * 70)

print()
print("Source records:", len(df))
print("Evidence rows:", len(out))

print()
print(
    "PHONE FOUND:",
    (out["phone"] != "").sum()
)

print(
    "ADDRESS FOUND:",
    (out["address"] != "").sum()
)

print(
    "HOURS FOUND:",
    (out["hours"] != "").sum()
)

print(
    "EMAIL FOUND:",
    (out["email"] != "").sum()
)

print()
print("Businesses:",
      out["business_name"].nunique())

print()
print("Saved:", OUTPUT)
