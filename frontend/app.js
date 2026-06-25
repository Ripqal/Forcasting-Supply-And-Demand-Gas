// Initialize Lucide Icons
lucide.createIcons();

// --- STATE & CONFIG ---
const API_BASE = '/api/v1';
let forecastChartInstance = null;
let selectedFile = null;
let currentRegion = ''; // Region filter state
let lastUploadResult = null; // Store upload result for download

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
    setupNavigation();
    setupModalUpload();
    setupPageUpload();
    setupManualInput();
    setupRegionFilter();
});

// =============================================================================
// NAVIGATION
// =============================================================================
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();

            const target = item.getAttribute('data-target');

            // Remove active from all, add to clicked
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            // Hide all view sections
            document.querySelectorAll('.view-section').forEach(v => v.classList.add('hidden'));

            // Show the matching view
            const viewEl = document.getElementById(target + '-view');
            if (viewEl) {
                viewEl.classList.remove('hidden');
                // Re-render lucide icons for newly visible content
                lucide.createIcons();
            }
        });
    });
}

// =============================================================================
// REGION FILTER
// =============================================================================
function setupRegionFilter() {
    const regionSelect = document.getElementById('region-filter');
    if (!regionSelect) return;

    regionSelect.addEventListener('change', (e) => {
        currentRegion = e.target.value;
        loadDashboardData();
    });
}

// =============================================================================
// DATA FETCHING (with timeout + mock fallback)
// =============================================================================
function fetchWithTimeout(url, options = {}, timeoutMs = 3000) {
    return Promise.race([
        fetch(url, options),
        new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Request timed out')), timeoutMs)
        )
    ]);
}

async function fetchWithFallback(url, mockData) {
    try {
        const response = await fetchWithTimeout(url);
        if (!response.ok) throw new Error('Network response was not ok');
        return await response.json();
    } catch (error) {
        console.warn(`API unavailable (${url}), using mock data.`);
        return mockData;
    }
}

