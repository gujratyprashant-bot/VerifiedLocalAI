import pandas as pd
import re
from urllib.parse import urlparse

INPUT = "reports/clean_field_evidence_v11.xlsx"
OUTPUT = "reports/verification_v12.xlsx"


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


def normalize_phone(x):

    digits = re.sub(
        r"\D",
        "",
        clean(x)
    )

    if digits.startswith("91") and len(digits) >= 12:
        digits = digits[-10:]

    if (
        len(digits) == 10
        and digits[0] in "6789"
    ):
        return digits

    return ""


def normalize_text(x):

    x = clean(x).lower()

    replacements = {
        "m.i. road": "mirza ismail road",
        "m i road": "mirza ismail road",
        "mi road": "mirza ismail road",
        "mirza ismail rd": "mirza ismail road",
        "marg": "road",
        "street": "road",
        "rd": "road",
    }

    x = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        x
    )

    x = re.sub(
        r"\s+",
        " ",
        x
    ).strip()

    for a, b in replacements.items():
        x = x.replace(a, b)

    return re.sub(
        r"\s+",
        " ",
        x
    ).strip()


def normalize_hours(x):

    x = clean(x).lower()

    x = x.replace("–", "-")
    x = x.replace("—", "-")

    x = re.sub(
        r"\s+",
        " ",
        x
    ).strip()

    return x


def domain(url):

    try:

        d = urlparse(
            clean(url)
        ).netloc.lower()

        return d.replace(
            "www.",
            ""
        )

    except:

        return ""


def classify_source(domain_name):

    d = domain_name.lower()

    if any(
        x in d
        for x in [
            "instagram.",
            "youtube.",
            "facebook.",
            "reddit."
        ]
    ):
        return "SOCIAL_OR_VIDEO"

    if any(
        x in d
        for x in [
            "zomato.",
            "swiggy.",
            "tripadvisor.",
            "justdial.",
            "magicpin.",
            "eazydiner."
        ]
    ):
        return "DIRECTORY"

    if any(
        x in d
        for x in [
            "tajhotels.",
            "oberoihotels.",
            "hotelkalyan.",
            "nirosindia."
        ]
    ):
        return "OFFICIAL_FIRST_PARTY"

    if any(
        x in d
        for x in [
            "cntraveler.",
            "condnasttraveler."
        ]
    ):
        return "LIST_ARTICLE"

    return "OTHER"


def independent_domains(records):

    return sorted(
        set(
            r["domain"]
            for r in records
            if r["domain"]
        )
    )


def evaluate(records):

    if not records:
        return {
            "status": "NO_EVIDENCE",
            "value": "",
            "domains": "",
            "domain_count": 0,
            "weighted_score": 0
        }


    groups = {}

    for r in records:

        value = r["value"]

        if not value:
            continue

        groups.setdefault(
            value,
            []
        ).append(r)


    if not groups:

        return {
            "status": "NO_EVIDENCE",
            "value": "",
            "domains": "",
            "domain_count": 0,
            "weighted_score": 0
        }


    scored = []

    for value, vals in groups.items():

        domains = independent_domains(
            vals
        )

        weighted = sum(
            WEIGHTS.get(
                v["source_type"],
                1
            )
            for v in vals
        )

        # Independent domain bonus
        score = (
            weighted
            + len(domains) * 2
        )

        scored.append({
            "value": value,
            "domains": domains,
            "domain_count": len(domains),
            "weighted_score": score
        })


    scored.sort(
        key=lambda x: (
            x["domain_count"],
            x["weighted_score"]
        ),
        reverse=True
    )


    best = scored[0]


    if len(groups) == 1:

        if best["domain_count"] >= 2:

            status = "MULTI_SOURCE_SUPPORTED"

        else:

            status = "SINGLE_SOURCE"


    else:

        # Different values exist.
        # Preserve conflict even when one value
        # has a stronger score.
        status = "CONFLICT"


    return {
        "status": status,
        "value": best["value"],
        "domains": " | ".join(
            best["domains"]
        ),
        "domain_count":
            best["domain_count"],
        "weighted_score":
            best["weighted_score"]
    }


