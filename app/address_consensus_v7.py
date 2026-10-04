import pandas as pd
import re
from difflib import SequenceMatcher

INPUT = "reports/address_reconstructed_v6.xlsx"
OUTPUT = "reports/address_consensus_v7.xlsx"

df = pd.read_excel(INPUT)

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def norm_text(s):
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
        x for x in norm_text(s).split()
        if len(x) >= 3
    )


def similarity(a, b):

    ta = tokens(a)
    tb = tokens(b)

    if not ta or not tb:
        return 0

    intersection = len(ta & tb)
    union = len(ta | tb)

    jaccard = intersection / union if union else 0

    seq = SequenceMatcher(
        None,
        norm_text(a),
        norm_text(b)
    ).ratio()

    return max(jaccard, seq * 0.75)


def domain(url):

    m = re.search(
        r"https?://(?:www\.)?([^/]+)",
        str(url)
    )

    if not m:
        return ""

    return m.group(1).lower()


# ---------------------------------------------------------
# Remove obvious contaminated addresses
# ---------------------------------------------------------

BAD_PATTERNS = [
    r"\border online\b",
    r"\brequest reservation\b",
    r"\bbook now\b",
    r"\btripadvisor\b",
    r"\breport an error\b",
    r"\bdirection\b",
    r"\bservice\b",
    r"\bform\b",
    r"\benquire\b",
    r"\bthey have\b",
    r"\bis a\b",
    r"\bis best\b",
    r"\bfamous for\b",
    r"\bwell known\b",
    r"\bindulge\b",
    r"\bdelicious\b",
    r"\bfood destination\b",
    r"\brecently visited\b",
    r"\bnow offer\b",
    r"\bfast food\b",
]

def is_clean(addr):

    s = norm_text(addr)

    if not s:
        return False

    if not re.search(r"\bjaipur\b", s):
        return False

    for p in BAD_PATTERNS:
        if re.search(p, s):
            return False

    # Address should not look like a whole paragraph
    if len(s.split()) > 18:
        return False

    return True


# ---------------------------------------------------------
# Prepare valid candidates
# ---------------------------------------------------------

valid = []

for _, r in df.iterrows():

    if str(r.get("final_quality", "")) not in [
        "CLEAN",
        "REVIEW"
    ]:
        continue

    address = str(
        r.get("reconstructed_address", "")
    ).strip()

    if not is_clean(address):
        continue

    url = str(r.get("url", ""))

    valid.append({
        "business_name": str(r.get("business_name", "")),
        "address": address,
        "normalized": norm_text(address),
        "url": url,
        "domain": domain(url),
        "title": str(r.get("title", "")),
        "entity_relevance": r.get(
            "entity_relevance", ""
        )
    })


valid_df = pd.DataFrame(valid)

# ---------------------------------------------------------
# Cluster addresses per business
# ---------------------------------------------------------

results = []

for business, group in valid_df.groupby(
    "business_name"
):

    records = group.to_dict("records")

    clusters = []

    for record in records:

        placed = False

        for cluster in clusters:

            representative = cluster[0]

            sim = similarity(
                record["address"],
                representative["address"]
            )

            if sim >= 0.55:

                cluster.append(record)
                placed = True
                break

        if not placed:
            clusters.append([record])

    # -----------------------------------------------------
    # Process clusters
    # -----------------------------------------------------

    for cluster_id, cluster in enumerate(
        clusters,
        start=1
    ):

        addresses = [
            x["address"]
            for x in cluster
        ]

        # Pick longest clean address as representative
        representative = max(
            addresses,
            key=lambda x: len(x)
        )

        domains = sorted(
            set(
                x["domain"]
                for x in cluster
                if x["domain"]
            )
        )

        sources = len(
            set(
                x["url"]
                for x in cluster
                if x["url"]
            )
        )

        independent_domains = len(domains)

        # -------------------------------------------------
        # Confidence
        # -------------------------------------------------

        if independent_domains >= 3:
            status = "MULTI_SOURCE_SUPPORTED"

        elif independent_domains == 2:
            status = "SECONDARY_SUPPORTED"

        elif independent_domains == 1:
            status = "SINGLE_SOURCE"

        else:
            status = "NO_SOURCE"

        # Potential branch signal
        if len(clusters) > 1:
            branch_status = "MULTIPLE_LOCATION_CANDIDATES"
        else:
            branch_status = "SINGLE_LOCATION_CANDIDATE"

        results.append({
            "business_name": business,
            "cluster_id": cluster_id,
            "representative_address": representative,
            "address_variants": " | ".join(
                sorted(set(addresses))
            ),
            "source_count": sources,
            "independent_domain_count":
                independent_domains,
            "domains": " | ".join(domains),
            "status": status,
            "branch_status": branch_status
        })


out = pd.DataFrame(results)

if len(out):

    out = out.sort_values(
        [
            "business_name",
            "independent_domain_count",
            "source_count"
        ],
        ascending=[
            True,
            False,
            False
        ]
    )

out.to_excel(
    OUTPUT,
    index=False
)

print("=" * 70)
print("ADDRESS CONSENSUS V7")
print("=" * 70)
print()
print("Valid candidate records:", len(valid_df))
print("Businesses:", valid_df["business_name"].nunique())
print("Address clusters:", len(out))
print()
print("STATUS")
print(
    out["status"].value_counts().to_string()
    if len(out)
    else "No valid clusters"
)
print()
print("BRANCH STATUS")
print(
    out["branch_status"].value_counts().to_string()
    if len(out)
    else "No clusters"
)
print()
print("CONSENSUS RESULTS")
print()

if len(out):
    print(
        out[
            [
                "business_name",
                "cluster_id",
                "representative_address",
                "source_count",
                "independent_domain_count",
                "status",
                "branch_status"
            ]
        ].to_string(index=False)
    )

print()
print("Saved:", OUTPUT)
