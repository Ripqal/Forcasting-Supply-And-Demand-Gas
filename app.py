import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Gas Forecasting Dashboard",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* App Background */
    .stApp {
        background-color: #0f172a;
        background-image: 
            radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.1) 0px, transparent 50%);
        color: #f8fafc;
    }
    
    /* Sidebar Background */
    [data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6, p, label {
        color: #f8fafc !important;
    }
    
    /* KPI Cards */
    .kpi-card {
        background: #1e293b;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 1rem;
        padding: 1.5rem;
        position: relative;
        overflow: hidden;
        margin-bottom: 1rem;
    }
    .kpi-title {
        color: #94a3b8;
        font-size: 0.95rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 700;
    }
    .kpi-unit {
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 500;
    }
    
    /* Content Boxes (Chart & Alerts) */
    .content-box {
        background: #1e293b;
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 1rem;
        padding: 1.5rem;
        height: 100%;
    }
    
    /* Region Summary Cards */
    .region-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 0.75rem;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
    }
    .region-name {
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
        color: #60a5fa;
    }
    
    /* Uploader area */
    [data-testid="stFileUploadDropzone"] {
        background-color: rgba(59, 130, 246, 0.05);
        border: 2px dashed rgba(255, 255, 255, 0.1);
        border-radius: 1rem;
    }
    
    /* Hide top padding */
    .block-container {
        padding-top: 2rem;
    }
    
    /* Unit Badge */
    .unit-badge {
        display: inline-block;
        padding: 0.3rem 0.75rem;
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.15);
        border-radius: 0.5rem;
        font-size: 0.75rem;
        color: #60a5fa;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- AVAILABLE REGIONS ---
REGIONS = [
    "SOR 1 - Sumatera Bagian Utara",
    "SOR 2 - Sumatera Bagian Selatan",
    "SOR 3 - Jawa Bagian Barat",
    "SOR 4 - Jawa Bagian Timur",
    "SOR 5 - Kalimantan",
]

# --- REQUIRED SCHEMA ---
REQUIRED_COLUMNS = ["tanggal", "region", "demand_actual", "supply_actual"]

import os
import json

# --- STATE & PERSISTENCE ---
DATA_DIR = "data_cache"
os.makedirs(DATA_DIR, exist_ok=True)

def load_cached_data():
    try:
        if os.path.exists(f"{DATA_DIR}/latest_source.csv") and os.path.exists(f"{DATA_DIR}/latest_pred.csv"):
            src = pd.read_csv(f"{DATA_DIR}/latest_source.csv")
            pred = pd.read_csv(f"{DATA_DIR}/latest_pred.csv")
            src['tanggal'] = pd.to_datetime(src['tanggal'])
            pred['tanggal'] = pd.to_datetime(pred['tanggal'])
            
            with open(f"{DATA_DIR}/latest_summary.json", "r") as f:
                summary = json.load(f)
                
            return src, pred, summary
    except Exception as e:
        pass
    return None, None, None

cached_src, cached_pred, cached_summary = load_cached_data()

if 'uploaded_data' not in st.session_state:
    st.session_state['uploaded_data'] = cached_src
if 'prediction_data' not in st.session_state:
    st.session_state['prediction_data'] = cached_pred
if 'prediction_summary' not in st.session_state:
    st.session_state['prediction_summary'] = cached_summary
if 'current_menu' not in st.session_state:
    st.session_state['current_menu'] = "Operational Dashboard"