df = pd.read_excel(INPUT)


results = []


for business, group in df.groupby(
    "business_name"
):

    phone_records = []
    address_records = []
    hour_records = []


    for _, r in group.iterrows():

        d = clean(
            r.get("domain", "")
        )

        source_type = classify_source(
            d
        )


        phone = normalize_phone(
            r.get("phone", "")
        )

        if phone:

            phone_records.append({
                "value":
                    phone,
                "domain":
                    d,
                "source_type":
                    source_type
            })


        address = normalize_text(
            r.get("address", "")
        )

        if address:

            address_records.append({
                "value":
                    address,
                "domain":
                    d,
                "source_type":
                    source_type
            })


        hours = normalize_hours(
            r.get("hours", "")
        )

        if hours:

            hour_records.append({
                "value":
                    hours,
                "domain":
                    d,
                "source_type":
                    source_type
            })


    phone_result = evaluate(
        phone_records
    )

    address_result = evaluate(
        address_records
    )

    hours_result = evaluate(
        hour_records
    )


    statuses = [
        phone_result["status"],
        address_result["status"],
        hours_result["status"]
    ]


    if "CONFLICT" in statuses:

        overall = "CONFLICT"

    elif (
        "MULTI_SOURCE_SUPPORTED"
        in statuses
    ):

        overall = "WEB_SUPPORTED"

    elif (
        "SINGLE_SOURCE"
        in statuses
    ):

        overall = "SINGLE_SOURCE_EVIDENCE"

    else:

        overall = "INSUFFICIENT_EVIDENCE"


    results.append({

        "business_name":
            business,

        "phone":
            phone_result["value"],

        "phone_status":
            phone_result["status"],

        "phone_domains":
            phone_result["domains"],

        "phone_domain_count":
            phone_result["domain_count"],

        "phone_score":
            phone_result["weighted_score"],


        "address":
            address_result["value"],

        "address_status":
            address_result["status"],

        "address_domains":
            address_result["domains"],

        "address_domain_count":
            address_result["domain_count"],

        "address_score":
            address_result["weighted_score"],


        "hours":
            hours_result["value"],

        "hours_status":
            hours_result["status"],

        "hours_domains":
            hours_result["domains"],

        "hours_domain_count":
            hours_result["domain_count"],

        "hours_score":
            hours_result["weighted_score"],


        "overall_status":
            overall,

        "physical_verification":
            "NOT_PHYSICALLY_VERIFIED"
    })


out = pd.DataFrame(
    results
)


out.to_excel(
    OUTPUT,
    index=False
)


print("=" * 70)
print("VERIFICATION V12")
print("=" * 70)

print()
print("Businesses:",
      len(out))

print()
print("OVERALL")
print(
    out["overall_status"]
    .value_counts()
    .to_string()
)

print()
print("PHONE")
print(
    out["phone_status"]
    .value_counts()
    .to_string()
)

print()
print("ADDRESS")
print(
    out["address_status"]
    .value_counts()
    .to_string()
)

print()
print("HOURS")
print(
    out["hours_status"]
    .value_counts()
    .to_string()
)

print()
print("MULTI-SOURCE RESULTS")
print()

multi = out[
    (
        (out["phone_domain_count"] >= 2)
        |
        (out["address_domain_count"] >= 2)
        |
        (out["hours_domain_count"] >= 2)
    )
]

if len(multi):

    print(
        multi[
            [
                "business_name",
                "phone",
                "phone_status",
                "address",
                "address_status",
                "hours",
                "hours_status",
                "overall_status"
            ]
        ].to_string(index=False)
    )

else:

    print(
        "No multi-source results."
    )

print()
print("Saved:", OUTPUT)
