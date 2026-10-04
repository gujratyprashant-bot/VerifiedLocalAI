import pandas as pd
import re

CONTEXT = "reports/contextual_evidence.xlsx"
RAW = "reports/targeted_sources.xlsx"
OUTPUT = "reports/strict_evidence_v2.xlsx"

ctx = pd.read_excel(CONTEXT).fillna("")
raw = pd.read_excel(RAW).fillna("")

# Raw content is in targeted_sources.xlsx.
# Contextual evidence contains title/content match information.
KEYS = ["business_name", "title", "url"]

keep_ctx = [
    "business_name",
    "title",
    "url",
    "title_match",
    "content_match"
]

ctx = ctx[[
    c for c in keep_ctx
    if c in ctx.columns
]]

raw = raw[[
    c for c in [
        "business_name",
        "title",
        "url",
        "content"
    ]
    if c in raw.columns
]]

df = raw.merge(
    ctx,
    on=KEYS,
    how="left"
).fillna("")


def norm(x):
    x = str(x).lower()
    x = re.sub(r"\s+", " ", x)
    return x.strip()


def business_tokens(name):

    text = norm(name)
    text = re.sub(
        r"[^a-z0-9 ]",
        " ",
        text
    )

    stop = {
        "restaurant",
        "jaipur",
        "the",
        "and",
        "bar",
        "cafe",
        "kitchen",
        "hotel",
        "road",
        "since",
        "india"
    }

    return {
        x for x in text.split()
        if len(x) >= 3
        and x not in stop
    }


def entity_relevance(
    business,
    title,
    content
):

    tokens = business_tokens(
        business
    )

    title = norm(title)
    content = norm(content)

    if not tokens:
        return 0

    title_hits = sum(
        1 for token in tokens
        if token in title
    )

    content_hits = sum(
        1 for token in tokens
        if token in content
    )

    if title_hits >= min(
        2,
        len(tokens)
    ):
        return 3

    if title_hits >= 1:
        return 2

    if content_hits >= min(
        2,
        len(tokens)
    ):
        return 2

    if content_hits >= 1:
        return 1

    return 0


def extract_address(
    business,
    title,
    content,
    title_match,
    content_match
):

    title = norm(title)
    content = norm(content)

    if not content:
        return ""

    relevance = entity_relevance(
        business,
        title,
        content
    )

    if relevance == 0:
        return ""

    candidates = []

    # Explicit address labels.
    patterns = [

        r"(?:address)\s*[:\-]\s*"
        r"([^.;\n]{15,250})",

        r"(?:located at)\s*[:\-]?\s*"
        r"([^.;\n]{15,250})",

        r"(?:location)\s*[:\-]\s*"
        r"([^.;\n]{15,250})",

        r"(?:situated at)\s*[:\-]?\s*"
        r"([^.;\n]{15,250})",
    ]

    for pattern in patterns:

        for m in re.finditer(
            pattern,
            content,
            re.I
        ):

            candidates.append(
                (
                    m.group(1).strip(),
                    5
                )
            )

    # Structured Indian address.
    address_pattern = (
        r"(?:(?:no\.?|shop|unit|plot|"
        r"house|building)\s*)?"
        r"\d{1,5}"
        r".{0,160}?"
        r"(?:road|marg|nagar|market|circle|"
        r"colony|street|lane|bazar|bazaar|"
        r"johari|mi road|tonk road|ajmer road)"
        r".{0,120}?"
        r"(?:jaipur|rajasthan|302\d{3})"
    )

    for m in re.finditer(
        address_pattern,
        content,
        re.I
    ):

        candidates.append(
            (
                m.group(0).strip(),
                4
            )
        )

    # Address-like phrase containing Jaipur.
    location_pattern = (
        r".{0,100}"
        r"(?:road|marg|nagar|market|circle|"
        r"colony|street|lane|bazar|bazaar)"
        r".{0,140}"
        r"jaipur"
        r".{0,80}"
    )

    for m in re.finditer(
        location_pattern,
        content,
        re.I
    ):

        value = m.group(0).strip()

        # "near X" alone is weak evidence.
        if value.startswith("near "):
            continue

        candidates.append(
            (
                value,
                3
            )
        )

    if not candidates:
        return ""

    scored = []

    for value, base_score in candidates:

        value_norm = norm(value)

        score = base_score

        if "jaipur" in value_norm:
            score += 2

        if "rajasthan" in value_norm:
            score += 1

        if re.search(
            r"\b302\d{3}\b",
            value_norm
        ):
            score += 2

        components = [
            "road",
            "marg",
            "nagar",
            "market",
            "circle",
            "colony",
            "street",
            "lane",
            "bazar",
            "bazaar"
        ]

        component_count = sum(
            1
            for c in components
            if c in value_norm
        )

        if component_count >= 2:
            score += 2

        if title_match in (
            "EXACT",
            "ALL_TOKENS"
        ):
            score += 2

        scored.append(
            (
                score,
                value[:300]
            )
        )

    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )

    best_score, best_value = scored[0]

    if best_score < 6:
        return ""

    return best_value


