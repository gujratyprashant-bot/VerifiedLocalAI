from flask import Flask, request, render_template_string
from tavily import TavilyClient
from dotenv import load_dotenv
import os
import re
from urllib.parse import urlparse

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("TAVILY_API_KEY")

if not API_KEY:
    raise RuntimeError("TAVILY_API_KEY not found in .env")

tavily = TavilyClient(api_key=API_KEY)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Verified Local Intelligence</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f3f6fa;
            color: #111827;
        }

        .container {
            max-width: 1000px;
            margin: 40px auto;
            padding: 20px;
        }

        .box, .report {
            background: white;
            border-radius: 18px;
            padding: 30px;
            box-shadow: 0 8px 30px rgba(0,0,0,.07);
        }

        h1 {
            margin-top: 0;
            font-size: 38px;
        }

        .subtitle {
            color: #6b7280;
            margin-bottom: 25px;
        }

        form {
            display: flex;
            gap: 10px;
        }

        input {
            flex: 1;
            padding: 15px;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            font-size: 16px;
        }

        button {
            padding: 15px 24px;
            border: 0;
            border-radius: 10px;
            background: #111827;
            color: white;
            font-size: 16px;
            cursor: pointer;
        }

        .report {
            margin-top: 25px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            gap: 15px;
            align-items: center;
        }

        .badge {
            padding: 8px 12px;
            border-radius: 999px;
            background: #dcfce7;
            color: #166534;
            font-weight: bold;
            font-size: 13px;
        }

        .score {
            margin: 25px 0;
            padding: 20px;
            border-radius: 14px;
            background: #f9fafb;
        }

        .score-number {
            font-size: 32px;
            font-weight: bold;
        }

        .field {
            margin: 12px 0;
            line-height: 1.6;
        }

        .source {
            margin-top: 15px;
            padding: 16px;
            background: #f9fafb;
            border-radius: 12px;
        }

        .source a {
            color: #2563eb;
            word-break: break-all;
        }

        .conflict {
            margin-top: 20px;
            padding: 18px;
            border-radius: 12px;
            background: #fff7ed;
            color: #9a3412;
        }

        .agreement {
            margin-top: 20px;
            padding: 18px;
            border-radius: 12px;
            background: #ecfdf5;
            color: #166534;
        }

        .error {
            margin-top: 20px;
            padding: 15px;
            background: #fee2e2;
            color: #991b1b;
            border-radius: 10px;
        }

        .note {
            color: #6b7280;
            line-height: 1.6;
        }
.report h2 {
    font-size: 28px;
    margin-bottom: 8px;
}

.report h3 {
    margin-top: 28px;
    margin-bottom: 8px;
}

.badge {
    text-align: center;
}

@media(max-width:650px) {
    .container {
        margin: 10px auto;
        padding: 10px;
    }

    .box, .report {
        padding: 20px;
        border-radius: 14px;
    }

    h1 {
        font-size: 30px;
    }

    .score-number {
        font-size: 38px;
    }
}
        @media(max-width:650px) {
            form, .header {
                flex-direction: column;
                align-items: stretch;
            }
        }
    </style>
</head>

<body>

<div class="container">

    <div class="box">

        <h1>Verified Local Intelligence</h1>

        <div class="subtitle">
            Fresh web research → evidence extraction → source comparison
        </div>

        <form method="POST">

            <input
                name="query"
                placeholder="Enter a business name..."
                value="{{ query }}"
                autofocus
            >

            <button type="submit">
                Verify
            </button>

        </form>

        {% if error %}
            <div class="error">
                {{ error }}
            </div>
        {% endif %}

    </div>

    {% if report %}

    <div class="report">

        <div class="header">

            <h2>
                {{ report.name }}
            </h2>

            <div class="badge">
                {{ report.status }}
            </div>

        </div>

        <div class="score">

            <div class="score-number">
                {{ report.score }}%
            </div>

            <div class="note">
                Evidence confidence
            </div>

        </div>

        <h3>📍 Address</h3>

        <div class="field">
            {{ report.address }}
        </div>

        <h3>📞 Phone</h3>

        <div class="field">
            {{ report.phone }}
        </div>

        <h3>🕐 Hours</h3>

        <div class="field">
            {{ report.hours }}
        </div>

        {% if report.conflicts %}

        <div class="conflict">

            <strong>
                ⚠️ Source conflict detected
            </strong>

            {% for conflict in report.conflicts %}

            <p>
                <b>{{ conflict.field }}:</b>
                {{ conflict.message }}
            </p>

            {% endfor %}

        </div>

        {% else %}

        <div class="agreement">

            <strong>
                ✓ No major field conflicts detected
            </strong>

            <p>
                Available sources are broadly consistent
                on the extracted fields.
            </p>

        </div>

        {% endif %}

        <h3>
            🔎 Evidence Sources
        </h3>

        {% for source in report.sources %}

        <div class="source">

            <strong>
                {{ source.title }}
            </strong>

            <p>
                {{ source.content }}
            </p>

            <a
                href="{{ source.url }}"
                target="_blank"
            >
                {{ source.url }}
            </a>

        </div>

        {% endfor %}

        <h3>
            📋 Assessment
        </h3>

        <p class="note">
            {{ report.assessment }}
        </p>

        <p class="note">
            ⚠️ Web evidence does not equal physical verification.
            Physical verification must be performed separately.
        </p>

    </div>

    {% endif %}

