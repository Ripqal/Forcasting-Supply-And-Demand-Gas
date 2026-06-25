from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import pandas as pd
import numpy as np
import io
import json
import math

from backend.services.ml_service import forecaster

router = APIRouter()


def sanitize_for_json(obj):
    """Recursively replace NaN/Infinity values with None/0 for safe JSON serialization."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
        return obj
    elif isinstance(obj, (np.floating, np.integer)):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return 0.0
        return val
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, (np.ndarray,)):
        return sanitize_for_json(obj.tolist())
    elif isinstance(obj, pd.Timestamp):
        return obj.strftime('%Y-%m-%d')
    return obj

# Schema for validation
REQUIRED_COLUMNS = [
    "tanggal",
    "region",
    "demand_actual",
    "supply_actual"
]


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload daily data for one month → get predictions for the next month.
    Required columns: tanggal, region, demand_actual, supply_actual
    Unit: MMSCFD (Million Standard Cubic Feet per Day)
    """
    if not file.filename.endswith(('.csv', '.xlsx', '.parquet')):
        raise HTTPException(
            status_code=400,
            detail="Format file tidak valid. Hanya CSV, XLSX, dan Parquet yang diizinkan."
        )

    contents = await file.read()

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(contents))
        elif file.filename.endswith('.parquet'):
            df = pd.read_parquet(io.BytesIO(contents))

        # Normalize column names (strip whitespace, lowercase)
        df.columns = df.columns.str.strip().str.lower()

        # Validate schema
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise HTTPException(
                status_code=400,
                detail=f"Kolom wajib tidak ditemukan: {missing_cols}. "
                       f"Kolom yang dibutuhkan: {REQUIRED_COLUMNS}"
            )

        # Validate data types
        df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce', dayfirst=True)
        df['demand_actual'] = pd.to_numeric(df['demand_actual'], errors='coerce')
        df['supply_actual'] = pd.to_numeric(df['supply_actual'], errors='coerce')

        # Check for NaN values after conversion
        nan_dates = df['tanggal'].isna().sum()
        if nan_dates > 0:
            raise HTTPException(status_code=400, detail=f"Data tidak valid: {nan_dates} baris memiliki format tanggal yang tidak dikenali.")

        nan_demand = df['demand_actual'].isna().sum()
        nan_supply = df['supply_actual'].isna().sum()
        if nan_demand > 0 or nan_supply > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Data tidak valid: {nan_demand} baris demand dan {nan_supply} baris supply "
                       f"tidak dapat dikonversi ke angka."
            )

        # Detect source month info
        source_month = df['tanggal'].dt.month.mode()[0]
        source_year = df['tanggal'].dt.year.mode()[0]
        month_names = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
            5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
            9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }

        # Run ML prediction for next month
        prediction_df = forecaster.predict(df)

        # Generate summary
        summary = forecaster.get_summary(df, prediction_df)

        # Build response
        response_data = sanitize_for_json({
            "status": "success",
            "message": (
                f"Data {month_names[source_month]} {source_year} berhasil diproses. "
                f"Prediksi untuk {summary['prediction_month']} telah dibuat."
            ),
            "rows_processed": len(df),
            "rows_predicted": len(prediction_df),
            "source_month": summary["source_month"],
            "prediction_month": summary["prediction_month"],
            "regions": df['region'].unique().tolist(),
            "summary": summary,
            "source_preview": df.head(5).assign(
                tanggal=df['tanggal'].dt.strftime('%Y-%m-%d')
            ).to_dict(orient='records'),
            # Daily aggregated predictions (sum all regions per day)
            "daily_predictions": summary.get("daily_predictions", []),
            "source_data": df.assign(tanggal=df['tanggal'].dt.strftime('%Y-%m-%d')).to_dict(orient='records'),
            "prediction_data": prediction_df.assign(tanggal=prediction_df['tanggal'].dt.strftime('%Y-%m-%d')).to_dict(orient='records'),
        })

        return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal memproses file: {str(e)}"
        )


@router.post("/download-prediction")
async def download_prediction(file: UploadFile = File(...)):
    """
    Same as upload, but returns the prediction as a downloadable CSV.
    """
    if not file.filename.endswith(('.csv', '.xlsx', '.parquet')):
        raise HTTPException(status_code=400, detail="Format file tidak valid.")

    contents = await file.read()

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(contents))
        elif file.filename.endswith('.parquet'):
            df = pd.read_parquet(io.BytesIO(contents))

        df.columns = df.columns.str.strip().str.lower()

        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise HTTPException(status_code=400, detail=f"Kolom wajib tidak ditemukan: {missing_cols}")

        prediction_df = forecaster.predict(df)

        csv_buffer = io.StringIO()
        prediction_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        return StreamingResponse(
            io.BytesIO(csv_buffer.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=prediksi_bulan_depan.csv"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses file: {str(e)}")
