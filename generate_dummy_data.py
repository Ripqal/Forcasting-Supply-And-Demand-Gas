import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- Configuration ---
REGIONS = [
    "SOR 1 - Sumatera Bagian Utara",
    "SOR 2 - Sumatera Bagian Selatan",
    "SOR 3 - Jawa Bagian Barat",
    "SOR 4 - Jawa Bagian Timur",
    "SOR 5 - Kalimantan",
]

# Base demand/supply per region (BBTUDH) — varies by region size
REGION_PROFILES = {
    "SOR 1 - Sumatera Bagian Utara":   {"demand_base": 320, "supply_base": 340, "volatility": 25},
    "SOR 2 - Sumatera Bagian Selatan":  {"demand_base": 280, "supply_base": 295, "volatility": 20},
    "SOR 3 - Jawa Bagian Barat":        {"demand_base": 650, "supply_base": 630, "volatility": 40},
    "SOR 4 - Jawa Bagian Timur":        {"demand_base": 520, "supply_base": 510, "volatility": 35},
    "SOR 5 - Kalimantan":               {"demand_base": 380, "supply_base": 400, "volatility": 30},
}

# Generate daily data for May 2026
start_date = datetime(2026, 5, 1)
end_date = datetime(2026, 5, 31)
num_days = (end_date - start_date).days + 1  # 31 days

np.random.seed(42)

rows = []

for region in REGIONS:
    profile = REGION_PROFILES[region]
    
    for day_idx in range(num_days):
        current_date = start_date + timedelta(days=day_idx)
        
        # Add slight weekly pattern (weekend dips)
        weekday = current_date.weekday()
        weekend_factor = 0.92 if weekday >= 5 else 1.0
        
        # Add slight trend over the month
        trend_factor = 1.0 + (day_idx / num_days) * 0.03  # ~3% growth over month
        
        demand = (
            profile["demand_base"] * weekend_factor * trend_factor
            + np.random.normal(0, profile["volatility"])
        )
        supply = (
            profile["supply_base"] * weekend_factor * trend_factor
            + np.random.normal(0, profile["volatility"] * 0.8)
        )
        
        rows.append({
            "tanggal": current_date.strftime("%Y-%m-%d"),
            "region": region,
            "demand_actual": round(max(demand, 50), 2),  # Ensure positive
            "supply_actual": round(max(supply, 50), 2),
        })

df = pd.DataFrame(rows)

# Save to CSV
output_file = "dummy_gas_data.csv"
df.to_csv(output_file, index=False)

print(f"Successfully created {output_file}")
print(f"  Rows: {len(df)}")
print(f"  Regions: {df['region'].nunique()}")
print(f"  Date range: {df['tanggal'].min()} to {df['tanggal'].max()}")
print(f"\nSample data:")
print(df.head(10).to_string(index=False))