async function loadDashboardData() {
    const regionParam = currentRegion ? `?region=${encodeURIComponent(currentRegion)}` : '';
    
    // Check localStorage first
    const stored = localStorage.getItem('dashboardData');
    if (stored) {
        try {
            const parsed = JSON.parse(stored);
            let srcData = parsed.source_data || [];
            let predData = parsed.prediction_data || [];
            
            if (currentRegion && currentRegion !== "Semua Region") {
                srcData = srcData.filter(d => d.region === currentRegion);
                predData = predData.filter(d => d.region === currentRegion);
            }
            
            const aggData = (arr, isPred) => {
                const map = {};
                arr.forEach(row => {
                    if(!map[row.tanggal]) map[row.tanggal] = {
                        tanggal: row.tanggal,
                        demand_actual: null, supply_actual: null,
                        demand_forecast: null, supply_forecast: null,
                        is_prediction: isPred,
                        month_type: isPred ? 'prediction' : 'current'
                    };
                    if(!isPred) {
                        map[row.tanggal].demand_actual = (map[row.tanggal].demand_actual || 0) + (row.demand_actual || 0);
                        map[row.tanggal].supply_actual = (map[row.tanggal].supply_actual || 0) + (row.supply_actual || 0);
                    } else {
                        map[row.tanggal].demand_forecast = (map[row.tanggal].demand_forecast || 0) + (row.demand_forecast || 0);
                        map[row.tanggal].supply_forecast = (map[row.tanggal].supply_forecast || 0) + (row.supply_forecast || 0);
                    }
                });
                return Object.values(map).sort((a,b) => new Date(a.tanggal) - new Date(b.tanggal));
            };
            
            // Dynamically populate region dropdown to match actual data
            const regionSelect = document.getElementById('region-filter');
            if (regionSelect && parsed.regions && JSON.stringify(window.lastLoadedRegions) !== JSON.stringify(parsed.regions)) {
                window.lastLoadedRegions = parsed.regions;
                regionSelect.innerHTML = '<option value="">Semua Region</option>';
                parsed.regions.forEach(r => {
                    const opt = document.createElement('option');
                    opt.value = r;
                    opt.textContent = r;
                    regionSelect.appendChild(opt);
                });
                if (parsed.regions.includes(currentRegion)) {
                    regionSelect.value = currentRegion;
                } else {
                    currentRegion = '';
                    regionSelect.value = '';
                }
            }
            
            const aggSrc = aggData(srcData, false);
            const aggPred = aggData(predData, true);
            
            // Connecting actual and predicted lines for the chart
            if (aggSrc.length > 0 && aggPred.length > 0) {
                const lastActual = aggSrc[aggSrc.length - 1];
                const bridgePoint = {
                    tanggal: lastActual.tanggal,
                    demand_actual: null, supply_actual: null,
                    demand_forecast: lastActual.demand_actual, 
                    supply_forecast: lastActual.supply_actual,
                    is_prediction: true,
                    month_type: 'prediction'
                };
                aggPred.unshift(bridgePoint);
            }
            
            // Slicing chartData to show "Realisasi Bulan Ini" (last 30 days) and "Prediksi Bulan Depan" (first 31 days)
            const recentSrc = aggSrc.slice(-30);
            const nearPred = aggPred.slice(0, 31);
            const chartData = [...recentSrc, ...nearPred];
            renderChart(chartData);
            
            const pred_demand_avg = aggPred.length > 0 ? aggPred.reduce((a,b)=>a+b.demand_forecast,0)/aggPred.length : 0;
            const pred_supply_avg = aggPred.length > 0 ? aggPred.reduce((a,b)=>a+b.supply_forecast,0)/aggPred.length : 0;
            const actual_demand_avg = aggSrc.length > 0 ? aggSrc.reduce((a,b)=>a+b.demand_actual,0)/aggSrc.length : 0;
            const actual_supply_avg = aggSrc.length > 0 ? aggSrc.reduce((a,b)=>a+b.supply_actual,0)/aggSrc.length : 0;
            
            const imbalance = Math.max(pred_demand_avg, pred_supply_avg) > 0 ? Math.abs(pred_demand_avg - pred_supply_avg) / Math.max(pred_demand_avg, pred_supply_avg) * 100 : 0;
            
            const kpiData = {
                actual_demand_mmscfd: actual_demand_avg,
                actual_supply_mmscfd: actual_supply_avg,
                pred_demand_mmscfd: pred_demand_avg,
                pred_supply_mmscfd: pred_supply_avg,
                imbalance_rate_pct: imbalance,
                status: imbalance > 5 ? 'red' : (imbalance > 3 ? 'yellow' : 'green'),
                region: currentRegion || "Semua Region"
            };
            renderKPIs(kpiData);
            
            // Dynamic Alerts Generation
            const dynamicAlerts = [];
            if (pred_demand_avg > pred_supply_avg * 0.95) {
                dynamicAlerts.push({
                    id: 1, type: "Under-Supply Risk", severity: "Critical", 
                    message: `Prediksi demand (${formatNumber(pred_demand_avg)} MMSCFD) mendekati atau melebihi prediksi supply (${formatNumber(pred_supply_avg)} MMSCFD).`, 
                    timestamp: new Date().toISOString()
                });
            }
            if (Math.abs(actual_demand_avg - actual_supply_avg) / Math.max(actual_demand_avg, actual_supply_avg) > 0.05) {
                dynamicAlerts.push({
                    id: 2, type: "High Historical Imbalance", severity: "Warning", 
                    message: "Terdapat selisih >5% antara Realisasi Supply dan Demand historis.", 
                    timestamp: new Date(Date.now() - 3600000).toISOString()
                });
            }
            if (dynamicAlerts.length === 0) {
                dynamicAlerts.push({
                    id: 3, type: "Status Normal", severity: "Info", 
                    message: "Pasokan gas diprediksi aman untuk bulan depan berdasarkan tren.", 
                    timestamp: new Date().toISOString()
                });
            }
            renderAlerts(dynamicAlerts);
            return;
        } catch (e) {
            console.error('Error parsing localStorage dashboardData', e);
        }
    }

    // 1. Fetch KPIs
    const kpiData = await fetchWithFallback(`${API_BASE}/dashboard/kpi${regionParam}`, {
        actual_demand_mmscfd: 2120.0,
        actual_supply_mmscfd: 2150.0,
        pred_demand_mmscfd: 2150.0,
        pred_supply_mmscfd: 2175.0,
        imbalance_rate_pct: 1.16,
        status: 'green',
        region: currentRegion || 'Semua Region'
    });
    renderKPIs(kpiData);

    // 2. Fetch Alerts
    const alertsData = await fetchWithFallback(`${API_BASE}/dashboard/alerts`, [
        { id: 1, type: "Under-Supply Risk", severity: "Critical", message: "Prediksi demand > 95% kapasitas supply tersedia", timestamp: new Date().toISOString() },
        { id: 2, type: "Forecast Deviation", severity: "Info", message: "Selisih forecast vs realisasi > 2% di SOR 3", timestamp: new Date(Date.now() - 3600000).toISOString() }
    ]);
    renderAlerts(alertsData);

    // 3. Fetch Chart Data
    const chartData = await fetchWithFallback(
        `${API_BASE}/dashboard/monthly-chart${regionParam}`,
        generateMockChartData()
    );
    renderChart(chartData);
}

