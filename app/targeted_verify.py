import os
import time
import pandas as pd
from dotenv import load_dotenv
from tavily import TavilyClient

INPUT = "reports/business_candidates_clean.xlsx"
OUTPUT = "reports/targeted_sources.xlsx"

load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    raise RuntimeError("TAVILY_API_KEY nahi mili")

client = TavilyClient(api_key=api_key)

df = pd.read_excel(INPUT)

results = []

for index, row in df.iterrows():

    business = str(row["business_name"]).strip()
    city = str(row["city"]).strip()

    query = f'"{business}" {city} Rajasthan restaurant'

    print(f"\n[{index + 1}/{len(df)}] Searching: {business}")

    try:
        response = client.search(
            query,
            search_depth="advanced",
            max_results=5
        )

        for result in response.get("results", []):

            results.append({
                "business_name": business,
                "city": city,
                "query": query,
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", "")
            })

        print(
            f"  Sources found: {len(response.get('results', []))}"
        )

    except Exception as e:
        print(f"  ERROR: {e}")

    time.sleep(0.5)


out = pd.DataFrame(results)

if out.empty:
    print("\nNo targeted sources found.")
    raise SystemExit()

out.to_excel(OUTPUT, index=False)

print("\n==============================")
print("TARGETED SOURCE DISCOVERY DONE")
print("==============================")
print("Businesses searched:", df["business_name"].nunique())
print("Source records:", len(out))
print("Saved:", OUTPUT)