# --- ML PREDICTION FUNCTION ---
def predict_next_month(df):
    """
    Takes daily data, predicts daily values for the next N days per region (N = len of historical data).
    Returns (prediction_df, summary_dict)
    """
    df = df.copy()
    df['tanggal'] = pd.to_datetime(df['tanggal'])
    
    # Make deterministic based on input
    try:
        sum_val = int(np.nan_to_num(pd.to_numeric(df['demand_actual'], errors='coerce')).sum() % 10000)
    except:
        sum_val = 0
    np.random.seed(len(df) + sum_val)
    
    month_names = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
        5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
        9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }
    
    def format_date_range(min_date, max_date):
        if pd.isna(min_date) or pd.isna(max_date): return "Unknown"
        if min_date.month == max_date.month and min_date.year == max_date.year:
            return f"{month_names[min_date.month]} {min_date.year}"
        return f"{month_names[min_date.month]} {min_date.year} - {month_names[max_date.month]} {max_date.year}"
        
    regions = df['region'].unique()
    prediction_rows = []
    
    for region in regions:
        rd = df[df['region'] == region].sort_values('tanggal')
        
        num_days_to_predict = len(rd)
        if num_days_to_predict == 0: continue
            
        last_date = rd['tanggal'].max()
        
        # Ensure numeric
        rd['demand_actual'] = pd.to_numeric(rd['demand_actual'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        rd['supply_actual'] = pd.to_numeric(rd['supply_actual'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        demand_mean = rd['demand_actual'].mean()
        demand_std = rd['demand_actual'].std() if len(rd) > 1 else 10
        supply_mean = rd['supply_actual'].mean()
        supply_std = rd['supply_actual'].std() if len(rd) > 1 else 10
        
        # Weekly pattern
        rd['weekday'] = rd['tanggal'].dt.weekday
        wd_demand = rd.groupby('weekday')['demand_actual'].mean()
        wd_supply = rd.groupby('weekday')['supply_actual'].mean()
        
        # Trend
        if len(rd) > 1:
            x = np.arange(len(rd))
            dt = np.polyfit(x, rd['demand_actual'].values, 1)[0]
            st_trend = np.polyfit(x, rd['supply_actual'].values, 1)[0]
        else:
            dt, st_trend = 0, 0
        
        for day_idx in range(num_days_to_predict):
            pred_date = last_date + timedelta(days=day_idx + 1)
            weekday = pred_date.weekday()
            
            wf_d = wd_demand[weekday] / demand_mean if weekday in wd_demand.index and demand_mean != 0 else 1.0
            wf_s = wd_supply[weekday] / supply_mean if weekday in wd_supply.index and supply_mean != 0 else 1.0
            
            d_pred = demand_mean * wf_d + dt * (len(rd) + day_idx) * 0.3 + np.random.normal(0, demand_std * 0.3)
            s_pred = supply_mean * wf_s + st_trend * (len(rd) + day_idx) * 0.3 + np.random.normal(0, supply_std * 0.3)
            
            prediction_rows.append({
                "tanggal": pred_date,
                "region": region,
                "demand_forecast": round(max(d_pred, 0), 2),
                "supply_forecast": round(max(s_pred, 0), 2),
            })
    
    prediction_df = pd.DataFrame(prediction_rows)
    
    # Format date strings after creating DF to compute ranges
    src_month_str = format_date_range(df['tanggal'].min(), df['tanggal'].max())
    if not prediction_df.empty:
        pred_month_str = format_date_range(prediction_df['tanggal'].min(), prediction_df['tanggal'].max())
        prediction_df['tanggal'] = prediction_df['tanggal'].dt.strftime("%Y-%m-%d")
    else:
        pred_month_str = "Unknown"
    
    summary = {
        "source_month": src_month_str,
        "prediction_month": pred_month_str,
    }
    
    return prediction_df, summary

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color: #60a5fa; margin-bottom: 1rem;'>🔥 GasForecast</h2>", unsafe_allow_html=True)
    st.markdown("<span class='unit-badge'>Satuan: BBTUDH</span>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    menu = st.radio(
        "Navigation", 
        ["Operational Dashboard", "Strategic Planning", "Data Upload", "Manual Input"],
        label_visibility="collapsed"
    )
    st.session_state['current_menu'] = menu
    
    # Region filter
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**🗺️ Filter Region/SOR**")
    selected_region = st.selectbox(
        "Region",
        ["Semua Region"] + REGIONS,
        label_visibility="collapsed"
    )

# --- PAGES ---
current_page = st.session_state['current_menu']

if current_page == "Operational Dashboard":
    # --- HEADER ---
    head_col1, head_col2 = st.columns([4, 1])
    with head_col1:
        st.markdown("<h1 style='margin-bottom: 0;'>Operational Dashboard</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #94a3b8; margin-top: -10px;'>Monitoring supply & demand gas per Region/SOR</p>", unsafe_allow_html=True)
    with head_col2:
        st.button("Upload Data 📤", use_container_width=True, type="primary")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- DATA PREP ---
    if st.session_state['prediction_data'] is not None and st.session_state['uploaded_data'] is not None:
        src_df = st.session_state['uploaded_data']
        pred_df = st.session_state['prediction_data']
        summary = st.session_state['prediction_summary']
        
        # Filter by region
        if selected_region != "Semua Region":
            src_filtered = src_df[src_df['region'] == selected_region]
            pred_filtered = pred_df[pred_df['region'] == selected_region]
        else:
            src_filtered = src_df
            pred_filtered = pred_df
        
        demand_avg = pred_filtered['demand_forecast'].mean() if len(pred_filtered) > 0 else 0
        supply_avg = src_filtered['supply_actual'].mean() if len(src_filtered) > 0 else 0
    else:
        demand_avg = 2150.0
        supply_avg = 2175.0
        
        # Generate mock data for display
        dates_src = pd.date_range('2026-05-01', periods=31, freq='D')
        dates_pred = pd.date_range('2026-06-01', periods=30, freq='D')
        
        src_df = pd.DataFrame({
            'tanggal': dates_src,
            'demand_actual': [2150 + np.random.randint(-50, 50) for _ in range(31)],
            'supply_actual': [2175 + np.random.randint(-30, 30) for _ in range(31)],
            'region': 'Semua Region'
        })
        pred_df = pd.DataFrame({
            'tanggal': dates_pred,
            'demand_forecast': [2200 + np.random.randint(-40, 40) for _ in range(30)],
            'supply_forecast': [2210 + np.random.randint(-35, 35) for _ in range(30)],
            'region': 'Semua Region'
        })
        src_filtered = src_df
        pred_filtered = pred_df
        summary = None
        
    imbalance = round(abs(demand_avg - supply_avg) / max(demand_avg, supply_avg) * 100, 2) if max(demand_avg, supply_avg) > 0 else 0
    
    region_label = selected_region if selected_region != "Semua Region" else "Semua Region"
    
    # --- KPI CARDS ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Prediksi Demand — {region_label}</div>
            <div class="kpi-value" style="color: #60a5fa">{demand_avg:,.1f} <span class="kpi-unit">BBTUDH</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Realisasi Supply — {region_label}</div>
            <div class="kpi-value" style="color: #34d399">{supply_avg:,.1f} <span class="kpi-unit">BBTUDH</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        color = "#f87171" if imbalance > 5 else "#fbbf24" if imbalance > 3 else "#34d399"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Imbalance Rate</div>
            <div class="kpi-value" style="color: {color}">{imbalance}%</div>
        </div>
        """, unsafe_allow_html=True)

    # --- MAIN CONTENT AREA ---
    content_col1, content_col2 = st.columns([2, 1])
    
    with content_col1:
        st.markdown("<div class='content-box'>", unsafe_allow_html=True)
        st.markdown("<h3>Prediksi Bulanan — Data Harian & Forecast (BBTUDH)</h3>", unsafe_allow_html=True)
        
        fig = go.Figure()
        
        # Source month actuals
        if selected_region != "Semua Region":
            src_plot = src_filtered.groupby('tanggal').agg({'demand_actual': 'sum', 'supply_actual': 'sum'}).reset_index() if 'region' in src_filtered.columns else src_filtered
            pred_plot = pred_filtered.groupby('tanggal').agg({'demand_forecast': 'sum', 'supply_forecast': 'sum'}).reset_index() if 'region' in pred_filtered.columns else pred_filtered
        else:
            src_plot = src_filtered.groupby('tanggal').agg({'demand_actual': 'sum', 'supply_actual': 'sum'}).reset_index() if 'region' in src_filtered.columns else src_filtered
            pred_plot = pred_filtered.groupby('tanggal').agg({'demand_forecast': 'sum', 'supply_forecast': 'sum'}).reset_index() if 'region' in pred_filtered.columns else pred_filtered
        
        fig.add_trace(go.Scatter(
            x=src_plot['tanggal'], y=src_plot['demand_actual'],
            mode='lines', name='Demand Aktual',
            line=dict(color='#3b82f6', width=2.5),
            fill='tozeroy', fillcolor='rgba(59, 130, 246, 0.1)'
        ))
        
        fig.add_trace(go.Scatter(
            x=src_plot['tanggal'], y=src_plot['supply_actual'],
            mode='lines', name='Supply Aktual',
            line=dict(color='#10b981', width=2.5),
            fill='tozeroy', fillcolor='rgba(16, 185, 129, 0.1)'
        ))
        
        fig.add_trace(go.Scatter(
            x=pred_plot['tanggal'], y=pred_plot['demand_forecast'],
            mode='lines', name='Demand Prediksi',
            line=dict(color='rgba(59, 130, 246, 0.6)', width=2, dash='dash'),
        ))
        
        fig.add_trace(go.Scatter(
            x=pred_plot['tanggal'], y=pred_plot['supply_forecast'],
            mode='lines', name='Supply Prediksi',
            line=dict(color='rgba(16, 185, 129, 0.6)', width=2, dash='dash'),
        ))
            
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8'),
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title='Volume (BBTUDH)'),
            hovermode='x unified', height=380, margin=dict(l=0, r=0, t=10, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with content_col2:
        st.markdown("<div class='content-box'>", unsafe_allow_html=True)
        
        alert_count = 1 if imbalance > 5 else (1 if imbalance > 3 else 0)
        
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3>Active Alerts</h3>
            <span style="background:#ef4444; color:white; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; font-weight: bold;">{alert_count}</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if imbalance > 5:
            st.error(f"**CRITICAL:** Imbalance rate tinggi ({imbalance}%). Risiko tekanan pipa turun.")
        elif imbalance > 3:
            st.warning(f"**WARNING:** Imbalance rate mencapai {imbalance}%.")
        else:
            st.markdown("<p style='color: #94a3b8;'>No active alerts at the moment.</p>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)

elif current_page == "Data Upload":
    st.header("Upload Dataset Bulanan")
    st.markdown("Upload data harian **1 bulan** → Sistem akan memprediksi **bulan berikutnya**.")
    
    # Info banner
    info_col1, info_col2, info_col3 = st.columns(3)
    with info_col1:
        st.info("📅 **Format Data**: Data harian selama 1 bulan (misal: Mei 2026)")
    with info_col2:
        st.success("🎯 **Hasil Prediksi**: Prediksi harian bulan berikutnya (misal: Juni 2026)")
    with info_col3:
        st.warning("⚡ **Satuan**: BBTUDH (Miliar British Thermal Unit Per Hari)")
    
    st.markdown("**Kolom wajib:** `tanggal`, `region`, `demand_actual`, `supply_actual`")
    st.markdown("---")
    
    uploaded_file = st.file_uploader("", type=['csv', 'xlsx', 'parquet'])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'): 
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith('.xlsx'): 
                df = pd.read_excel(uploaded_file)
            elif uploaded_file.name.endswith('.parquet'): 
                df = pd.read_parquet(uploaded_file)
            
            # Normalize column names
            df.columns = df.columns.str.strip().str.lower()
                
            missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ Kolom wajib tidak ditemukan: {missing_cols}")
                st.info(f"Kolom yang dibutuhkan: {REQUIRED_COLUMNS}")
                st.write("Kolom yang ada di file:", list(df.columns))
            else:
                with st.spinner("🔄 Menjalankan prediksi..."):
                    prediction_df, summary = predict_next_month(df)
                    st.session_state['uploaded_data'] = df
                    st.session_state['prediction_data'] = prediction_df
                    st.session_state['prediction_summary'] = summary
                    
                    # Cache to disk for persistence across refreshes
                    try:
                        df.to_csv(f"{DATA_DIR}/latest_source.csv", index=False)
                        prediction_df.to_csv(f"{DATA_DIR}/latest_pred.csv", index=False)
                        with open(f"{DATA_DIR}/latest_summary.json", "w") as f:
                            json.dump(summary, f)
                    except:
                        pass
                
                st.success(f"✅ Data **{summary['source_month']}** berhasil diproses → Prediksi **{summary['prediction_month']}** telah dibuat!")
                
                # Daily aggregated summary
                # Aggregate source by day
                df_agg = df.copy()
                df_agg['tanggal'] = pd.to_datetime(df_agg['tanggal'])
                df_agg['demand_actual'] = pd.to_numeric(df_agg['demand_actual'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                df_agg['supply_actual'] = pd.to_numeric(df_agg['supply_actual'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                daily_src = df_agg.groupby('tanggal').agg(
                    demand_actual=('demand_actual', 'sum'),
                    supply_actual=('supply_actual', 'sum')
                ).reset_index()
                
                # Aggregate prediction by day
                pred_agg = prediction_df.copy()
                pred_agg['tanggal'] = pd.to_datetime(pred_agg['tanggal'])
                daily_pred = pred_agg.groupby('tanggal').agg(
                    demand_forecast=('demand_forecast', 'sum'),
                    supply_forecast=('supply_forecast', 'sum')
                ).reset_index().round(2)
                
                src_demand_avg = daily_src['demand_actual'].mean()
                src_supply_avg = daily_src['supply_actual'].mean()
                pred_demand_avg = daily_pred['demand_forecast'].mean()
                pred_supply_avg = daily_pred['supply_forecast'].mean()
                
                demand_chg = round(((pred_demand_avg - src_demand_avg) / src_demand_avg) * 100, 2) if src_demand_avg != 0 else 0
                supply_chg = round(((pred_supply_avg - src_supply_avg) / src_supply_avg) * 100, 2) if src_supply_avg != 0 else 0
                
                # Avg per day metrics
                st.markdown("### 📊 Ringkasan Harian (Total Semua Region)")
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                with m_col1:
                    st.metric(f"Avg Demand/Hari ({summary['source_month']})", f"{src_demand_avg:,.1f} BBTUDH")
                with m_col2:
                    st.metric(f"Avg Demand/Hari ({summary['prediction_month']})", f"{pred_demand_avg:,.1f} BBTUDH", f"{demand_chg:+.2f}%")
                with m_col3:
                    st.metric(f"Avg Supply/Hari ({summary['source_month']})", f"{src_supply_avg:,.1f} BBTUDH")
                with m_col4:
                    st.metric(f"Avg Supply/Hari ({summary['prediction_month']})", f"{pred_supply_avg:,.1f} BBTUDH", f"{supply_chg:+.2f}%")
                
                # Monthly totals
                st.markdown("### 📈 Total Bulanan")
                t_col1, t_col2, t_col3, t_col4 = st.columns(4)
                with t_col1:
                    st.metric(f"Total Demand {summary['source_month']} ({len(daily_src)} hari)", f"{daily_src['demand_actual'].sum():,.0f}")
                with t_col2:
                    st.metric(f"Total Demand {summary['prediction_month']} ({len(daily_pred)} hari)", f"{daily_pred['demand_forecast'].sum():,.0f}")
                with t_col3:
                    st.metric(f"Total Supply {summary['source_month']} ({len(daily_src)} hari)", f"{daily_src['supply_actual'].sum():,.0f}")
                with t_col4:
                    st.metric(f"Total Supply {summary['prediction_month']} ({len(daily_pred)} hari)", f"{daily_pred['supply_forecast'].sum():,.0f}")
                
                # Daily prediction table
                st.markdown(f"### 📋 Prediksi Harian — {summary['prediction_month']}")
                st.caption("Total semua region per hari (BBTUDH)")
                
                daily_display = daily_pred.copy()
                daily_display['tanggal'] = daily_display['tanggal'].dt.strftime('%Y-%m-%d')
                daily_display.columns = ['Tanggal', 'Demand Forecast (BBTUDH)', 'Supply Forecast (BBTUDH)']
                daily_display.index = range(1, len(daily_display) + 1)
                daily_display.index.name = 'No'
                st.dataframe(daily_display, use_container_width=True)
                
                # Download daily prediction
                csv_data = daily_pred.to_csv(index=False)
                st.download_button(
                    label=f"📥 Download Prediksi Harian {summary['prediction_month']} (CSV)",
                    data=csv_data,
                    file_name=f"prediksi_harian_{summary['prediction_month'].replace(' ', '_')}.csv",
                    mime="text/csv",
                )
                
        except Exception as e:
            st.error(f"❌ Gagal memproses file: {str(e)}")

elif current_page == "Manual Input":
    st.header("Manual Input Data")
    st.markdown("Masukkan data operasional secara manual. Satuan: **BBTUDH**")
    
    with st.form("manual_input_form"):
        col_ts, col_reg = st.columns(2)
        with col_ts:
            input_ts = st.date_input("Tanggal", datetime.now())
        with col_reg:
            input_region = st.selectbox("Region / SOR", REGIONS)
        
        col_dem, col_sup = st.columns(2)
        with col_dem:
            input_demand = st.number_input("Demand Actual (BBTUDH)", min_value=0.0, value=500.0, step=10.0)
        with col_sup:
            input_supply = st.number_input("Supply Actual (BBTUDH)", min_value=0.0, value=500.0, step=10.0)
            
        submit_btn = st.form_submit_button("Submit Data")
        
    if submit_btn:
        new_row = pd.DataFrame([{
            "tanggal": pd.to_datetime(input_ts),
            "region": input_region,
            "demand_actual": input_demand,
            "supply_actual": input_supply
        }])
        
        # Merge with existing or create new
        if st.session_state['uploaded_data'] is not None:
            df_existing = st.session_state['uploaded_data'][REQUIRED_COLUMNS].copy()
            df_combined = pd.concat([df_existing, new_row], ignore_index=True)
        else:
            df_combined = new_row
        
        st.session_state['uploaded_data'] = df_combined
        
        # Try to run prediction if we have enough data
        if len(df_combined) >= 5:
            with st.spinner("Menjalankan prediksi..."):
                pred_df, summary = predict_next_month(df_combined)
                st.session_state['prediction_data'] = pred_df
                st.session_state['prediction_summary'] = summary
            st.success(f"✅ Data berhasil ditambahkan! Prediksi {summary['prediction_month']} diperbarui.")
        else:
            st.success("✅ Data manual berhasil ditambahkan! Upload lebih banyak data untuk prediksi.")

elif current_page == "Strategic Planning":
    st.header("Strategic Planning Dashboard")
    st.info("Modul Perencanaan Strategis (Fitur Phase 2).")
