import pandas as pd
import re
from urllib.parse import urlparse

INPUT = "reports/clean_field_evidence_v11.xlsx"
OUTPUT = "reports/verification_v13.xlsx"

df = pd.read_excel(INPUT)

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def phone(x):
    raw = clean(x)
    s = re.sub(r"\D", "", raw)
    if raw.endswith(".0") and len(s) == 11:
        s = s[:-1]
    if s.startswith("91") and len(s) >= 12:
        s = s[-10:]
    if len(s) == 10 and s[0] in "6789":
        return s
    return ""

def domain(url):
    try:
        return urlparse(clean(url)).netloc.lower().replace("www.", "")
    except:
        return ""

def source_type(d):
    if any(x in d for x in ["instagram.","youtube.","facebook.","reddit."]):
        return "SOCIAL"
    if any(x in d for x in ["zomato.","swiggy.","tripadvisor.","justdial.","magicpin.","eazydiner."]):
        return "DIRECTORY"
    if any(x in d for x in ["tajhotels.","oberoihotels.","hotelkalyan.","nirosindia."]):
        return "OFFICIAL"
    if any(x in d for x in ["cntraveler.","condnasttraveler."]):
        return "ARTICLE"
    return "OTHER"

def norm_text(x):
    x = clean(x).lower()
    x = x.replace("m.i. road", "mi road")
    x = x.replace("m i road", "mi road")
    x = re.sub(r"[^a-z0-9 ]+", " ", x)
    return re.sub(r"\s+", " ", x).strip()

def evaluate(records):
    if not records:
        return ("NO_EVIDENCE", "", 0)

    groups = {}

    for r in records:
        if r["value"]:
            groups.setdefault(r["value"], []).append(r)

    if not groups:
        return ("NO_EVIDENCE", "", 0)

    ranked = []

    for value, rows in groups.items():

        domains = set(
            r["domain"]
            for r in rows
            if r["domain"]
        )

        # Social/video is not counted as strong independent confirmation
        credible_domains = set(
            r["domain"]
            for r in rows
            if r["domain"]
            and r["source_type"] not in ["SOCIAL"]
        )

        score = sum(
            5 if r["source_type"] == "OFFICIAL"
            else 3 if r["source_type"] == "DIRECTORY"
            else 2 if r["source_type"] == "ARTICLE"
            else 1
            for r in rows
        )

        ranked.append(
            (
                value,
                len(credible_domains),
                len(domains),
                score
            )
        )

    ranked.sort(
        key=lambda x: (x[1], x[2], x[3]),
        reverse=True
    )

    best = ranked[0]

    if len(groups) > 1:
        status = "CONFLICT"
    elif best[1] >= 2:
        status = "MULTI_SOURCE_SUPPORTED"
    else:
        status = "SINGLE_SOURCE"

    return (
        status,
        best[0],
        best[1]
    )

results = []

for business, g in df.groupby("business_name"):

    phones = []
    addresses = []
    hours = []

    for _, r in g.iterrows():

        d = domain(r.get("domain", ""))
        st = source_type(d)

        p = phone(r.get("phone", ""))

        if p:
            phones.append({
                "value": p,
                "domain": d,
                "source_type": st
            })

        a = norm_text(r.get("address", ""))

        if a:
            addresses.append({
                "value": a,
                "domain": d,
                "source_type": st
            })

        h = clean(r.get("hours", "")).lower()

        if re.search(r"\d{1,2}(:\d{2})?\s*(am|pm)", h):
            hours.append({
                "value": h,
                "domain": d,
                "source_type": st
            })

    ps, pv, pc = evaluate(phones)
    ass, av, ac = evaluate(addresses)
    hs, hv, hc = evaluate(hours)

    if "CONFLICT" in [ps, ass, hs]:
        overall = "CONFLICT"
    elif "MULTI_SOURCE_SUPPORTED" in [ps, ass, hs]:
        overall = "WEB_SUPPORTED"
    elif "SINGLE_SOURCE" in [ps, ass, hs]:
        overall = "SINGLE_SOURCE"
    else:
        overall = "NO_EVIDENCE"

    results.append({
        "business_name": business,

        "phone": pv,
        "phone_status": ps,
        "phone_credible_domains": pc,

        "address": av,
        "address_status": ass,
        "address_credible_domains": ac,

        "hours": hv,
        "hours_status": hs,
        "hours_credible_domains": hc,

        "overall_status": overall,

        "physical_verification":
            "NOT_PHYSICALLY_VERIFIED"
    })

out = pd.DataFrame(results)

out.to_excel(
    OUTPUT,
    index=False
)

print("=" * 70)
print("VERIFICATION V13")
print("=" * 70)

print("\nBUSINESSES:", len(out))

print("\nOVERALL")
print(
    out["overall_status"]
    .value_counts()
    .to_string()
)

print("\nPHONE")
print(
    out["phone_status"]
    .value_counts()
    .to_string()
)

print("\nADDRESS")
print(
    out["address_status"]
    .value_counts()
    .to_string()
)

print("\nHOURS")
print(
    out["hours_status"]
    .value_counts()
    .to_string()
)

print("\nRESULTS")
print(
    out[
        [
            "business_name",
            "phone_status",
            "address_status",
            "hours_status",
            "overall_status"
        ]
    ].to_string(index=False)
)

print("\nSaved:", OUTPUT)



