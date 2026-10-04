import pandas as pd
import re
from difflib import SequenceMatcher

INPUT = "reports/address_consensus_v7.xlsx"
OUTPUT = "reports/address_final_v8.xlsx"

df = pd.read_excel(INPUT)

def norm(s):
    s = str(s).lower()

    replacements = {
        "road": "rd",
        "marg": "rd",
        "street": "st",
        "bazaar": "bazar",
        "circle": "cir",
        "number": "no",
    }

    for a, b in replacements.items():
        s = re.sub(r"\b" + a + r"\b", b, s)

    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s)

    return s.strip()


def tokens(s):
    return set(
        x for x in norm(s).split()
        if len(x) >= 3
    )


def similarity(a, b):

    ta = tokens(a)
    tb = tokens(b)

    if not ta or not tb:
        return 0

    intersection = len(ta & tb)
    union = len(ta | tb)

    jaccard = intersection / union

    seq = SequenceMatcher(
        None,
        norm(a),
        norm(b)
    ).ratio()

    return max(jaccard, seq * 0.8)


# Location aliases commonly used in Jaipur
ALIASES = {
    "mi road": "mirza ismail road",
    "m i road": "mirza ismail road",
    "mirza ismail rd": "mirza ismail road",
    "jln marg": "jawahar lal nehru marg",
    "nehru bazar rd": "nehru bazar",
    "bapu bazar road": "bapu bazar",
}


def canonical(s):

    s = norm(s)

    for old, new in ALIASES.items():
        s = s.replace(
            norm(old),
            norm(new)
        )

    s = re.sub(r"\s+", " ", s)

    return s.strip()


def extract_location_parts(address):

    original = str(address)
    c = canonical(original)

    parts = {
        "house_shop_number": "",
        "road": "",
        "area": "",
        "city": "Jaipur" if "jaipur" in c else ""
    }

    # Number
    m = re.search(
        r"\b(?:shop|house|plot|no|number|khasra)?\s*"
        r"(\d{1,5})\b",
        c
    )

    if m:
        parts["house_shop_number"] = m.group(1)

    # Road
    road_patterns = [
        r"([a-z ]+ road)\b",
        r"([a-z ]+ rd)\b",
        r"([a-z ]+ marg)\b"
    ]

    for p in road_patterns:

        m = re.search(p, c)

        if m:
            parts["road"] = m.group(1).strip()
            break

    # Known areas
    areas = [
        "mi road",
        "mirza ismail road",
        "bapu bazar",
        "johari bazar",
        "pink city",
        "vaishali nagar",
        "mansarovar",
        "vidhyadhar nagar",
        "adarsh nagar",
        "sindhi camp",
        "tonk phatak",
        "malviya nagar",
        "jamdoli",
        "raja park",
        "nehru bazar",
        "modikhana",
        "choti chaupar",
        "kishanpole bazar",
        "amer",
        "civil lines",
    ]

    for area in areas:

        if norm(area) in c:
            parts["area"] = area
            break

    return parts


rows = []

for _, r in df.iterrows():

    address = str(
        r.get("representative_address", "")
    ).strip()

    if not address:
        continue

    parts = extract_location_parts(address)

    canonical_address = canonical(address)

    rows.append({
        "business_name":
            r.get("business_name", ""),
        "cluster_id":
            r.get("cluster_id", ""),
        "original_address":
            address,
        "canonical_address":
            canonical_address,
        "house_shop_number":
            parts["house_shop_number"],
        "road":
            parts["road"],
        "area":
            parts["area"],
        "city":
            parts["city"],
        "source_count":
            r.get("source_count", 0),
        "independent_domain_count":
            r.get(
                "independent_domain_count",
                0
            ),
        "domains":
            r.get("domains", ""),
        "v7_status":
            r.get("status", "")
    })


out = pd.DataFrame(rows)

# ---------------------------------------------------------
# Merge clusters with same canonical location
# ---------------------------------------------------------

final_rows = []

for business, group in out.groupby(
    "business_name"
):

    records = group.to_dict("records")

    merged = []

    for rec in records:

        placed = False

        for cluster in merged:

            base = cluster[0]

            # Same canonical road/area
            same_road = (
                rec["road"] != ""
                and base["road"] != ""
                and rec["road"] == base["road"]
            )

            same_area = (
                rec["area"] != ""
                and base["area"] != ""
                and rec["area"] == base["area"]
            )

            sim = similarity(
                rec["canonical_address"],
                base["canonical_address"]
            )

            # Exact same number is strong evidence
            same_number = (
                rec["house_shop_number"]
                and base["house_shop_number"]
                and rec["house_shop_number"]
                == base["house_shop_number"]
            )

            if (
                same_number
                or sim >= 0.60
                or (same_road and same_area)
            ):
                cluster.append(rec)
                placed = True
                break

        if not placed:
            merged.append([rec])

    # -----------------------------------------------------
    # Output merged location candidates
    # -----------------------------------------------------

    for i, cluster in enumerate(
        merged,
        start=1
    ):

        addresses = [
            x["original_address"]
            for x in cluster
        ]

        domains = set()

        for x in cluster:

            for d in str(
                x["domains"]
            ).split("|"):

                d = d.strip()

                if d:
                    domains.add(d)

        source_count = sum(
            int(x["source_count"])
            if str(x["source_count"]).isdigit()
            else 0
            for x in cluster
        )

        independent_domains = len(domains)

        # Best representative = longest address
        representative = max(
            addresses,
            key=len
        )

        if independent_domains >= 3:
            evidence = "STRONG_WEB_SUPPORT"

        elif independent_domains == 2:
            evidence = "SECONDARY_WEB_SUPPORT"

        else:
            evidence = "SINGLE_SOURCE"

        if len(merged) > 1:
            location_status = "MULTIPLE_LOCATION_CANDIDATES"
        else:
            location_status = "SINGLE_LOCATION_CANDIDATE"

        final_rows.append({
            "business_name":
                business,
            "location_cluster":
                i,
            "representative_address":
                representative,
            "address_variants":
                " | ".join(
                    sorted(set(addresses))
                ),
            "independent_domains":
                independent_domains,
            "source_count":
                source_count,
            "domains":
                " | ".join(
                    sorted(domains)
                ),
            "web_evidence":
                evidence,
            "location_status":
                location_status
        })


final = pd.DataFrame(final_rows)

final.to_excel(
    OUTPUT,
    index=False
)

print("=" * 70)
print("ADDRESS FINAL V8")
print("=" * 70)
print()
print("Businesses:",
      final["business_name"].nunique())
print("Location candidates:",
      len(final))
print()
print("WEB EVIDENCE")
print(
    final["web_evidence"]
    .value_counts()
    .to_string()
)
print()
print("LOCATION STATUS")
print(
    final["location_status"]
    .value_counts()
    .to_string()
)
print()
print("FINAL LOCATION TABLE")
print()

print(
    final[
        [
            "business_name",
            "location_cluster",
            "representative_address",
            "independent_domains",
            "source_count",
            "web_evidence",
            "location_status"
        ]
    ].to_string(index=False)
)

print()
print("Saved:", OUTPUT)
