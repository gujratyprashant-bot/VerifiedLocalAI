import pandas as pd
import re

INPUT = "reports/final_business_dataset_v14.xlsx"
OUTPUT = "reports/business_leads_v15.xlsx"

df = pd.read_excel(INPUT)

def clean(x):
    if pd.isna(x):
        return ""
    return str(x).strip()

def good_address(x):

    x = clean(x).lower()

    if not x:
        return False

    bad = [
        "more st",
        "per person",
        "request reservation",
        "order online",
        "opening more",
        "rating",
        "reviews",
        "phone",
        "call",
        "hours",
        "booking",
        "price",
        "guest",
        "category",
        "player in the category",
        "at amer fort are the two",
        "near iffco chowk metro st"
    ]

    if any(b in x for b in bad):
        return False

    # Reject suspiciously long prose
    if len(x) > 120:
        return False

    # Must contain some location signal
    location_words = [
        "jaipur",
        "road",
        "marg",
        "bazar",
        "market",
        "nagar",
        "circle",
        "chaupar",
        "fort",
        "chowk",
        "agra",
        "tonk",
        "mi road"
    ]

    if not any(w in x for w in location_words):
        return False

    return True


def good_phone(x):

    x = clean(x)

    digits = re.sub(
        r"\D",
        "",
        x
    )

    if digits.startswith("91") and len(digits) >= 12:
        digits = digits[-10:]

    return (
        len(digits) == 10
        and digits[0] in "6789"
    )


rows = []

for _, r in df.iterrows():

    name = clean(
        r["business_name"]
    )

    address = clean(
        r["address"]
    )

    phone = clean(
        r["phone"]
    )

    address_ok = good_address(
        address
    )

    phone_ok = good_phone(
        phone
    )

    # Keep businesses where we have
    # at least one usable real-world field.
    if not address_ok and not phone_ok:
        continue

    if address_ok:
        final_address = address
    else:
        final_address = ""

    if phone_ok:
        digits = re.sub(
            r"\D",
            "",
            phone
        )

        if digits.startswith("91") and len(digits) >= 12:
            digits = digits[-10:]

        final_phone = digits
    else:
        final_phone = ""

    rows.append({

        "business_name":
            name,

        "address":
            final_address,

        "phone":
            final_phone,

        "hours":
            clean(r["hours"])
            if address_ok or phone_ok
            else "",

        "verification_status":
            clean(
                r["verification_status"]
            ),

        "confidence":
            clean(
                r["confidence"]
            ),

        "physical_verification":
            "NOT_PHYSICALLY_VERIFIED",

        "data_quality":
            (
                "ADDRESS_AVAILABLE"
                if address_ok and not phone_ok
                else
                "PHONE_AVAILABLE"
                if phone_ok and not address_ok
                else
                "ADDRESS_AND_PHONE_AVAILABLE"
            )
    })


out = pd.DataFrame(rows)

out = out.drop_duplicates(
    subset=["business_name"],
    keep="first"
)

out = out.sort_values(
    by="business_name"
)

out.to_excel(
    OUTPUT,
    index=False
)

print("=" * 70)
print("BUSINESS LEADS V15")
print("=" * 70)

print()
print("Usable businesses:",
      len(out))

print()
print("DATA QUALITY")

print(
    out["data_quality"]
    .value_counts()
    .to_string()
)

print()
print("VERIFICATION")

print(
    out["verification_status"]
    .value_counts()
    .to_string()
)

print()
print("LEADS")

print(
    out[
        [
            "business_name",
            "address",
            "phone",
            "verification_status",
            "data_quality"
        ]
    ].to_string(index=False)
)

print()
print("Saved:", OUTPUT)