</div>

</body>
</html>
"""


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize(value):
    value = clean_text(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def address_tokens(value):

    value = normalize(value)

    stop_words = {
        "india",
        "rajasthan",
        "jaipur",
        "road",
        "mi",
        "m",
        "i",
        "near",
        "the",
        "address",
        "contact",
        "reservation"
    }

    return {
        word
        for word in value.split()
        if len(word) > 2
        and word not in stop_words
    }

def addresses_are_consistent(a, b):

    a_normalized = normalize(a)
    b_normalized = normalize(b)

    # Broad street-level addresses
    broad_a = (
        "mi road" in a_normalized
        or "m i road" in a_normalized
    )

    broad_b = (
        "mi road" in b_normalized
        or "m i road" in b_normalized
    )

    if broad_a and broad_b:
        return True

    a_tokens = address_tokens(a)
    b_tokens = address_tokens(b)

    if not a_tokens or not b_tokens:
        return False

    common = a_tokens.intersection(b_tokens)

    similarity_a = len(common) / len(a_tokens)
    similarity_b = len(common) / len(b_tokens)

    return (
        similarity_a >= 0.50
        or similarity_b >= 0.50
    )


def extract_phone(text):

    patterns = [
        r"\+91[\s-]?\d{5}[\s-]?\d{5}",
        r"\+91[\s-]?\d{10}",
        r"\b\d{3,5}[\s-]\d{6,8}\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:
            return clean_text(
                match.group(0)
            )

    return ""


def extract_address(text):
    patterns = [
        r"\b(?:Address|address)\s*[:\-]\s*([^.\[\]\n]{8,160})",
        r"\b\d{1,5}[A-Za-z]?\s*,\s*[^.\[\]\n]{3,120},\s*(?:MI Road|M\.I\. Road|M I Road|Johri Bazar|Ajmer Road|JLN Marg|Jawahar Nagar|Adarsh Nagar|Vaishali Nagar|Bapu Bazar|Goner Road|Tonk Road|Kings Road|Station Road|Malviya Nagar|Jamdoli)\s*,?\s*Jaipur\b",
        r"\b(?:MI Road|M\.I\. Road|M I Road|Johri Bazar|Ajmer Road|JLN Marg|Jawahar Nagar|Adarsh Nagar|Vaishali Nagar|Bapu Bazar|Goner Road|Tonk Road|Kings Road|Station Road|Malviya Nagar|Jamdoli),?\s*Jaipur(?:,\s*Rajasthan)?(?:,\s*India)?\b"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue

        value = clean_text(
            match.group(1)
            if match.lastindex
            else match.group(0)
        )

        value = value.split("Location Tag:")[0]
value = value.split("LOCATION TAG:")[0]
value = value.split("Contact:")[0]

value = value.strip(" ,:-")

    if len(value) >= 8:
            return value

    return ""


def extract_hours(text):

    patterns = [

        r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\s*(?:to|-)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",

        r"(?:Opening Times|Opening Hours|Hours|Timings)\s*[:\-]\s*([^\.\[\]\n]{5,80})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:

            value = (
                match.group(1)
                if match.lastindex
                else match.group(0)
            )

            return clean_text(
                value
            )

    return ""


def compare_field(
    results,
    extractor,
    field_name
):

    values = []

    for result in results:

        text = clean_text(
            result.get(
                "content",
                ""
            )
        )

        value = extractor(
            text
        )

        if value:

            values.append({
                "value": value,
                "url": result.get(
                    "url",
                    ""
                )
            })

    if len(values) < 2:
        return None

    if field_name == "Address":

        for i in range(
            len(values)
        ):

            for j in range(
                i + 1,
                len(values)
            ):

                if not addresses_are_consistent(
                    values[i]["value"],
                    values[j]["value"]
                ):

                    return {
                        "field": field_name,
                        "message": (
                            f"{values[i]['value']} "
                            f"({urlparse(values[i]['url']).netloc}) "
                            f"vs "
                            f"{values[j]['value']} "
                            f"({urlparse(values[j]['url']).netloc})"
                        )
                    }

        return None

    normalized = {}

    for item in values:

        key = normalize(
            item["value"]
        )

        if key:

            normalized.setdefault(
                key,
                []
            ).append(
                item
            )

    if len(normalized) <= 1:
        return None

    details = []

    for items in normalized.values():

        value = items[0]["value"]

        domains = []

        for item in items:

            domain = urlparse(
                item["url"]
            ).netloc

            if (
                domain
                and domain not in domains
            ):
                domains.append(
                    domain
                )

        details.append(
            f"{value} ({', '.join(domains)})"
        )

    return {
        "field": field_name,
        "message": " vs ".join(
            details
        )
    }


def calculate_score(
    results,
    conflicts
):

    if not results:
        return 0

    unique_domains = set()

    for result in results:

        domain = urlparse(
            result.get(
                "url",
                ""
            )
        ).netloc

        if domain:
            unique_domains.add(
                domain
            )

    score = min(
        len(unique_domains) * 15,
        60
    )

    if len(results) >= 4:
        score += 15

    elif len(results) >= 3:
        score += 10

    score -= (
        len(conflicts) * 10
    )

    return max(
        0,
        min(
            score,
            100
        )
    )


def build_report(query):

    response = tavily.search(

        query=f"{query} Jaipur Rajasthan",

        search_depth="advanced",

        max_results=5,

        include_answer=True
    )

    results = response.get(
        "results",
        []
    )

    if not results:
        return None

    combined = " ".join(

        clean_text(
            result.get(
                "content",
                ""
            )
        )

        for result in results
    )

    address = extract_address(
        combined
    )

    phone = extract_phone(
        combined
    )

    hours = extract_hours(
        combined
    )

    conflicts = []

    fields = [
        (
            extract_address,
            "Address"
        ),
        (
            extract_phone,
            "Phone"
        ),
        (
            extract_hours,
            "Hours"
        )
    ]

    for extractor, field in fields:

        conflict = compare_field(
            results,
            extractor,
            field
        )

        if conflict:
            conflicts.append(
                conflict
            )

    score = calculate_score(
        results,
        conflicts
    )

    if conflicts:

        status = "REVIEW REQUIRED"

        assessment = (
            "Multiple web sources were found, but "
            "at least one important field differs "
            "between sources. The conflicting field "
            "should be reviewed before treating the "
            "information as fully verified."
        )

    elif score >= 70:

        status = "STRONG WEB SUPPORT"

        assessment = (
            "Multiple independent web sources provide "
            "supporting evidence with no major "
            "extracted-field conflict detected."
        )

    elif score >= 45:

        status = "MODERATE WEB SUPPORT"

        assessment = (
            "Several web sources provide useful "
            "evidence, but additional verification "
            "is recommended."
        )

    else:

        status = "LIMITED WEB SUPPORT"

        assessment = (
            "The available web evidence is limited. "
            "Additional sources or physical "
            "verification are recommended."
        )

    return {

        "name": query,

        "score": score,

        "status": status,

        "address": (
            address
            or "Not confidently extracted"
        ),

        "phone": (
            phone
            or "Not found in current evidence"
        ),

        "hours": (
            hours
            or "Not found in current evidence"
        ),

        "sources": results,

        "conflicts": conflicts,

        "assessment": assessment
    }
@app.route("/report/<business_name>")
def public_report(business_name):
    report = build_report(business_name)

    if not report:
        return "Business not found", 404

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>{{ report.name }} — Verified Local Intelligence</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background: #f6f7f9;
        }
        .card {
            background: white;
            padding: 28px;
            border-radius: 16px;
            margin-bottom: 20px;
            box-shadow: 0 4px 18px rgba(0,0,0,.06);
        }
        .score {
            font-size: 42px;
            font-weight: bold;
        }
        .status {
            font-weight: bold;
            font-size: 20px;
        }
        .field {
            margin: 18px 0;
        }
        .label {
            font-weight: bold;
            color: #666;
        }
    </style>
</head>
<body>

<div class="card">
    <h1>{{ report.name }}</h1>
    <div class="status">{{ report.status }}</div>
    <div class="score">{{ report.score }}%</div>
    <p>Evidence confidence</p>
</div>

<div class="card">
    <div class="field">
        <div class="label">📍 Address</div>
        <div>{{ report.address }}</div>
    </div>

    <div class="field">
        <div class="label">📞 Phone</div>
        <div>{{ report.phone }}</div>
    </div>

    <div class="field">
        <div class="label">🕐 Hours</div>
        <div>{{ report.hours }}</div>
    </div>
</div>

<div class="card">
    <h2>Assessment</h2>
    <p>{{ report.assessment }}</p>
</div>

<div class="card">
    <h2>Verification Notice</h2>
    <p>
        Web evidence does not equal physical verification.
        Physical verification must be performed separately.
    </p>
</div>

</body>
</html>
    """, report=report)
@app.route("/api/verify", methods=["POST"])
def api_verify():

    data = request.get_json(silent=True) or {}

    query = clean_text(
        data.get("query", "")
    )

    if not query:
        return {
            "error": "Enter a business name."
        }, 400

    try:
        report = build_report(query)

        if not report:
            return {
                "error": "No useful web evidence found."
            }, 404

        return report, 200

    except Exception as e:
        return {
            "error": str(e)
        }, 500
@app.route(
    "/",
    methods=["GET", "POST"]
)
def home():

    query = ""

    report = None

    error = ""

    if request.method == "POST":

        query = request.form.get(
            "query",
            ""
        ).strip()

        if not query:

            error = (
                "Enter a business name."
            )

        else:

            try:

                report = build_report(
                    query
                )

                if not report:

                    error = (
                        "No useful web evidence found."
                    )

            except Exception as e:

                error = (
                    f"Research failed: {e}"
                )

    return render_template_string(
        HTML,
        query=query,
        report=report,
        error=error
    )


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )