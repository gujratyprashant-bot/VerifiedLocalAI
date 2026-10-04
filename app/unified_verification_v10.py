import pandas as pd
import re
from urllib.parse import urlparse
from collections import Counter

EVIDENCE = "reports/evidence_with_source_type.xlsx"
V9 = "reports/address_provenance_v9.xlsx"
OUTPUT = "reports/unified_verification_v10.xlsx"


WEIGHTS = {
    "OFFICIAL_FIRST_PARTY": 5,
    "DIRECTORY": 3,
    "LIST_ARTICLE": 2,
    "SOCIAL_OR_VIDEO": 1,
    "OTHER": 1
}


def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def norm_phone(x):
    digits = re.sub(r"\D", "", clean(x))

    if digits.startswith("91") and len(digits) >= 12:
        digits = digits[-10:]

    if len(digits) == 10:
        return digits

    return ""


def norm_text(x):
    x = clean(x).lower()
    x = re.sub(r"[^a-z0-9 ]+", " ", x)
    x = re.sub(r"\s+", " ", x)
    return x.strip()


def norm_hours(x):
    x = clean(x).lower()

    if not x:
        return ""

    x = x.replace("–", "-")
    x = x.replace("—", "-")
    x = re.sub(r"\s+", " ", x)

    return x.strip()


def source_weight(source_type):
    return WEIGHTS.get(
        clean(source_type),
        1
    )


def unique_domains(rows):

    domains = set()

    for _, r in rows.iterrows():

        url = clean(
            r.get("url", "")
        )

        try:
            d = urlparse(url).netloc.lower()
            d = d.replace("www.", "")

            if d:
                domains.add(d)

        except:
            pass

    return domains


print("=" * 70)
print("UNIFIED VERIFICATION V10")
print("=" * 70)


evidence = pd.read_excel(EVIDENCE)
address = pd.read_excel(V9)


print()
print("Evidence records:", len(evidence))
print("Address candidates:", len(address))


# ---------------------------------------------------------
# Detect evidence columns
# ---------------------------------------------------------

print()
print("Evidence columns:")
print(list(evidence.columns))


# ---------------------------------------------------------
# Build business list
# ---------------------------------------------------------

businesses = sorted(
    set(
        evidence["business_name"]
        .dropna()
        .astype(str)
    )
)


results = []


for business in businesses:

    rows = evidence[
        evidence["business_name"]
        .astype(str)
        .str.lower()
        == business.lower()
    ].copy()


    # -----------------------------------------------------
    # PHONE
    # -----------------------------------------------------

    phone_records = []

    for _, r in rows.iterrows():

        value = norm_phone(
            r.get("phone", "")
        )

        if value:

            phone_records.append({
                "value": value,
                "source_type":
                    clean(
                        r.get(
                            "source_type",
                            "OTHER"
                        )
                    ),
                "weight":
                    source_weight(
                        r.get(
                            "source_type",
                            "OTHER"
                        )
                    ),
                "url":
                    clean(
                        r.get("url", "")
                    )
            })


    phone_groups = {}

    for rec in phone_records:

        phone_groups.setdefault(
            rec["value"],
            []
        ).append(rec)


    phone_scores = {}

    for value, records in phone_groups.items():

        domains = set()

        for rec in records:

            try:
                d = urlparse(
                    rec["url"]
                ).netloc.lower()

                d = d.replace(
                    "www.",
                    ""
                )

                if d:
                    domains.add(d)

            except:
                pass

        phone_scores[value] = (
            sum(
                r["weight"]
                for r in records
            )
            + len(domains)
        )


    if not phone_groups:

        phone_status = "NO_EVIDENCE"
        phone_value = ""

    elif len(phone_groups) == 1:

        phone_value = max(
            phone_scores,
            key=phone_scores.get
        )

        supporting_domains = set()

        for rec in phone_groups[
            phone_value
        ]:

            try:
                d = urlparse(
                    rec["url"]
                ).netloc.lower()

                d = d.replace(
                    "www.",
                    ""
                )

                if d:
                    supporting_domains.add(d)

            except:
                pass

        if len(supporting_domains) >= 2:
            phone_status = "MULTI_SOURCE_SUPPORTED"
        else:
            phone_status = "SINGLE_SOURCE"

    else:

        phone_value = max(
            phone_scores,
            key=phone_scores.get
        )

        phone_status = "CONFLICT"


    # -----------------------------------------------------
    # HOURS
    # -----------------------------------------------------

    hour_records = []

    for _, r in rows.iterrows():

        value = norm_hours(
            r.get("hours", "")
        )

        if value:

            hour_records.append({
                "value": value,
                "source_type":
                    clean(
                        r.get(
                            "source_type",
                            "OTHER"
                        )
                    ),
                "weight":
                    source_weight(
                        r.get(
                            "source_type",
                            "OTHER"
                        )
                    ),
                "url":
                    clean(
                        r.get("url", "")
                    )
            })


    hour_groups = {}

    for rec in hour_records:

        hour_groups.setdefault(
            rec["value"],
            []
        ).append(rec)


    if not hour_groups:

        hours_status = "NO_EVIDENCE"
        hours_value = ""

    elif len(hour_groups) == 1:

        hours_value = list(
            hour_groups.keys()
        )[0]

        domains = set()

        for rec in hour_records:

            try:
                d = urlparse(
                    rec["url"]
                ).netloc.lower()

                d = d.replace(
                    "www.",
                    ""
                )

                if d:
                    domains.add(d)

            except:
                pass

        if len(domains) >= 2:
            hours_status = (
                "MULTI_SOURCE_SUPPORTED"
            )
        else:
            hours_status = (
                "SINGLE_SOURCE"
            )

    else:

        # Pick the value with greatest
        # evidence weight, but preserve conflict.
        scores = {}

        for value, recs in hour_groups.items():

            scores[value] = sum(
                r["weight"]
                for r in recs
            )

        hours_value = max(
            scores,
            key=scores.get
        )

        hours_status = "CONFLICT"


    # -----------------------------------------------------
    # ADDRESS
    # -----------------------------------------------------

    addr_rows = address[
        address["business_name"]
        .astype(str)
        .str.lower()
        == business.lower()
    ].copy()


    if len(addr_rows) == 0:

        address_value = ""
        address_status = "NO_EVIDENCE"
        address_support = 0

    else:

        # Only locations with actual source support
        # are considered.
        supported = addr_rows[
            addr_rows[
                "web_support"
            ].isin([
                "SINGLE_SOURCE",
                "SECONDARY_WEB_SUPPORT",
                "STRONG_WEB_SUPPORT"
            ])
        ].copy()

        if len(supported) == 0:

            address_value = ""
            address_status = "NO_SOURCE_MATCH"
            address_support = 0

        else:

            # Choose candidate with highest
            # independent domain support.
            supported[
                "support_score"
            ] = (
                supported[
                    "independent_domain_count"
                ].fillna(0)
                * 10
                +
                supported[
                    "source_count"
                ].fillna(0)
            )

            best = supported.sort_values(
                "support_score",
                ascending=False
            ).iloc[0]

            address_value = clean(
                best[
                    "representative_address"
                ]
            )

            address_support = int(
                best[
                    "independent_domain_count"
                ]
            )

            if len(supported) > 1:

                # Different candidates can mean
                # branches or unresolved variants.
                unique_addresses = set(
                    norm_text(x)
                    for x in supported[
                        "representative_address"
                    ]
                )

                if len(unique_addresses) > 1:
                    address_status = (
                        "MULTIPLE_LOCATION_CANDIDATES"
                    )
                else:
                    address_status = (
                        "MULTI_SOURCE_SUPPORTED"
                    )

            else:

                if address_support >= 3:
                    address_status = (
                        "STRONG_WEB_SUPPORT"
                    )
                elif address_support == 2:
                    address_status = (
                        "MULTI_SOURCE_SUPPORTED"
                    )
                else:
                    address_status = (
                        "SINGLE_SOURCE"
                    )


    # -----------------------------------------------------
    # Overall status
    # -----------------------------------------------------

    statuses = [
        phone_status,
        hours_status,
        address_status
    ]


    if "CONFLICT" in statuses:

        overall = "CONFLICT_REQUIRES_REVIEW"

    elif (
        "MULTIPLE_LOCATION_CANDIDATES"
        in statuses
    ):

        overall = (
            "LOCATION_REQUIRES_REVIEW"
        )

    elif all(
        x in [
            "MULTI_SOURCE_SUPPORTED",
            "STRONG_WEB_SUPPORT"
        ]
        for x in statuses
        if x != "NO_EVIDENCE"
    ):

        overall = "WEB_SUPPORTED"

    elif any(
        x in [
            "MULTI_SOURCE_SUPPORTED",
            "STRONG_WEB_SUPPORT"
        ]
        for x in statuses
    ):

        overall = "PARTIALLY_WEB_SUPPORTED"

    elif any(
        x == "SINGLE_SOURCE"
        for x in statuses
    ):

        overall = "SINGLE_SOURCE_EVIDENCE"

    else:

        overall = "INSUFFICIENT_EVIDENCE"


    results.append({

        "business_name":
            business,

        "address":
            address_value,

        "address_status":
            address_status,

        "address_domain_support":
            address_support,

        "phone":
            phone_value,

        "phone_status":
            phone_status,

        "hours":
            hours_value,

        "hours_status":
            hours_status,

        "overall_status":
            overall,

        "physical_verification":
            "NOT_PHYSICALLY_VERIFIED"
    })


final = pd.DataFrame(results)


final.to_excel(
    OUTPUT,
    index=False
)


print()
print("=" * 70)
print("V10 RESULT")
print("=" * 70)

print()
print("Businesses:",
      len(final))

print()
print("OVERALL STATUS")
print(
    final[
        "overall_status"
    ].value_counts()
    .to_string()
)

print()
print("ADDRESS")
print(
    final[
        "address_status"
    ].value_counts()
    .to_string()
)

print()
print("PHONE")
print(
    final[
        "phone_status"
    ].value_counts()
    .to_string()
)

print()
print("HOURS")
print(
    final[
        "hours_status"
    ].value_counts()
    .to_string()
)

print()
print("PHYSICAL VERIFICATION")
print(
    final[
        "physical_verification"
    ].value_counts()
    .to_string()
)

print()
print("FINAL TABLE")
print()

print(
    final[
        [
            "business_name",
            "address",
            "address_status",
            "phone",
            "phone_status",
            "hours",
            "hours_status",
            "overall_status",
            "physical_verification"
        ]
    ].to_string(index=False)
)

print()
print("Saved:", OUTPUT)