// =============================================================================
// RENDERERS
// =============================================================================
function formatNumber(val) {
    const n = Number(val);
    if (isNaN(n) || !isFinite(n) || val === null || val === undefined) return '0';
    return new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 }).format(n);
}

function renderKPIs(data) {
    const container = document.getElementById('kpi-container');
    container.innerHTML = '';

    const kpis = [
        {
            title: `Realisasi Demand — ${data.region || 'Semua Region'}`,
            value: `${formatNumber(data.actual_demand_mmscfd)}`,
            unit: 'MMSCFD',
            trend: 'Historis',
            trendClass: 'trend-up',
            icon: 'bar-chart-2'
        },
        {
            title: `Prediksi Demand — ${data.region || 'Semua Region'}`,
            value: `${formatNumber(data.pred_demand_mmscfd)}`,
            unit: 'MMSCFD',
            trend: 'Bulan Depan',
            trendClass: 'trend-up',
            icon: 'trending-up'
        },
        {
            title: `Realisasi Supply — ${data.region || 'Semua Region'}`,
            value: `${formatNumber(data.actual_supply_mmscfd)}`,
            unit: 'MMSCFD',
            trend: 'Historis',
            trendClass: 'trend-up',
            icon: 'bar-chart-2'
        },
        {
            title: `Prediksi Supply — ${data.region || 'Semua Region'}`,
            value: `${formatNumber(data.pred_supply_mmscfd)}`,
            unit: 'MMSCFD',
            trend: 'Bulan Depan',
            trendClass: 'trend-up',
            icon: 'trending-up'
        },
        {
            title: 'Imbalance Rate (Prediksi)',
            value: `${formatNumber(data.imbalance_rate_pct)}%`,
            unit: '',
            trend: data.status === 'green' ? 'Normal' : (data.status === 'yellow' ? 'Waspada' : 'Kritis'),
            trendClass: data.status === 'green' ? 'trend-up' : (data.status === 'yellow' ? 'trend-warning' : 'trend-down'),
            icon: 'activity'
        }
    ];

    kpis.forEach(kpi => {
        const card = document.createElement('div');
        card.className = 'kpi-card';
        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:1rem">
                <div class="kpi-title">${kpi.title}</div>
                <i data-lucide="${kpi.icon}" style="color:var(--text-muted); width:20px; height:20px"></i>
            </div>
            <div class="kpi-value">${kpi.value} <span class="kpi-unit">${kpi.unit}</span></div>
            <div class="kpi-trend ${kpi.trendClass}">
                <i data-lucide="${kpi.icon === 'trending-down' ? 'arrow-down-right' : (kpi.icon === 'trending-up' ? 'arrow-up-right' : 'clock')}" style="width:14px; height:14px"></i>
                ${kpi.trend}
            </div>
        `;
        container.appendChild(card);
    });

    lucide.createIcons();
}

function renderAlerts(alerts) {
    const list = document.getElementById('alert-list');
    document.getElementById('alert-badge').textContent = alerts.length;
    list.innerHTML = '';

    if (alerts.length === 0) {
        list.innerHTML = '<p style="color:var(--text-muted); font-size:0.9rem">Tidak ada alert aktif.</p>';
        return;
    }

    alerts.forEach(alert => {
        const timeStr = new Date(alert.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const sevClass = alert.severity.toLowerCase();

        const item = document.createElement('div');
        item.className = `alert-item ${sevClass}`;
        item.innerHTML = `
            <div class="alert-header">
                <span class="alert-type">${alert.type}</span>
                <span class="alert-time">${timeStr}</span>
            </div>
            <div class="alert-msg">${alert.message}</div>
        `;
        list.appendChild(item);
    });
}

function renderChart(data) {
    const ctx = document.getElementById('forecastChart').getContext('2d');

    if (forecastChartInstance) {
        forecastChartInstance.destroy();
    }

    const labels = data.map(d => {
        const date = new Date(d.tanggal);
        return `${date.getDate()}/${date.getMonth()+1}`;
    });

    const demandActual = data.map(d => d.demand_actual);
    const supplyActual = data.map(d => d.supply_actual);
    const demandForecast = data.map(d => d.demand_forecast);
    const supplyForecast = data.map(d => d.supply_forecast);

    // Find the boundary between actual and prediction
    const predStartIdx = data.findIndex(d => d.is_prediction || d.month_type === 'prediction');

    const gradientDemand = ctx.createLinearGradient(0, 0, 0, 400);
    gradientDemand.addColorStop(0, 'rgba(59, 130, 246, 0.3)');
    gradientDemand.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

    const gradientSupply = ctx.createLinearGradient(0, 0, 0, 400);
    gradientSupply.addColorStop(0, 'rgba(16, 185, 129, 0.3)');
    gradientSupply.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

    forecastChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Demand Aktual',
                    data: demandActual,
                    borderColor: '#3b82f6',
                    backgroundColor: gradientDemand,
                    borderWidth: 2.5,
                    pointBackgroundColor: '#3b82f6',
                    pointRadius: 2,
                    fill: true,
                    tension: 0.3,
                    spanGaps: false,
                },
                {
                    label: 'Supply Aktual',
                    data: supplyActual,
                    borderColor: '#10b981',
                    backgroundColor: gradientSupply,
                    borderWidth: 2.5,
                    pointBackgroundColor: '#10b981',
                    pointRadius: 2,
                    fill: true,
                    tension: 0.3,
                    spanGaps: false,
                },
                {
                    label: 'Demand Prediksi',
                    data: demandForecast,
                    borderColor: 'rgba(59, 130, 246, 0.6)',
                    borderWidth: 2,
                    borderDash: [6, 3],
                    pointRadius: 0,
                    fill: false,
                    tension: 0.3,
                },
                {
                    label: 'Supply Prediksi',
                    data: supplyForecast,
                    borderColor: 'rgba(16, 185, 129, 0.6)',
                    borderWidth: 2,
                    borderDash: [6, 3],
                    pointRadius: 0,
                    fill: false,
                    tension: 0.3,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: '#f8fafc', usePointStyle: true, boxWidth: 8, font: { size: 11 } }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#f8fafc',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            let val = context.parsed.y;
                            if (val === null || val === undefined) return null;
                            return `${context.dataset.label}: ${formatNumber(val)} MMSCFD`;
                        }
                    }
                },
                // Vertical line annotation for prediction start
                annotation: predStartIdx > 0 ? {
                    annotations: {
                        predLine: {
                            type: 'line',
                            xMin: predStartIdx,
                            xMax: predStartIdx,
                            borderColor: 'rgba(255, 255, 255, 0.2)',
                            borderWidth: 2,
                            borderDash: [4, 4]
                        }
                    }
                } : undefined
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#94a3b8' },
                    title: { display: true, text: 'Volume (MMSCFD)', color: '#94a3b8', font: { size: 12 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', maxTicksLimit: 15, font: { size: 10 } }
                }
            }
        }
    });
}

function generateMockChartData() {
    const data = [];
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();

    // Current month actuals (up to today)
    for (let day = 1; day <= 30; day++) {
        const date = new Date(currentYear, currentMonth, day);
        const isPast = date <= now;

        const baseDemand = currentRegion ? 400 : 2150;
        const baseSupply = currentRegion ? 420 : 2175;

        data.push({
            tanggal: date.toISOString().split('T')[0],
            demand_actual: isPast ? baseDemand + (Math.random() * 60 - 30) : null,
            supply_actual: isPast ? baseSupply + (Math.random() * 50 - 25) : null,
            demand_forecast: baseDemand + (Math.random() * 40 - 20),
            supply_forecast: baseSupply + (Math.random() * 35 - 17),
            is_prediction: !isPast,
            month_type: 'current'
        });
    }

    // Next month predictions
    const nextMonth = currentMonth + 1 > 11 ? 0 : currentMonth + 1;
    const nextYear = nextMonth === 0 ? currentYear + 1 : currentYear;

    for (let day = 1; day <= 30; day++) {
        const date = new Date(nextYear, nextMonth, day);
        const baseDemand = currentRegion ? 410 : 2200;
        const baseSupply = currentRegion ? 425 : 2210;

        data.push({
            tanggal: date.toISOString().split('T')[0],
            demand_actual: null,
            supply_actual: null,
            demand_forecast: baseDemand + (Math.random() * 50 - 25),
            supply_forecast: baseSupply + (Math.random() * 45 - 22),
            is_prediction: true,
            month_type: 'prediction'
        });
    }

    return data;
}

// =============================================================================
// UPLOAD — via MODAL (dashboard quick-upload button)
// =============================================================================
const modal = document.getElementById('uploadModal');
const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const btnSubmit = document.getElementById('btnSubmitUpload');
const statusDiv = document.getElementById('uploadStatus');
const progressBar = document.getElementById('uploadProgress');
const statusMsg = document.getElementById('uploadMessage');

function openUploadModal() {
    modal.classList.add('show');
    resetModalUploadState();
}

function closeUploadModal() {
    modal.classList.remove('show');
}

function resetModalUploadState() {
    selectedFile = null;
    fileInput.value = '';
    btnSubmit.disabled = true;
    uploadArea.classList.remove('hidden');
    statusDiv.classList.add('hidden');
    progressBar.style.width = '0%';
    progressBar.style.backgroundColor = 'var(--primary)';
    statusMsg.style.color = 'var(--text-muted)';
    uploadArea.innerHTML = `
        <i data-lucide="file-up" class="upload-icon"></i>
        <p>Drag & drop file Anda di sini atau <span class="text-primary">browse</span></p>
        <p class="upload-hint">Mendukung CSV, XLSX, Parquet (Maks 100MB)</p>
        <p class="upload-hint">Kolom: <strong>tanggal</strong>, <strong>region</strong>, <strong>demand_actual</strong>, <strong>supply_actual</strong></p>
    `;
    lucide.createIcons();
}

function setupModalUpload() {
    uploadArea.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleFileSelection(e.target.files[0]);
    });

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) handleFileSelection(e.dataTransfer.files[0]);
    });
}

function handleFileSelection(file) {
    const validExts = ['.csv', '.xlsx', '.parquet'];
    const isValid = validExts.some(ext => file.name.toLowerCase().endsWith(ext));

    if (!isValid) {
        alert('Format file tidak valid. Silakan upload CSV, XLSX, atau Parquet.');
        return;
    }

    selectedFile = file;
    uploadArea.innerHTML = `
        <i data-lucide="file-check-2" class="upload-icon" style="color:var(--success)"></i>
        <p style="font-weight:600">${file.name}</p>
        <p class="upload-hint">${(file.size / 1024 / 1024).toFixed(2)} MB</p>
    `;
    lucide.createIcons();
    btnSubmit.disabled = false;
}

async function submitUpload() {
    if (!selectedFile) return;

    btnSubmit.disabled = true;
    uploadArea.classList.add('hidden');
    statusDiv.classList.remove('hidden');
    progressBar.style.backgroundColor = 'var(--primary)';
    progressBar.style.width = '30%';
    statusMsg.style.color = 'var(--text-muted)';
    statusMsg.textContent = 'Memvalidasi schema...';

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        await new Promise(r => setTimeout(r, 800));
        progressBar.style.width = '60%';
        statusMsg.textContent = 'Menjalankan prediksi ML...';

        const response = await fetchWithTimeout(`${API_BASE}/upload/`, {
            method: 'POST',
            body: formData
        }, 15000);

        progressBar.style.width = '90%';

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Upload gagal');
        }

        const result = await response.json();

        // Save to localStorage so it persists
        localStorage.setItem('dashboardData', JSON.stringify(result));

        progressBar.style.width = '100%';
        statusMsg.textContent = `Berhasil! Prediksi ${result.prediction_month} telah dibuat.`;
        statusMsg.style.color = 'var(--success)';

        setTimeout(() => {
            closeUploadModal();
            loadDashboardData();
        }, 1500);

    } catch (error) {
        progressBar.style.backgroundColor = 'var(--danger)';
        statusMsg.textContent = `Error: ${error.message}`;
        statusMsg.style.color = 'var(--danger)';
        btnSubmit.disabled = false;

        setTimeout(() => {
            resetModalUploadState();
        }, 4000);
    }
}

// =============================================================================
// UPLOAD — via DEDICATED PAGE
// =============================================================================
function setupPageUpload() {
    const area = document.getElementById('uploadAreaPage');
    const input = document.getElementById('fileInputPage');
    const statusEl = document.getElementById('uploadStatusPage');
    const progressEl = document.getElementById('uploadProgressPage');
    const msgEl = document.getElementById('uploadMessagePage');
    const resultDiv = document.getElementById('uploadResultPage');
    const resultContent = document.getElementById('uploadResultContent');

    if (!area || !input) return;

    let pageFile = null;

    area.addEventListener('click', () => input.click());

    input.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            pageFile = e.target.files[0];
            showPageFileSelected(area, pageFile);
            processPageUpload(pageFile, area, statusEl, progressEl, msgEl, resultDiv, resultContent);
        }
    });

    area.addEventListener('dragover', (e) => {
        e.preventDefault();
        area.classList.add('dragover');
    });
    area.addEventListener('dragleave', () => area.classList.remove('dragover'));
    area.addEventListener('drop', (e) => {
        e.preventDefault();
        area.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            pageFile = e.dataTransfer.files[0];
            showPageFileSelected(area, pageFile);
            processPageUpload(pageFile, area, statusEl, progressEl, msgEl, resultDiv, resultContent);
        }
    });
}

function showPageFileSelected(area, file) {
    area.innerHTML = `
        <i data-lucide="file-check-2" class="upload-icon" style="color:var(--success)"></i>
        <p style="font-weight:600">${file.name}</p>
        <p class="upload-hint">${(file.size / 1024 / 1024).toFixed(2)} MB — Memproses...</p>
    `;
    lucide.createIcons();
}

async function processPageUpload(file, area, statusEl, progressEl, msgEl, resultDiv, resultContent) {
    // Show progress
    statusEl.classList.remove('hidden');
    resultDiv.classList.add('hidden');
    progressEl.style.width = '20%';
    progressEl.style.backgroundColor = 'var(--primary)';
    msgEl.style.color = 'var(--text-muted)';
    msgEl.textContent = 'Memvalidasi file...';

    const formData = new FormData();
    formData.append('file', file);

    try {
        await new Promise(r => setTimeout(r, 500));
        progressEl.style.width = '50%';
        msgEl.textContent = 'Menjalankan prediksi bulan depan...';

        const response = await fetchWithTimeout(`${API_BASE}/upload/`, {
            method: 'POST',
            body: formData
        }, 15000);

        progressEl.style.width = '90%';

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Upload gagal');
        }

        const result = await response.json();
        lastUploadResult = result;
        
        // Save to localStorage so it persists
        localStorage.setItem('dashboardData', JSON.stringify(result));

        progressEl.style.width = '100%';
        msgEl.textContent = `Berhasil! ${result.rows_processed} baris diproses → ${result.rows_predicted} baris prediksi dibuat.`;
        msgEl.style.color = 'var(--success)';

        // Render prediction result
        renderUploadResult(resultContent, result);
        resultDiv.classList.remove('hidden');

        // Refresh dashboard in background
        loadDashboardData();

    } catch (error) {
        progressEl.style.backgroundColor = 'var(--danger)';
        msgEl.textContent = `Error: ${error.message}`;
        msgEl.style.color = 'var(--danger)';

        setTimeout(() => {
            resetPageUploadArea(area, statusEl, progressEl, msgEl, resultDiv);
        }, 5000);
    }
}

function renderUploadResult(container, result) {
    const summary = result.summary;
    if (!summary) {
        container.innerHTML = '<p style="color:var(--success)">✅ File berhasil diproses.</p>';
        return;
    }

    // Safe number helper — prevents NaN display
    const safeNum = (val, fallback = 0) => {
        const n = Number(val);
        return (isNaN(n) || !isFinite(n)) ? fallback : n;
    };

    const demandChangePct = safeNum(summary.demand_change_pct);
    const supplyChangePct = safeNum(summary.supply_change_pct);
    const demandChangeClass = demandChangePct >= 0 ? 'positive' : 'negative';
    const supplyChangeClass = supplyChangePct >= 0 ? 'positive' : 'negative';
    const demandArrow = demandChangePct >= 0 ? '↑' : '↓';
    const supplyArrow = supplyChangePct >= 0 ? '↑' : '↓';

    let html = `
        <div class="prediction-summary">
            <h4>
                📊 Hasil Prediksi Harian
                <span class="prediction-month-badge">
                    ${summary.source_month || '?'} → ${summary.prediction_month || '?'}
                </span>
            </h4>

            <!-- Summary Stats -->
            <div class="grand-total-bar">
                <div class="grand-total-item">
                    <div class="gt-label">Avg Demand/Hari (${summary.source_month})</div>
                    <div class="gt-value">${formatNumber(safeNum(summary.source_demand_avg_daily))}</div>
                </div>
                <div class="grand-total-item">
                    <div class="gt-label">Avg Demand/Hari (${summary.prediction_month})</div>
                    <div class="gt-value" style="color:var(--primary)">
                        ${formatNumber(safeNum(summary.pred_demand_avg_daily))}
                        <span class="change ${demandChangeClass}" style="font-size:0.7rem;margin-left:0.35rem">${demandArrow} ${Math.abs(demandChangePct)}%</span>
                    </div>
                </div>
                <div class="grand-total-item">
                    <div class="gt-label">Avg Supply/Hari (${summary.source_month})</div>
                    <div class="gt-value">${formatNumber(safeNum(summary.source_supply_avg_daily))}</div>
                </div>
                <div class="grand-total-item">
                    <div class="gt-label">Avg Supply/Hari (${summary.prediction_month})</div>
                    <div class="gt-value" style="color:var(--success)">
                        ${formatNumber(safeNum(summary.pred_supply_avg_daily))}
                        <span class="change ${supplyChangeClass}" style="font-size:0.7rem;margin-left:0.35rem">${supplyArrow} ${Math.abs(supplyChangePct)}%</span>
                    </div>
                </div>
            </div>

            <!-- Monthly Totals -->
            <div class="grand-total-bar" style="margin-top:0.75rem;">
                <div class="grand-total-item">
                    <div class="gt-label">Total Demand ${summary.source_month} (${safeNum(summary.source_days)} hari)</div>
                    <div class="gt-value">${formatNumber(safeNum(summary.source_demand_total))}</div>
                </div>
                <div class="grand-total-item">
                    <div class="gt-label">Total Demand ${summary.prediction_month} (${safeNum(summary.prediction_days)} hari)</div>
                    <div class="gt-value" style="color:var(--primary)">${formatNumber(safeNum(summary.pred_demand_total))}</div>
                </div>
                <div class="grand-total-item">
                    <div class="gt-label">Total Supply ${summary.source_month} (${safeNum(summary.source_days)} hari)</div>
                    <div class="gt-value">${formatNumber(safeNum(summary.source_supply_total))}</div>
                </div>
                <div class="grand-total-item">
                    <div class="gt-label">Total Supply ${summary.prediction_month} (${safeNum(summary.prediction_days)} hari)</div>
                    <div class="gt-value" style="color:var(--success)">${formatNumber(safeNum(summary.pred_supply_total))}</div>
                </div>
            </div>

            <!-- Daily Prediction Table -->
            <h4 style="margin-top:1.5rem;">📋 Prediksi Harian — ${summary.prediction_month}</h4>
            <p style="color:var(--text-muted);font-size:0.8rem;margin-bottom:0.75rem;">
                Total semua region per hari (MMSCFD)
            </p>
            <table class="upload-result-table">
                <thead>
                    <tr>
                        <th>No</th>
                        <th>Tanggal</th>
                        <th>Demand Forecast (MMSCFD)</th>
                        <th>Supply Forecast (MMSCFD)</th>
                    </tr>
                </thead>
                <tbody>
    `;

    const dailyData = summary.daily_predictions || result.daily_predictions || [];
    dailyData.forEach((row, idx) => {
        html += `
            <tr>
                <td>${idx + 1}</td>
                <td>${row.tanggal}</td>
                <td>${formatNumber(row.demand_forecast)}</td>
                <td>${formatNumber(row.supply_forecast)}</td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>

            <button class="btn-download" onclick="downloadPrediction()">
                <i data-lucide="download" style="width:16px;height:16px"></i>
                Download Prediksi ${summary.prediction_month} (CSV)
            </button>
        </div>
    `;

    container.innerHTML = html;
    lucide.createIcons();
}

function downloadPrediction() {
    if (!lastUploadResult || !lastUploadResult.prediction_data) {
        alert('Tidak ada data prediksi untuk diunduh.');
        return;
    }

    const data = lastUploadResult.prediction_data;
    const headers = ['tanggal', 'demand_forecast', 'supply_forecast'];
    let csv = headers.join(',') + '\n';

    data.forEach(row => {
        csv += headers.map(h => row[h] ?? '').join(',') + '\n';
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `prediksi_harian_${lastUploadResult.prediction_month || 'bulan_depan'}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function resetPageUploadArea(area, statusEl, progressEl, msgEl, resultDiv) {
    area.innerHTML = `
        <i data-lucide="file-up" class="upload-icon"></i>
        <p>Drag & drop file Anda di sini atau <span class="text-primary">browse</span></p>
        <p class="upload-hint">Mendukung CSV, XLSX, Parquet (Maks 100MB)</p>
        <p class="upload-hint">Kolom wajib: <strong>tanggal</strong>, <strong>region</strong>, <strong>demand_actual</strong>, <strong>supply_actual</strong></p>
    `;
    lucide.createIcons();
    statusEl.classList.add('hidden');
    resultDiv.classList.add('hidden');
    progressEl.style.width = '0%';
    progressEl.style.backgroundColor = 'var(--primary)';
    msgEl.style.color = 'var(--text-muted)';
}

// =============================================================================
// MANUAL INPUT
// =============================================================================
function setupManualInput() {
    const form = document.getElementById('manual-form');
    if (!form) return;

    // Set today's date as default
    const dateInput = document.getElementById('manual-ts');
    dateInput.value = new Date().toISOString().split('T')[0];

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const statusEl = document.getElementById('manual-status');
        const submitBtn = form.querySelector('button[type="submit"]');

        const tanggal = document.getElementById('manual-ts').value;
        const region = document.getElementById('manual-region').value;
        const demand = parseFloat(document.getElementById('manual-demand').value);
        const supply = parseFloat(document.getElementById('manual-supply').value);

        if (!tanggal) {
            showManualStatus(statusEl, 'Silakan pilih tanggal!', 'error');
            return;
        }
        if (!region) {
            showManualStatus(statusEl, 'Silakan pilih region/SOR!', 'error');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i data-lucide="loader"></i> Memproses...';
        lucide.createIcons();
        statusEl.classList.add('hidden');

        // Build a CSV in-memory and send it to the API
        const csvContent = `tanggal,region,demand_actual,supply_actual\n${tanggal},${region},${demand},${supply}`;
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const dummyFile = new File([blob], 'manual_input.csv', { type: 'text/csv' });

        const formData = new FormData();
        formData.append('file', dummyFile);

        try {
            const response = await fetchWithTimeout(`${API_BASE}/upload/`, {
                method: 'POST',
                body: formData
            }, 10000);

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Upload gagal');
            }

            showManualStatus(statusEl, '✅ Data berhasil dikirim dan diprediksi!', 'success');
            
            const result = await response.json();
            localStorage.setItem('dashboardData', JSON.stringify(result));
            
            loadDashboardData();

        } catch (error) {
            showManualStatus(statusEl, `❌ Error: ${error.message}`, 'error');
        }

        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i data-lucide="send"></i> Submit Data';
        lucide.createIcons();
    });
}

function showManualStatus(el, message, type) {
    el.textContent = message;
    el.className = `manual-status ${type}`;
    el.classList.remove('hidden');
}
