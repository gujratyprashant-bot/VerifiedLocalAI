import os
import pandas as pd
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    raise RuntimeError("❌ TAVILY_API_KEY nahi mili")

client = TavilyClient(api_key=api_key)

query = "restaurants in Jaipur Rajasthan"

print("\n🔎 Discovering businesses...")
print(f"Query: {query}\n")

response = client.search(
    query,
    search_depth="advanced",
    max_results=10
)

results = []

for item in response.get("results", []):
    title = item.get("title", "")
    url = item.get("url", "")
    content = item.get("content", "")

    results.append({
        "search_query": query,
        "title": title,
        "url": url,
        "source_content": content,
    })

    print(f"✅ {title}")
    print(f"   {url}\n")

output_file = "reports/discovered_sources.xlsx"

df = pd.DataFrame(results)

df.to_excel(output_file, index=False)

print("=" * 60)
print(f"✅ Discovery complete")
print(f"Sources discovered: {len(df)}")
print(f"📄 Saved: {output_file}")