def extract_hours(content):

    content = norm(content)

    if not content:
        return ""

    results = []

    patterns = [

        r"(?:opening hours|business hours|"
        r"restaurant hours|opening time|"
        r"opening times|timings?|hours?)"
        r"\s*[:\-]\s*([^.;\n]{5,120})",

        r"(?:open(?:s)?|closed)"
        r"\s+(?:from|at|daily)?\s*"
        r"([^.;\n]{5,120})"
    ]

    for pattern in patterns:

        for m in re.finditer(
            pattern,
            content,
            re.I
        ):

            value = m.group(1).strip()

            if re.search(
                r"\d{1,2}"
                r"(?::\d{2})?"
                r"\s*(?:am|pm)",
                value,
                re.I
            ):
                results.append(
                    value[:150]
                )

    range_pattern = (
        r"\b\d{1,2}"
        r"(?::\d{2})?\s*(?:am|pm)"
        r"\s*(?:-|to|–|—)\s*"
        r"\d{1,2}"
        r"(?::\d{2})?\s*(?:am|pm)\b"
    )

    results += re.findall(
        range_pattern,
        content,
        re.I
    )

    clean = []

    for x in results:

        x = re.sub(
            r"\s+",
            " ",
            x
        ).strip()

        if x and x not in clean:
            clean.append(x)

    return " | ".join(
        clean[:3]
    )


def extract_phone(content):

    matches = re.findall(
        r"(?:\+?91[\s\-]?)?"
        r"(?:\d[\s\-]?){10,12}",
        str(content)
    )

    values = []

    for x in matches:

        digits = re.sub(
            r"\D",
            "",
            x
        )

        if (
            digits.startswith("91")
            and len(digits) > 10
        ):
            digits = digits[-10:]

        if len(digits) == 10:
            values.append(digits)

    return "|".join(
        sorted(set(values))
    )


def extract_email(content):

    matches = re.findall(
        r"[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        str(content).lower()
    )

    return "|".join(
        sorted(set(matches))
    )


rows = []

for _, r in df.iterrows():

    business = str(
        r["business_name"]
    )

    title = str(
        r["title"]
    )

    content = str(
        r["content"]
    )

    title_match = str(
        r.get("title_match", "")
    )

    content_match = str(
        r.get("content_match", "")
    )

    relevance = entity_relevance(
        business,
        title,
        content
    )

    rows.append({

        "business_name":
            business,

        "title":
            title,

        "url":
            r["url"],

        "title_match":
            title_match,

        "content_match":
            content_match,

        "entity_relevance":
            relevance,

        "strict_phone":
            extract_phone(
                content
            ),

        "strict_address":
            extract_address(
                business,
                title,
                content,
                title_match,
                content_match
            ),

        "strict_hours":
            extract_hours(
                content
            ),

        "strict_email":
            extract_email(
                content
            )
    })


out = pd.DataFrame(
    rows
)

out.to_excel(
    OUTPUT,
    index=False
)

print()
print("==============================")
print("STRICT EVIDENCE V2")
print("==============================")
print()

print(
    "Records:",
    len(out)
)

print(
    "Businesses:",
    out["business_name"].nunique()
)

print()

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
        ":",
        count
    )

print()

print(
    "Entity relevance:"
)

print(
    out["entity_relevance"]
    .value_counts()
    .sort_index()
)

print()

print(
    "Saved:",
    OUTPUT
)
