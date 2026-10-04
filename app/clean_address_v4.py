import pandas as pd
import re

INPUT = "reports/strict_evidence_v2.xlsx"
OUTPUT = "reports/clean_address_v4.xlsx"

df = pd.read_excel(INPUT)

rows = []

# Explicit address labels
LABEL_PATTERNS = [
    r"\baddress\s*[:\-]\s*(.{10,180})",
    r"\blocated at\s*[:\-]?\s*(.{10,180})",
    r"\bsituated at\s*[:\-]?\s*(.{10,180})",
    r"\bvisit us at\s*[:\-]?\s*(.{10,180})",
    r"\bfind us at\s*[:\-]?\s*(.{10,180})",
]

# Strong structured Indian address patterns
STRUCTURED_PATTERNS = [
    r"\b\d{1,5}\s*[/,-]?\s*\d{0,5}\s+[A-Za-z][A-Za-z .'-]{2,60}"
    r"(?:road|rd|marg|nagar|bazar|bazaar|chowk|colony|market|"
    r"circle|phatak|camp|bagh|vihar|plaza|palace|hotel|complex)"
    r"[^.;]{0,100}\bjaipur\b",

    r"\b(?:khasra|plot|shop|house|unit|floor|building|gate)\s*(?:no\.?|number)?"
    r"\s*[A-Za-z0-9./-]{1,15}"
    r"[^.;]{0,120}\bjaipur\b",

    r"\b[A-Za-z][A-Za-z .'-]{2,60}"
    r"(?:road|rd|marg|nagar|bazar|bazaar|chowk|colony|market|"
    r"circle|phatak|camp|bagh|vihar)"
    r"[^.;]{0,100}\bjaipur\b",
]

STOP_PATTERNS = [
    r"\b(?:phone|call|contact|email|website)\b",
    r"\b(?:open|closed|hours|timings|menu|reviews?|ratings?)\b",
    r"\b(?:order online|delivery|book now|view in map)\b",
    r"\b(?:similar restaurants?|more restaurants?)\b",
    r"\b(?:report an error|directioncopy|read more)\b",
]

def ascii_clean(s):
    s = str(s)

    # Remove markdown
    s = re.sub(r"#+", " ", s)
    s = re.sub(r"\[[^\]]*\]", " ", s)

    # Remove obvious URLs
    s = re.sub(r"https?://\S+", " ", s)

    # Normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()

    return s


def clean_candidate(s):

    s = ascii_clean(s)

    # Remove phone numbers
    s = re.sub(r"(?:\+91[\s-]*)?(?:\d[\s-]*){10,13}", " ", s)

    # Remove emails
    s = re.sub(r"\S+@\S+", " ", s)

    # Cut at obvious non-address content
    low = s.lower()

    cut_positions = []

    for pattern in STOP_PATTERNS:
        m = re.search(pattern, low)

        if m and m.start() > 15:
            cut_positions.append(m.start())

    if cut_positions:
        s = s[:min(cut_positions)]

    # Remove ratings/prices
    s = re.sub(r"\b\d+(?:\.\d+)?\s*/\s*5\b", " ", s)
    s = re.sub(r"₹\s*\d+(?:,\d+)*(?:\s*for two)?", " ", s)

    s = re.sub(r"\s+", " ", s).strip(" .,:;-/")

    return s


def extract_addresses(text):

    text = ascii_clean(text)

    candidates = []

    # 1. Explicit labels
    for pattern in LABEL_PATTERNS:

        for m in re.finditer(pattern, text, flags=re.I):

            candidate = clean_candidate(m.group(1))

            if candidate:
                candidates.append(("EXPLICIT", candidate))

    # 2. Structured address patterns
    for pattern in STRUCTURED_PATTERNS:

        for m in re.finditer(pattern, text, flags=re.I):

            candidate = clean_candidate(m.group(0))

            if candidate:
                candidates.append(("STRUCTURED", candidate))

    # Deduplicate
    seen = set()
    output = []

    for method, candidate in candidates:

        key = re.sub(
            r"[^a-z0-9]",
            "",
            candidate.lower()
        )

        if len(key) < 12:
            continue

        if key in seen:
            continue

        seen.add(key)

        output.append((method, candidate))

    return output


def normalize(s):

    s = s.lower()

    replacements = {
        "road": "rd",
        "marg": "rd",
        "street": "st",
        "circle": "cir",
        "bazaar": "bazar",
        "number": "no",
    }

    for a, b in replacements.items():
        s = re.sub(r"\b" + a + r"\b", b, s)

    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    return s


def get_pincode(s):

    m = re.search(r"\b[1-9]\d{5}\b", s)

    return m.group(0) if m else ""


for _, r in df.iterrows():

    raw = str(r.get("strict_address", "")).strip()

    if not raw:
        continue

    candidates = extract_addresses(raw)

    if not candidates:

        rows.append({
            "business_name": r["business_name"],
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "entity_relevance": r.get("entity_relevance", ""),
            "raw_address": raw,
            "extraction_method": "",
            "clean_address": "",
            "normalized_address": "",
            "pincode": "",
            "quality": "NO_ADDRESS"
        })

        continue

    for method, candidate in candidates:

        normalized = normalize(candidate)
        pin = get_pincode(candidate)

        # Strong validation requirements
        has_jaipur = bool(
            re.search(r"\bjaipur\b", normalized)
        )

        has_location_word = bool(
            re.search(
                r"\b(rd|road|marg|nagar|bazar|chowk|"
                r"colony|market|circle|phatak|camp|"
                r"bagh|vihar|plaza|palace|hotel|complex)\b",
                normalized
            )
        )

        # Reject suspiciously long snippets
        word_count = len(normalized.split())

        if has_jaipur and has_location_word and word_count <= 35:
            quality = "USABLE"
        elif has_jaipur and word_count <= 35:
            quality = "WEAK"
        else:
            quality = "REJECT"

        rows.append({
            "business_name": r["business_name"],
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "entity_relevance": r.get("entity_relevance", ""),
            "raw_address": raw,
            "extraction_method": method,
            "clean_address": candidate,
            "normalized_address": normalized,
            "pincode": pin,
            "quality": quality
        })


out = pd.DataFrame(rows)

out.to_excel(OUTPUT, index=False)

print("=" * 60)
print("CLEAN ADDRESS V4")
print("=" * 60)
print()
print("Extracted rows:", len(out))
print()
print("Quality:")
print(out["quality"].value_counts().to_string())
print()
print("Businesses with usable evidence:",
      out.loc[out["quality"] == "USABLE", "business_name"].nunique())
print()
print("USABLE ADDRESS SAMPLE")
print(
    out[out["quality"] == "USABLE"][
        [
            "business_name",
            "extraction_method",
            "clean_address",
            "pincode"
        ]
    ].head(60).to_string(index=False)
)
print()
print("Saved:", OUTPUT)
