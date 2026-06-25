import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import calendar


class MonthlyForecaster:
    """
    Forecaster that takes daily data for one month and predicts 
    daily values for the next month, per region.
    """

    def __init__(self):
        self.model_loaded = True

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Given a DataFrame with columns [tanggal, region, demand_actual, supply_actual],
        produce a prediction DataFrame for the NEXT month with columns:
        [tanggal, region, demand_forecast, supply_forecast]
        """
        if not self.model_loaded:
            raise Exception("Model not loaded")

        df = df.copy()
        df['tanggal'] = pd.to_datetime(df['tanggal'])
        
        # Make predictions deterministic based on the input data size
        try:
            sum_val = int(np.nan_to_num(df['demand_actual']).sum() % 10000)
        except:
            sum_val = 0
        np.random.seed(len(df) + sum_val)

        # Detect which month the data is from (use the most common month)
        source_month = df['tanggal'].dt.month.mode()[0]
        source_year = df['tanggal'].dt.year.mode()[0]

        # Calculate next month
        if source_month == 12:
            next_month = 1
            next_year = source_year + 1
        else:
            next_month = source_month + 1
            next_year = source_year

        num_days_next = calendar.monthrange(next_year, next_month)[1]

        regions = df['region'].unique()
        prediction_rows = []

        for region in regions:
            region_data = df[df['region'] == region].sort_values('tanggal')

            # Calculate statistics from source month
            demand_mean = region_data['demand_actual'].mean()
            demand_std = region_data['demand_actual'].std()
            supply_mean = region_data['supply_actual'].mean()
            supply_std = region_data['supply_actual'].std()

            # Detect weekly pattern
            region_data['weekday'] = region_data['tanggal'].dt.weekday
            weekday_demand = region_data.groupby('weekday')['demand_actual'].mean()
            weekday_supply = region_data.groupby('weekday')['supply_actual'].mean()

            # Detect trend (simple linear)
            if len(region_data) > 1:
                x = np.arange(len(region_data))
                demand_trend = np.polyfit(x, region_data['demand_actual'].values, 1)[0]
                supply_trend = np.polyfit(x, region_data['supply_actual'].values, 1)[0]
            else:
                demand_trend = 0
                supply_trend = 0

            # Generate predictions for next month
            for day_idx in range(num_days_next):
                pred_date = datetime(next_year, next_month, day_idx + 1)
                weekday = pred_date.weekday()

                # Base = mean + continued trend + weekly pattern adjustment
                trend_offset = demand_trend * (len(region_data) + day_idx)
                
                # Weekly pattern factor
                if weekday in weekday_demand.index:
                    weekday_factor_demand = weekday_demand[weekday] / demand_mean
                    weekday_factor_supply = weekday_supply[weekday] / supply_mean
                else:
                    weekday_factor_demand = 1.0
                    weekday_factor_supply = 1.0

                demand_pred = (
                    demand_mean * weekday_factor_demand
                    + trend_offset * 0.3  # Dampen the trend extrapolation
                    + np.random.normal(0, demand_std * 0.3)  # Reduced noise
                )

                supply_trend_offset = supply_trend * (len(region_data) + day_idx)
                supply_pred = (
                    supply_mean * weekday_factor_supply
                    + supply_trend_offset * 0.3
                    + np.random.normal(0, supply_std * 0.3)
                )

                prediction_rows.append({
                    "tanggal": pred_date.strftime("%Y-%m-%d"),
                    "region": region,
                    "demand_forecast": round(max(demand_pred, 0), 2),
                    "supply_forecast": round(max(supply_pred, 0), 2),
                })

        prediction_df = pd.DataFrame(prediction_rows)
        return prediction_df

    def get_daily_prediction(self, prediction_df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate prediction per day (sum all regions for each day).
        Returns DataFrame with columns: [tanggal, demand_forecast, supply_forecast]
        """
        pred = prediction_df.copy()
        pred['tanggal'] = pd.to_datetime(pred['tanggal'])

        # Ensure numeric
        pred['demand_forecast'] = pd.to_numeric(pred['demand_forecast'], errors='coerce').fillna(0)
        pred['supply_forecast'] = pd.to_numeric(pred['supply_forecast'], errors='coerce').fillna(0)

        daily = pred.groupby('tanggal').agg(
            demand_forecast=('demand_forecast', 'sum'),
            supply_forecast=('supply_forecast', 'sum')
        ).reset_index().fillna(0)

        daily['demand_forecast'] = daily['demand_forecast'].round(2)
        daily['supply_forecast'] = daily['supply_forecast'].round(2)
        daily['tanggal'] = daily['tanggal'].dt.strftime('%Y-%m-%d')

        return daily.sort_values('tanggal')

    def get_daily_source(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate source data per day (sum all regions for each day).
        Returns DataFrame with columns: [tanggal, demand_actual, supply_actual]
        """
        src = source_df.copy()
        src['tanggal'] = pd.to_datetime(src['tanggal'])

        # Ensure numeric
        src['demand_actual'] = pd.to_numeric(src['demand_actual'], errors='coerce').fillna(0)
        src['supply_actual'] = pd.to_numeric(src['supply_actual'], errors='coerce').fillna(0)

        daily = src.groupby('tanggal').agg(
            demand_actual=('demand_actual', 'sum'),
            supply_actual=('supply_actual', 'sum')
        ).reset_index().fillna(0)

        daily['demand_actual'] = daily['demand_actual'].round(2)
        daily['supply_actual'] = daily['supply_actual'].round(2)
        daily['tanggal'] = daily['tanggal'].dt.strftime('%Y-%m-%d')

        return daily.sort_values('tanggal')

    @staticmethod
    def _safe_float(val, default=0.0):
        """Convert value to a safe float (no NaN/Inf)."""
        try:
            f = float(val)
            if pd.isna(f) or np.isinf(f):
                return default
            return f
        except (ValueError, TypeError):
            return default

    def get_summary(self, source_df: pd.DataFrame, prediction_df: pd.DataFrame) -> dict:
        """
        Generate a summary comparing source month vs predicted month.
        Aggregated by day (total all regions per day).
        """
        source_df = source_df.copy()
        prediction_df = prediction_df.copy()

        source_df['tanggal'] = pd.to_datetime(source_df['tanggal'])
        prediction_df['tanggal'] = pd.to_datetime(prediction_df['tanggal'])

        # Ensure numeric columns
        source_df['demand_actual'] = pd.to_numeric(source_df['demand_actual'], errors='coerce').fillna(0)
        source_df['supply_actual'] = pd.to_numeric(source_df['supply_actual'], errors='coerce').fillna(0)
        prediction_df['demand_forecast'] = pd.to_numeric(prediction_df['demand_forecast'], errors='coerce').fillna(0)
        prediction_df['supply_forecast'] = pd.to_numeric(prediction_df['supply_forecast'], errors='coerce').fillna(0)

        source_month = int(source_df['tanggal'].dt.month.mode()[0])
        source_year = int(source_df['tanggal'].dt.year.mode()[0])
        pred_month = int(prediction_df['tanggal'].dt.month.mode()[0])
        pred_year = int(prediction_df['tanggal'].dt.year.mode()[0])

        # Month names in Indonesian
        month_names = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
            5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
            9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }

        # Daily aggregation (sum all regions per day)
        daily_src = source_df.groupby('tanggal').agg(
            demand_actual=('demand_actual', 'sum'),
            supply_actual=('supply_actual', 'sum')
        ).reset_index().fillna(0)

        daily_pred = prediction_df.groupby('tanggal').agg(
            demand_forecast=('demand_forecast', 'sum'),
            supply_forecast=('supply_forecast', 'sum')
        ).reset_index().fillna(0)

        # Daily averages and totals — use _safe_float to prevent NaN in JSON
        sf = self._safe_float

        src_demand_avg_daily = sf(daily_src['demand_actual'].mean())
        src_supply_avg_daily = sf(daily_src['supply_actual'].mean())
        src_demand_total = sf(daily_src['demand_actual'].sum())
        src_supply_total = sf(daily_src['supply_actual'].sum())

        pred_demand_avg_daily = sf(daily_pred['demand_forecast'].mean())
        pred_supply_avg_daily = sf(daily_pred['supply_forecast'].mean())
        pred_demand_total = sf(daily_pred['demand_forecast'].sum())
        pred_supply_total = sf(daily_pred['supply_forecast'].sum())

        demand_change_pct = round(
            ((pred_demand_avg_daily - src_demand_avg_daily) / src_demand_avg_daily) * 100, 2
        ) if src_demand_avg_daily != 0 else 0.0

        supply_change_pct = round(
            ((pred_supply_avg_daily - src_supply_avg_daily) / src_supply_avg_daily) * 100, 2
        ) if src_supply_avg_daily != 0 else 0.0

        # Build daily prediction list for the table
        daily_prediction_list = []
        for _, row in daily_pred.iterrows():
            tanggal_val = row['tanggal']
            # Handle both Timestamp and string
            if hasattr(tanggal_val, 'strftime'):
                tanggal_str = tanggal_val.strftime('%Y-%m-%d')
            else:
                tanggal_str = str(tanggal_val)

            daily_prediction_list.append({
                "tanggal": tanggal_str,
                "demand_forecast": round(sf(row['demand_forecast']), 2),
                "supply_forecast": round(sf(row['supply_forecast']), 2),
            })

        summary = {
            "source_month": f"{month_names[source_month]} {source_year}",
            "prediction_month": f"{month_names[pred_month]} {pred_year}",
            "source_days": int(len(daily_src)),
            "prediction_days": int(len(daily_pred)),
            "source_demand_avg_daily": round(src_demand_avg_daily, 2),
            "source_supply_avg_daily": round(src_supply_avg_daily, 2),
            "source_demand_total": round(src_demand_total, 2),
            "source_supply_total": round(src_supply_total, 2),
            "pred_demand_avg_daily": round(pred_demand_avg_daily, 2),
            "pred_supply_avg_daily": round(pred_supply_avg_daily, 2),
            "pred_demand_total": round(pred_demand_total, 2),
            "pred_supply_total": round(pred_supply_total, 2),
            "demand_change_pct": sf(demand_change_pct),
            "supply_change_pct": sf(supply_change_pct),
            "daily_predictions": daily_prediction_list,
        }

        return summary


# Singleton instance
forecaster = MonthlyForecaster()
