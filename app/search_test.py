import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    raise RuntimeError("❌ TAVILY_API_KEY nahi mili")

client = TavilyClient(api_key=api_key)

response = client.search(
    "best restaurants in Jaipur Rajasthan",
    max_results=5
)

print("\n🔎 SEARCH RESULTS\n")

for i, result in enumerate(response["results"], 1):
    print(f"{i}. {result.get('title')}")
    print(f"   {result.get('url')}")
    print()
    
print("✅ Tavily source discovery working!")