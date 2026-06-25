"""Test upload with NaN detection"""
import requests, json

url = "http://127.0.0.1:8001/api/v1/upload/"

with open("dummy_gas_data.csv", "rb") as f:
    response = requests.post(url, files={"file": ("dummy_gas_data.csv", f, "text/csv")})

data = response.json()
print(f"Status: {response.status_code}")

# Check for NaN values in the summary
summary = data.get('summary', {})
nan_fields = []
for key, val in summary.items():
    if key == 'daily_predictions':
        for i, dp in enumerate(val):
            for dk, dv in dp.items():
                if dv is None or (isinstance(dv, float) and str(dv) == 'nan'):
                    nan_fields.append(f"daily_predictions[{i}].{dk}")
    elif val is None or (isinstance(val, float) and str(val) == 'nan'):
        nan_fields.append(key)

if nan_fields:
    print(f"WARNING: NaN detected in: {nan_fields}")
else:
    print("No NaN values detected in summary!")

print(f"\nSummary keys: {list(summary.keys())}")
print(f"source_days: {summary.get('source_days')}")
print(f"prediction_days: {summary.get('prediction_days')}")
print(f"source_demand_avg_daily: {summary.get('source_demand_avg_daily')}")
print(f"pred_demand_avg_daily: {summary.get('pred_demand_avg_daily')}")
print(f"demand_change_pct: {summary.get('demand_change_pct')}")
print(f"daily_predictions count: {len(summary.get('daily_predictions', []))}")
print(f"First daily: {summary.get('daily_predictions', [{}])[0] if summary.get('daily_predictions') else 'EMPTY'}")

# Check the raw JSON for NaN strings
raw = response.text
if 'NaN' in raw or 'nan' in raw or 'Infinity' in raw:
    print(f"\nWARNING: Raw JSON contains NaN/Infinity!")
else:
    print(f"\nJSON is clean (no NaN/Infinity).")

print("\n--- TEST DONE ---")
