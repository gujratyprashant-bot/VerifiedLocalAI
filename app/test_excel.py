import pandas as pd

file_path = "data/businesses.xlsx"

df = pd.read_excel(file_path)

print("\n✅ VerifiedLocalAI - Business Database")
print("-" * 50)

print(f"Businesses found: {len(df)}")
print(f"Columns found: {len(df.columns)}")

print("\nBusinesses:")
for name in df["business_name"]:
    print(f"  • {name}")

print("\n✅ Excel database successfully connected!")