from fastapi import APIRouter
from datetime import datetime, timedelta
import random

router = APIRouter()

# Available regions
REGIONS = [
    "SOR 1 - Sumatera Bagian Utara",
    "SOR 2 - Sumatera Bagian Selatan",
    "SOR 3 - Jawa Bagian Barat",
    "SOR 4 - Jawa Bagian Timur",
    "SOR 5 - Kalimantan",
]

# Base values per region (BBTUDH)
REGION_BASES = {
    "SOR 1 - Sumatera Bagian Utara":  {"demand": 320, "supply": 340},
    "SOR 2 - Sumatera Bagian Selatan": {"demand": 280, "supply": 295},
    "SOR 3 - Jawa Bagian Barat":       {"demand": 650, "supply": 630},
    "SOR 4 - Jawa Bagian Timur":       {"demand": 520, "supply": 510},
    "SOR 5 - Kalimantan":              {"demand": 380, "supply": 400},
}


@router.get("/regions")
def get_regions():
    """Return list of available SOR regions"""
    return {"regions": REGIONS}


@router.get("/kpi")
def get_kpi(region: str = None):
    """
    Mock API for KPI Cards — values in BBTUDH.
    Optional: filter by region.
    """
    if region and region in REGION_BASES:
        base = REGION_BASES[region]
        demand = round(base["demand"] + random.uniform(-20, 20), 2)
        supply = round(base["supply"] + random.uniform(-15, 15), 2)
    else:
        # Aggregate: sum all regions
        demand = sum(b["demand"] for b in REGION_BASES.values()) + random.uniform(-50, 50)
        supply = sum(b["supply"] for b in REGION_BASES.values()) + random.uniform(-40, 40)
        demand = round(demand, 2)
        supply = round(supply, 2)

    imbalance = round(abs(demand - supply) / max(demand, supply) * 100, 2)

    status = "green"
    if imbalance > 5:
        status = "red"
    elif imbalance > 3:
        status = "yellow"

    return {
        "demand_today_bbtudh": demand,
        "supply_today_bbtudh": supply,
        "imbalance_rate_pct": imbalance,
        "status": status,
        "region": region or "Semua Region"
    }


@router.get("/monthly-chart")
def get_monthly_chart(region: str = None):
    """
    Mock API for Monthly Chart — shows daily data for current month 
    and prediction for next month.
    Values in BBTUDH.
    """
    data = []
    now = datetime.now()
    
    # Current month data (actuals) 
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Determine days passed in current month
    days_in_month = 30

    for day_idx in range(days_in_month):
        current_date = current_month_start + timedelta(days=day_idx)
        is_past = current_date.date() <= now.date()

        if region and region in REGION_BASES:
            base = REGION_BASES[region]
        else:
            # Aggregate
            base = {
                "demand": sum(b["demand"] for b in REGION_BASES.values()),
                "supply": sum(b["supply"] for b in REGION_BASES.values()),
            }

        demand_val = base["demand"] + random.uniform(-30, 30)
        supply_val = base["supply"] + random.uniform(-25, 25)

        entry = {
            "tanggal": current_date.strftime("%Y-%m-%d"),
            "demand_actual": round(demand_val, 2) if is_past else None,
            "supply_actual": round(supply_val, 2) if is_past else None,
            "demand_forecast": round(demand_val + random.uniform(-10, 10), 2),
            "supply_forecast": round(supply_val + random.uniform(-10, 10), 2),
            "is_prediction": not is_past,
            "month_type": "current"
        }
        data.append(entry)

    # Next month predictions
    next_month_start = (current_month_start + timedelta(days=32)).replace(day=1)
    for day_idx in range(30):
        pred_date = next_month_start + timedelta(days=day_idx)

        if region and region in REGION_BASES:
            base = REGION_BASES[region]
        else:
            base = {
                "demand": sum(b["demand"] for b in REGION_BASES.values()),
                "supply": sum(b["supply"] for b in REGION_BASES.values()),
            }

        demand_val = base["demand"] * (1 + random.uniform(-0.05, 0.08))
        supply_val = base["supply"] * (1 + random.uniform(-0.04, 0.06))

        entry = {
            "tanggal": pred_date.strftime("%Y-%m-%d"),
            "demand_actual": None,
            "supply_actual": None,
            "demand_forecast": round(demand_val, 2),
            "supply_forecast": round(supply_val, 2),
            "is_prediction": True,
            "month_type": "prediction"
        }
        data.append(entry)

    return data


@router.get("/alerts")
def get_alerts():
    """Mock API for Alerts"""
    return [
        {
            "id": 1,
            "type": "Under-Supply Risk",
            "severity": "Critical",
            "message": "Prediksi demand > 95% kapasitas supply tersedia",
            "timestamp": datetime.now().isoformat(),
            "resolved": False
        },
        {
            "id": 2,
            "type": "Forecast Deviation",
            "severity": "Info",
            "message": "Selisih forecast vs realisasi > 2%",
            "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
            "resolved": False
        }
    ]


# Keep backward compatibility — alias intraday to monthly-chart
@router.get("/intraday")
def get_intraday_data(region: str = None):
    """Backward-compatible alias for monthly-chart"""
    return get_monthly_chart(region)
