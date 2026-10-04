import pandas as pd
import re

INPUT = "reports/targeted_sources.xlsx"
OUTPUT = "reports/contextual_evidence.xlsx"

df = pd.read_excel(INPUT).fillna("")

FIELDS = {
    "phone": r"(?:\+?91[\s\-]?)?(?:\d[\s\-]?){10,12}",
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "hours": r"(?i)(?:open(?:ing)?|hours?|timings?|timing|closed)[^.\n]{0,180}",
    "address": r"(?i)(?:address|located|location|situated|road|marg|street|near)[^.\n]{0,220}"
}

def norm(s):
    s = str(s).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def tokens(name):
    stop = {
        "restaurant", "restaurants", "hotel", "hotels",
        "cafe", "bar", "jaipur", "the", "and"
    }

    return [
        x for x in norm(name).split()
        if len(x) >= 3 and x not in stop
    ]

def title_match(name, title):
    n = norm(name)
    t = norm(title)

    if n and n in t:
        return "EXACT"

    ts = tokens(name)

    if not ts:
        return "NONE"

    matched = sum(x in t for x in ts)

    if matched == len(ts):
        return "ALL_TOKENS"

    if matched >= max(1, len(ts) // 2):
        return "PARTIAL"

    return "NONE"

def content_match(name, content):
    text = norm(content)
    n = norm(name)

    if n and n in text:
        return "EXACT"

    ts = tokens(name)

    if not ts:
        return "NONE"

    matched = sum(x in text for x in ts)

    if matched == len(ts):
        return "ALL_TOKENS"

    if matched >= max(1, len(ts) // 2):
        return "PARTIAL"

    return "NONE"

def get_snippet(text, pattern, radius=180):
    text = str(text)

    try:
        m = re.search(pattern, text)
    except:
        return ""

    if not m:
        return ""

    start = max(0, m.start() - radius)
    end = min(len(text), m.end() + radius)

    snippet = text[start:end]
    snippet = re.sub(r"\s+", " ", snippet)

    return snippet.strip()

rows = []

for _, r in df.iterrows():

    business = str(r["business_name"])
    title = str(r.get("title", ""))
    url = str(r.get("url", ""))
    content = str(r.get("content", ""))

    rows.append({
        "business_name": business,
        "title": title,
        "url": url,

        "title_match": title_match(
            business,
            title
        ),

        "content_match": content_match(
            business,
            content
        ),

        "phone_snippet": get_snippet(
            content,
            FIELDS["phone"]
        ),

        "email_snippet": get_snippet(
            content,
            FIELDS["email"]
        ),

        "hours_snippet": get_snippet(
            content,
            FIELDS["hours"]
        ),

        "address_snippet": get_snippet(
            content,
            FIELDS["address"]
        )
    })

out = pd.DataFrame(rows)

out.to_excel(
    OUTPUT,
    index=False
)

print()
print("==============================")
print("CONTEXTUAL EVIDENCE")
print("==============================")
print()

print("Source records:", len(out))
print("Businesses:", out["business_name"].nunique())

print()
print("Title match:")
print(
    out["title_match"]
    .value_counts()
    .to_string()
)

print()
print("Content match:")
print(
    out["content_match"]
    .value_counts()
    .to_string()
)

print()
print("Evidence snippets:")
print(
    "Phone:", (out["phone_snippet"] != "").sum()
)
print(
    "Address:", (out["address_snippet"] != "").sum()
)
print(
    "Hours:", (out["hours_snippet"] != "").sum()
)
print(
    "Email:", (out["email_snippet"] != "").sum()
)

print()
print("Saved:", OUTPUT)
