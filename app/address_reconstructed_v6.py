import pandas as pd
import re

INPUT = "reports/address_quality_v5.xlsx"
OUTPUT = "reports/address_reconstructed_v6.xlsx"

df = pd.read_excel(INPUT)

# Words that commonly indicate the address has ended
STOP_WORDS = [
    " is a restaurant",
    " is best",
    " is one of",
    " they have",
    " they offer",
    " famous for",
    " well known",
    " known for",
    " popular",
    " request reservation",
    " order online",
    " reviews",
    " ratings",
    " ambience",
    " delicious",
    " food destination",
    " recently visited",
    " offers",
    " serves",
]

def clean_text(s):
    s = str(s)

    # URLs
    s = re.sub(r"https?://\S+", " ", s)

    # Phone numbers
    s = re.sub(r"(?:\+91[\s-]*)?(?:\d[\s-]*){10,13}", " ", s)

    # Ratings
    s = re.sub(r"\b\d+(?:\.\d+)?\s*/\s*5\b", " ", s)

    # Excess whitespace
    s = re.sub(r"\s+", " ", s).strip()

    return s


def reconstruct(addr):

    s = clean_text(addr)
    low = s.lower()

    # Cut obvious descriptive text
    positions = []

    for word in STOP_WORDS:
        pos = low.find(word)

        if pos > 10:
            positions.append(pos)

    if positions:
        s = s[:min(positions)]

    # Remove trailing punctuation
    s = s.strip(" .,:;-/|")

    # Remove accidental leading descriptive fragments
    prefixes = [
        "figure-art-installation-at-",
        "5 on tripadvisor.",
        "on tripadvisor.",
        "dinner.",
    ]

    low = s.lower()

    for prefix in prefixes:
        if low.startswith(prefix):
            s = s[len(prefix):].strip()

    # Remove duplicated business-name phrases where possible
    s = re.sub(
        r"\bthey have two branches\b.*?\bjaipur\b",
        "Jaipur",
        s,
        flags=re.I
    )

    # Remove standalone business descriptions before a clear location
    s = re.sub(
        r"\b(?:restaurant|pvt ltd)\s+(?:is|in)\s+",
        " ",
        s,
        flags=re.I
    )

    # Normalize
    s = re.sub(r"\s+", " ", s).strip(" .,:;-/|")

    return s


def extract_components(addr):

    s = reconstruct(addr)

    # Pincode
    pincode = ""
    m = re.search(r"\b[1-9]\d{5}\b", s)

    if m:
        pincode = m.group(0)

    # Remove pincode from address body
    body = re.sub(r"\b[1-9]\d{5}\b", "", s)

    # Remove repeated punctuation
    body = re.sub(r"\s+", " ", body)
    body = body.strip(" .,:;-/|")

    # Strong cleanup of obvious review phrases
    body = re.sub(
        r"\b(?:restaurant|hotel|cafe|kitchen)\s+(?:in|at)\s+",
        "",
        body,
        flags=re.I
    )

    body = re.sub(r"\s+", " ", body).strip()

    return body, pincode


rows = []

for _, r in df.iterrows():

    quality = str(r.get("quality", ""))

    if quality not in ["STRONG_ADDRESS", "POSSIBLE_ADDRESS"]:
        continue

    raw = str(r.get("clean_address", "")).strip()

    if not raw:
        continue

    reconstructed, pincode = extract_components(raw)

    low = reconstructed.lower()

    # Validation
    has_jaipur = bool(re.search(r"\bjaipur\b", low))

    has_location = bool(
        re.search(
            r"\b(road|rd|marg|nagar|bazar|bazaar|chowk|"
            r"colony|market|circle|phatak|camp|bagh|"
            r"vihar|plaza|palace|complex)\b",
            low
        )
    )

    has_number = bool(
        re.search(r"\b(?:no\.?|number|shop|plot|house|khasra|floor)\s*[\w./-]*\d+", low)
        or re.search(r"^\d{1,5}[,\s]", low)
    )

    # Reject obvious contamination
    contamination = bool(
        re.search(
            r"\b(they|restaurant is|is a|famous for|well known|"
            r"recently visited|request reservation|tripadvisor|"
            r"reviews?|ratings?|ambience|delicious|"
            r"food destination)\b",
            low
        )
    )

    word_count = len(reconstructed.split())

    if has_jaipur and has_location and not contamination and word_count <= 18:
        final_quality = "CLEAN"
    elif has_jaipur and has_location and word_count <= 25:
        final_quality = "REVIEW"
    else:
        final_quality = "REJECT"

    rows.append({
        "business_name": r["business_name"],
        "title": r.get("title", ""),
        "url": r.get("url", ""),
        "entity_relevance": r.get("entity_relevance", ""),
        "original_address": raw,
        "reconstructed_address": reconstructed,
        "pincode": pincode,
        "source_quality": quality,
        "final_quality": final_quality,
        "word_count": word_count
    })


out = pd.DataFrame(rows)

out.to_excel(OUTPUT, index=False)

print("=" * 65)
print("ADDRESS RECONSTRUCTION V6")
print("=" * 65)
print()
print("Rows processed:", len(out))
print()
print("Final quality:")
print(out["final_quality"].value_counts().to_string())
print()
print(
    "Businesses with CLEAN addresses:",
    out[out["final_quality"] == "CLEAN"]["business_name"].nunique()
)
print()
print("CLEAN ADDRESS SAMPLE")
print(
    out[out["final_quality"] == "CLEAN"][
        [
            "business_name",
            "reconstructed_address",
            "pincode"
        ]
    ].to_string(index=False)
)
print()
print("Saved:", OUTPUT)
