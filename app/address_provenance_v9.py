import pandas as pd
import re
from urllib.parse import urlparse

TARGETED = "reports/targeted_sources.xlsx"
STRICT = "reports/strict_evidence_v2.xlsx"
V8 = "reports/address_final_v8.xlsx"
OUTPUT = "reports/address_provenance_v9.xlsx"


def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def norm(x):
    x = clean(x).lower()

    aliases = {
        "m.i. road": "mirza ismail road",
        "m i road": "mirza ismail road",
        "mi road": "mirza ismail road",
        "mirza ismail rd": "mirza ismail road",
        "marg": "road",
        "bazar": "bazar",
    }

    x = re.sub(r"[^a-z0-9 ]+", " ", x)
    x = re.sub(r"\s+", " ", x).strip()

    for a, b in aliases.items():
        x = x.replace(a, b)

    x = re.sub(r"\s+", " ", x).strip()

    return x


def domain(url):
    try:
        d = urlparse(clean(url)).netloc.lower()
        d = d.replace("www.", "")
        return d
    except:
        return ""


def address_tokens(x):
    stop = {
        "jaipur", "rajasthan", "india",
        "restaurant", "hotel", "the",
        "road", "rd", "marg"
    }

    return set(
        t for t in norm(x).split()
        if len(t) >= 3 and t not in stop
    )


def similarity(a, b):

    aa = address_tokens(a)
    bb = address_tokens(b)

    if not aa or not bb:
        return 0

    return len(aa & bb) / max(
        len(aa | bb), 1
    )


print("=" * 70)
print("ADDRESS PROVENANCE V9")
print("=" * 70)


targeted = pd.read_excel(TARGETED)
strict = pd.read_excel(STRICT)
v8 = pd.read_excel(V8)

print()
print("Targeted records:", len(targeted))
print("Strict records:", len(strict))
print("V8 locations:", len(v8))


# ---------------------------------------------------------
# Build source index
# ---------------------------------------------------------

source_records = []

for _, r in targeted.iterrows():

    business = clean(
        r.get("business_name", "")
    )

    title = clean(
        r.get("title", "")
    )

    url = clean(
        r.get("url", "")
    )

    content = clean(
        r.get("content", "")
    )

    source_records.append({
        "business_name": business,
        "title": title,
        "url": url,
        "domain": domain(url),
        "content": content,
        "address_text":
            content.lower()
    })


sources = pd.DataFrame(source_records)


# ---------------------------------------------------------
# Pull strict address evidence where available
# ---------------------------------------------------------

strict_cols = set(strict.columns)

strict_address_col = None

for candidate in [
    "strict_address",
    "address",
    "address_evidence"
]:

    if candidate in strict_cols:
        strict_address_col = candidate
        break


strict_rows = []

if strict_address_col:

    for _, r in strict.iterrows():

        addr = clean(
            r.get(strict_address_col, "")
        )

        if not addr:
            continue

        strict_rows.append({
            "business_name":
                clean(r.get(
                    "business_name", ""
                )),
            "title":
                clean(r.get("title", "")),
            "url":
                clean(r.get("url", "")),
            "address":
                addr
        })


strict_addr = pd.DataFrame(
    strict_rows
)


# ---------------------------------------------------------
# Match V8 representative locations against evidence
# ---------------------------------------------------------

provenance = []


for _, loc in v8.iterrows():

    business = clean(
        loc.get("business_name", "")
    )

    representative = clean(
        loc.get(
            "representative_address",
            ""
        )
    )

    if not representative:
        continue

    candidates = []


    # First use strict evidence when available
    if len(strict_addr):

        business_rows = strict_addr[
            strict_addr["business_name"]
            .str.lower()
            == business.lower()
        ]

        for _, sr in business_rows.iterrows():

            score = similarity(
                representative,
                sr["address"]
            )

            if score >= 0.20:

                candidates.append({
                    "address":
                        sr["address"],
                    "title":
                        sr["title"],
                    "url":
                        sr["url"],
                    "domain":
                        domain(sr["url"]),
                    "match_score":
                        round(score, 3)
                })


    # If strict matching is unavailable,
    # search the raw targeted evidence.
    if not candidates:

        business_rows = sources[
            sources["business_name"]
            .str.lower()
            == business.lower()
        ]

        rep_tokens = address_tokens(
            representative
        )

        for _, sr in business_rows.iterrows():

            content = sr["content"]

            if not content:
                continue

            text_tokens = address_tokens(
                content
            )

            overlap = len(
                rep_tokens & text_tokens
            )

            if overlap >= 2:

                candidates.append({
                    "address":
                        representative,
                    "title":
                        sr["title"],
                    "url":
                        sr["url"],
                    "domain":
                        sr["domain"],
                    "match_score":
                        round(
                            overlap /
                            max(
                                len(rep_tokens),
                                1
                            ),
                            3
                        )
                })


    # -----------------------------------------------------
    # Deduplicate sources
    # -----------------------------------------------------

    unique = {}

    for c in candidates:

        key = (
            c["domain"],
            c["url"]
        )

        unique[key] = c

    candidates = list(
        unique.values()
    )


    domains = sorted(
        set(
            c["domain"]
            for c in candidates
            if c["domain"]
        )
    )

    urls = sorted(
        set(
            c["url"]
            for c in candidates
            if c["url"]
        )
    )


    independent_domains = len(
        domains
    )

    if independent_domains >= 3:

        support = "STRONG_WEB_SUPPORT"

    elif independent_domains == 2:

        support = "SECONDARY_WEB_SUPPORT"

    elif independent_domains == 1:

        support = "SINGLE_SOURCE"

    else:

        support = "NO_SOURCE_MATCH"


    # Multiple domains are useful,
    # but do NOT mean physical verification.
    physical_status = (
        "NOT_PHYSICALLY_VERIFIED"
    )


    provenance.append({

        "business_name":
            business,

        "location_cluster":
            loc.get(
                "location_cluster",
                ""
            ),

        "representative_address":
            representative,

        "address_variants":
            clean(
                loc.get(
                    "address_variants",
                    ""
                )
            ),

        "web_support":
            support,

        "independent_domain_count":
            independent_domains,

        "source_count":
            len(urls),

        "source_domains":
            " | ".join(domains),

        "source_urls":
            " | ".join(urls),

        "physical_verification":
            physical_status,

        "location_status":
            clean(
                loc.get(
                    "location_status",
                    ""
                )
            )
    })


final = pd.DataFrame(
    provenance
)


final.to_excel(
    OUTPUT,
    index=False
)


print()
print("=" * 70)
print("V9 RESULT")
print("=" * 70)

print()
print(
    "Businesses:",
    final["business_name"].nunique()
)

print(
    "Location candidates:",
    len(final)
)

print()
print("WEB SUPPORT")
print(
    final["web_support"]
    .value_counts()
    .to_string()
)

print()
print("INDEPENDENT DOMAINS")
print(
    final[
        final["independent_domain_count"] >= 2
    ][
        [
            "business_name",
            "representative_address",
            "independent_domain_count",
            "source_domains",
            "web_support"
        ]
    ].to_string(index=False)
)

print()
print("PHYSICAL VERIFICATION")
print(
    final["physical_verification"]
    .value_counts()
    .to_string()
)

print()
print("Saved:", OUTPUT)
