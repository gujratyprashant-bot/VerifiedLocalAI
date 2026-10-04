import pandas as pd
import re

INPUT = "reports/strict_evidence_v2.xlsx"
OUTPUT = "reports/clean_address_v3.xlsx"

df = pd.read_excel(INPUT)

rows = []

STOP_WORDS = [
    "directioncopy",
    "report an error",
    "similar restaurants",
    "similar hotels",
    "read more",
    "view in map",
    "book now",
    "open now",
    "currently closed",
    "dropdown",
    "photos",
    "menu",
    "reviews",
    "rating",
    "delivery",
    "order online",
    "more restaurants",
    "people who viewed",
]

def clean_text(s):
    s = str(s)

    s = re.sub(r"#+", " ", s)
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = re.sub(r"\([^)]{0,100}\)", " ", s)

    # ASCII-safe separator cleanup
    s = s.replace("|", " ")
    s = s.replace(";", " ")
    s = s.replace(":", " ")

    s = re.sub(r"\s+", " ", s).strip()

    return s


def cut_noise(text):
    low = text.lower()
    positions = []

    for word in STOP_WORDS:
        p = low.find(word)
        if p > 10:
            positions.append(p)

    if positions:
        text = text[:min(positions)]

    return text.strip(" .,:;-")


def extract_after_label(text):
    low = text.lower()

    patterns = [
        "address",
        "located at",
        "location",
        "situated at",
        "visit us at",
        "find us at",
        "direction"
    ]

    for label in patterns:
        pos = low.find(label)

        if pos >= 0:
            result = text[pos + len(label):]
            result = result.lstrip(" :-")
            return result

    return text


def find_pincode(text):
    m = re.search(r"\b[1-9]\d{5}\b", text)
    return m.group(0) if m else ""


def find_jaipur_segment(text):

    low = text.lower()

    positions = [
        m.start()
        for m in re.finditer(r"\bjaipur\b", low)
    ]

    if not positions:
        return ""

    pos = positions[0]

    start = max(0, pos - 180)

    segment = text[start:pos + 40]

    segment = re.sub(
        r"^(.*?)(?:address|location|direction)\s*[-:]?\s*",
        "",
        segment,
        flags=re.I
    )

    return segment.strip(" .,:;-")


def normalize_address(addr):

    addr = addr.lower()

    replacements = [
        (r"\broad\b", "rd"),
        (r"\bmarg\b", "rd"),
        (r"\bstreet\b", "st"),
        (r"\bcircle\b", "cir"),
        (r"\bnumber\b", "no"),
        (r"\bno\.\b", "no")
    ]

    for pattern, replacement in replacements:
        addr = re.sub(pattern, replacement, addr)

    addr = re.sub(r"[^a-z0-9 ]+", " ", addr)
    addr = re.sub(r"\s+", " ", addr).strip()

    return addr


for _, r in df.iterrows():

    raw = str(r.get("strict_address", "")).strip()

    if not raw:
        continue

    text = clean_text(raw)

    text = cut_noise(text)

    text = extract_after_label(text)

    candidate = find_jaipur_segment(text)

    if not candidate:
        candidate = text

    candidate = re.sub(
        r"^(?:address|location|direction|directions)\s*[-:]?\s*",
        "",
        candidate,
        flags=re.I
    )

    candidate = cut_noise(candidate)

    pin = find_pincode(candidate)

    normalized = normalize_address(candidate)

    has_jaipur = "jaipur" in normalized

    has_address_signal = bool(
        re.search(
            r"\b(rd|road|marg|circle|nagar|bazar|bazaar|chowk|"
            r"colony|market|camp|phatak|palace|hotel|plaza|"
            r"complex|vihar|bagh|farm|station|jln)\b",
            normalized
        )
    )

    if has_jaipur and has_address_signal:
        quality = "USABLE"
    elif has_jaipur:
        quality = "WEAK"
    else:
        quality = "REJECT"

    rows.append({
        "business_name": r["business_name"],
        "title": r.get("title", ""),
        "url": r.get("url", ""),
        "entity_relevance": r.get("entity_relevance", ""),
        "raw_address": raw,
        "clean_address": candidate,
        "normalized_address": normalized,
        "pincode": pin,
        "quality": quality
    })


out = pd.DataFrame(rows)

out.to_excel(OUTPUT, index=False)

print("=" * 60)
print("CLEAN ADDRESS V3")
print("=" * 60)
print()
print("Records:", len(out))
print()
print("Quality:")
print(out["quality"].value_counts().to_string())
print()
print("USABLE:", (out["quality"] == "USABLE").sum())
print("WEAK:", (out["quality"] == "WEAK").sum())
print("REJECT:", (out["quality"] == "REJECT").sum())
print()
print("Sample cleaned addresses:")
print(
    out[out["quality"] == "USABLE"][
        ["business_name", "clean_address", "pincode"]
    ].head(40).to_string(index=False)
)
print()
print("Saved:", OUTPUT)
