# Product Requirements Document (PRD)

## Gas Supply-Demand Forecasting System

**Sistem Peramalan Supply-Demand Gas Berbasis XGBoost dengan Dashboard Operasional dan Strategis**

---

## Document Information

| Field | Value |
|---|---|
| **Versi Dokumen** | 1.0 |
| **Tanggal Dibuat** | 24 Juni 2026 |
| **Status** | Draft |
| **Product Owner** | [Nama PO] |
| **Tech Lead** | [Nama Tech Lead] |

---

## Executive Summary

Dokumen ini mendefinisikan kebutuhan produk untuk sistem peramalan supply-demand gas menggunakan model XGBoost. Sistem ini dirancang untuk meminimalkan gap antara prediksi dan realisasi, serta menyediakan dashboard interaktif untuk mendukung keputusan operasional harian dan perencanaan strategis jangka panjang.

---

## Goals & Success Metrics

### Primary Goals

1. **Akurasi Prediksi Tinggi** — Gap minimal antara nilai prediksi model dengan data realisasi aktual.
2. **Visualisasi Real-Time** — Dashboard yang menampilkan perbandingan prediksi vs realisasi secara intuitif.
3. **Data Ingestion Cepat** — Data baru dapat diunggah dan diproses untuk prediksi secara near real-time.

### Key Performance Indicators (KPIs)

| KPI | Target | Metode Pengukuran |
|---|---|---|
| **MAPE** | <= 5% | Perbandingan prediksi vs realisasi bulanan |
| **RMSE** | Sesuai benchmark internal | Evaluasi model berkala |
| **Imbalance Rate Harian** | <= 3% | Monitoring dashboard operasional |
| **Alert Precision** | >= 90% | Rasio alert valid vs total alert |
| **Dashboard Uptime** | >= 99.5% | Monitoring sistem |
| **Waktu Inferensi** | < 500 ms/request | Monitoring API prediksi |

---

## Problem Statement

Saat ini proses pemantauan dan perencalan supply-demand gas cenderung tersebar di berbagai sumber data dan sering kali membutuhkan analisis manual. Akibatnya:

- Terdapat keterlambatan dalam mendeteksi potensi **under-supply** atau **imbalance** jaringan.
- Sulit melakukan perbandingan cepat antara **forecast** dan **realisasi**.
- Perencanaan jangka panjang untuk kontrak payung, LNG/pipa, dan investasi infrastruktur belum didukung oleh simulasi skenario yang cepat dan terukur.

Sistem ini bertujuan mengatasi masalah tersebut dengan menggabungkan **forecasting berbasis XGBoost**, **dashboard operasional**, dan **dashboard strategis** dalam satu platform.

---

## Product Vision

Menyediakan platform forecasting supply-demand gas yang akurat, cepat, dan dapat ditindaklanjuti untuk mendukung keputusan operasional harian serta perencanaan strategis jangka panjang.

---

## Scope

### In Scope

- Forecasting demand/supply gas berbasis XGBoost.
- Upload data untuk inferensi real-time atau batch.
- Dashboard operasional jangka pendek.
- Dashboard strategis jangka panjang.
- Alert dini untuk potensi under-supply, imbalance, dan dampak maintenance.
- What-if analysis untuk variabel makro dan harga komoditas.
- Perbandingan realisasi vs forecasting historis.

### Out of Scope

- Optimasi dispatch otomatis ke jaringan pipa.
- Kontrol langsung ke sistem SCADA.
- Auto-trading atau keputusan komersial otomatis.
- Dukungan model non-XGBoost pada fase awal MVP.

---

## User Personas

### Persona 1: Operator Dispatching

- **Peran**: Mengawasi operasional harian jaringan pipa.
- **Kebutuhan**: Mengetahui prediksi demand harian/jam-an, realisasi supply, imbalance, dan alert dini.
- **Pain Points**: Sulit mendeteksi masalah sebelum terjadi gangguan distribusi.

### Persona 2: Manajer Perencanaan Strategis

- **Peran**: Menyusun rencana kontrak dan investasi infrastruktur.
- **Kebutuhan**: Proyeksi 12-24 bulan, simulasi skenario ekonomi, dan monitoring fuel switching.
- **Pain Points**: Analisis masih manual dan lambat saat menguji banyak skenario.

### Persona 3: Data Analyst / Data Scientist

- **Peran**: Menjaga performa model dan kualitas data.
- **Kebutuhan**: Upload dataset, validasi schema, monitoring akurasi model, retraining berkala.
- **Pain Points**: Proses evaluasi model belum terintegrasi dengan dashboard bisnis.

### Persona 4: Manajemen / Eksekutif

- **Peran**: Pengambil keputusan tingkat tinggi.
- **Kebutuhan**: Ringkasan KPI, tren jangka panjang, risiko pasokan, dan dampak skenario.
- **Pain Points**: Membutuhkan informasi yang ringkas, visual, dan cepat dipahami.

---

## Functional Requirements

## 1. Data Uploader

**Deskripsi**: Modul untuk mengunggah dataset yang akan diprediksi model secara real-time atau batch.

### Requirements

| ID | Requirement | Priority |
|---|---|---|
| **DU-01** | Sistem menerima file format CSV, XLSX, dan Parquet. | Must Have |
| **DU-02** | Sistem memvalidasi struktur kolom dan tipe data sesuai schema. | Must Have |
| **DU-03** | Sistem menampilkan preview data sebelum diproses. | Should Have |
| **DU-04** | Sistem mendeteksi missing value, duplikasi, dan outlier dasar. | Must Have |
| **DU-05** | Sistem menampilkan status upload, validasi, dan inferensi. | Must Have |
| **DU-06** | Sistem menyimpan riwayat upload beserta timestamp, user, dan status. | Should Have |
| **DU-07** | Sistem menghasilkan output prediksi yang dapat diunduh. | Must Have |
| **DU-08** | Sistem menolak file yang tidak sesuai schema dan memberi pesan error yang jelas. | Must Have |
| **DU-09** | Sistem mendukung inferensi batch untuk banyak record sekaligus. | Must Have |
| **DU-10** | Sistem mendukung inferensi near real-time untuk data terbaru. | Should Have |

### Minimum Input Schema

```text
Kolom wajib minimum:
- timestamp
- region
- demand_actual
- supply_actual
- temperature
- is_holiday
- industrial_activity_index
```

### Acceptance Criteria

- File hingga **100 MB** dapat diproses tanpa timeout.
- Validasi schema untuk file **50.000 baris** selesai dalam **< 5 detik**.
- Inferensi batch **10.000 record** selesai dalam **< 30 detik**.
- Pengguna menerima pesan error yang spesifik jika kolom wajib hilang atau tipe data salah.

---

## 2. Modul Jangka Pendek - Operational Dashboard

**Deskripsi**: Modul pemantauan harian untuk menjaga keseimbangan jaringan pipa secara real-time atau near real-time.

### 2.1 KPI Cards

| ID | Requirement | Priority |
|---|---|---|
| **OP-01** | Menampilkan total prediksi demand hari ini dalam MMscfd atau BBtu. | Must Have |
| **OP-02** | Menampilkan total realisasi pasokan hari ini. | Must Have |
| **OP-03** | Menghitung dan menampilkan imbalance rate. | Must Have |
| **OP-04** | Menampilkan warna status: hijau, kuning, merah berdasarkan threshold imbalance. | Must Have |
| **OP-05** | Menampilkan perbandingan dengan hari sebelumnya atau minggu lalu. | Should Have |
| **OP-06** | Data KPI refresh otomatis berkala dan dapat di-refresh manual. | Must Have |

### 2.2 Grafik Intraday / Harian

| ID | Requirement | Priority |
|---|---|---|
| **OP-07** | Menampilkan 3 garis: Prediksi Model, Realisasi Lapangan, dan Batas/Kapasitas. | Must Have |
| **OP-08** | Menampilkan horizon prediksi hingga 7 hari ke depan. | Must Have |
| **OP-09** | Mendukung granularitas per jam dan per hari. | Must Have |
| **OP-10** | Menampilkan tooltip interaktif saat hover. | Must Have |
| **OP-11** | Menampilkan highlight area saat terjadi gap besar antara forecast dan realisasi. | Must Have |
| **OP-12** | Menampilkan confidence interval prediksi jika tersedia. | Should Have |
| **OP-13** | Mendukung filter per wilayah, sektor, atau segmen jaringan. | Should Have |

### 2.3 Alert System

| ID | Requirement | Priority |
|---|---|---|
| **OP-14** | Sistem memberikan alert otomatis jika ada potensi under-supply. | Must Have |
| **OP-15** | Sistem memberikan alert otomatis jika ada risiko tekanan pipa turun. | Must Have |
| **OP-16** | Sistem mengaitkan alert dengan jadwal maintenance kilang/pipa. | Must Have |
| **OP-17** | Alert memiliki severity level: Critical, Warning, Info. | Must Have |
| **OP-18** | Tersedia log alert yang dapat difilter berdasarkan waktu dan severity. | Must Have |
| **OP-19** | User dapat melakukan acknowledge dan resolve terhadap alert. | Must Have |
| **OP-20** | Sistem mendukung notifikasi in-app. | Must Have |
| **OP-21** | Sistem mendukung pengiriman email untuk alert kritikal. | Should Have |

### Example Alert Rules

| Alert Type | Trigger | Severity |
|---|---|---|
| **Under-Supply Risk** | Prediksi demand > 95% kapasitas supply tersedia | Critical |
| **Imbalance Warning** | Imbalance rate > 5% selama 3 periode berturut-turut | Warning |
| **Maintenance Impact** | Ada maintenance aktif + forecast demand tinggi | Warning |
| **Pressure Drop Risk** | Estimasi tekanan < batas minimum operasi | Critical |
| **Forecast Deviation** | Selisih forecast vs realisasi melampaui ambang deviasi | Info |

---

## 3. Modul Jangka Panjang - Strategic Planning Dashboard

**Deskripsi**: Modul analisis tren bulanan/tahunan untuk kontrak pasokan dan perencanaan infrastruktur.

### 3.1 Proyeksi Tren Bulanan

| ID | Requirement | Priority |
|---|---|---|
| **ST-01** | Menampilkan proyeksi supply-demand hingga 12 atau 24 bulan ke depan. | Must Have |
| **ST-02** | Menampilkan data historis sebagai pembanding. | Must Have |
| **ST-03** | Menampilkan pola musiman dan tren jangka panjang. | Must Have |
| **ST-04** | Mendukung filter wilayah, sektor, dan horizon waktu. | Must Have |
| **ST-05** | Mendukung ekspor grafik untuk kebutuhan presentasi/laporan. | Should Have |

### 3.2 What-If Analysis

| ID | Requirement | Priority |
|---|---|---|
| **ST-06** | User dapat mengubah variabel makro secara dinamis. | Must Have |
| **ST-07** | Sistem menyediakan preset scenario seperti Baseline, High Growth, dan Recession. | Must Have |
| **ST-08** | Grafik proyeksi otomatis diperbarui setelah skenario dipilih atau diubah. | Must Have |
| **ST-09** | Sistem menampilkan dampak skenario terhadap demand, supply gap, dan KPI utama. | Must Have |
| **ST-10** | User dapat membandingkan beberapa skenario secara side-by-side. | Should Have |
| **ST-11** | User dapat menyimpan skenario kustom. | Should Have |

### Example Scenario Variables

| Variable | Example Range | Notes |
|---|---|---|
| **Pertumbuhan PDB** | -5% s/d +10% | Variabel makro utama |
| **Harga Gas** | Dinamis | Mengacu harga pasar |
| **Harga Batu Bara** | Dinamis | Untuk analisis substitusi |
| **Harga Brent** | Dinamis | Untuk pembanding energi |
| **Tambahan Kapasitas** | 0-500 MMscfd | Infrastruktur baru |
| **Perubahan Kebijakan** | Variatif | Subsidi / regulasi |

### 3.3 Fuel Switching Monitor

| ID | Requirement | Priority |
|---|---|---|
| **ST-12** | Menampilkan perbandingan harga gas vs batu bara vs minyak. | Must Have |
| **ST-13** | Menampilkan rasio harga sebagai indikator switching. | Must Have |
| **ST-14** | Menampilkan threshold switching point. | Should Have |
| **ST-15** | Menampilkan korelasi historis harga dengan perubahan demand gas. | Should Have |
| **ST-16** | Memberikan alert jika indikator mendekati switching threshold. | Should Have |

---

## Business Rules

- Forecast utama menggunakan **XGBoost** sebagai model baseline pada fase awal.
- Data historis harus memiliki timestamp valid dan konsisten.
- Realisasi lapangan dianggap sebagai **source of truth** untuk evaluasi akurasi.
- Threshold alert harus dapat dikonfigurasi oleh admin bisnis.
- Skenario what-if tidak boleh mengubah data historis asli.
- Semua hasil inferensi harus disimpan untuk keperluan audit dan evaluasi model.

---

## Model Requirements

### Model Objective

Memprediksi demand gas dan/atau gap supply-demand berdasarkan data historis, faktor temporal, variabel makro, harga komoditas, cuaca, dan data operasional.

### Recommended Features

- **Temporal features**: hour, day, week, month, quarter, holiday flag.
- **Lag features**: lag 1, lag 7, lag 30.
- **Rolling statistics**: rolling mean, rolling std, EWMA.
- **Weather features**: temperature, humidity, cooling/heating degree days.
- **Macro features**: GDP growth, industrial production, sektor demand.
- **Commodity features**: harga gas, batu bara, Brent.
- **Operational features**: kapasitas pipa, maintenance, storage level.

### Model Evaluation Metrics

| Metric | Purpose |
|---|---|
| **MAPE** | Mengukur error persentase terhadap realisasi |
| **RMSE** | Mengukur penalti error besar |
| **MAE** | Mengukur rata-rata error absolut |
| **Bias** | Mengetahui kecenderungan over-forecast / under-forecast |

### Retraining Strategy

| Item | Requirement |
|---|---|
| **Frekuensi Retraining** | Mingguan atau bulanan sesuai perubahan data |
| **Trigger Retraining** | Performa model turun melewati threshold |
| **Validasi** | Time-series cross validation |
| **Deployment Rule** | Model baru hanya menggantikan model aktif jika performanya lebih baik |

---

## Data Requirements

### Data Sources

| Source | Frequency | Format | Owner |
|---|---|---|---|
| **SCADA / Telemetry** | Real-time / 15 menit | API / JSON | Operations |
| **Billing / Nomination** | Harian | CSV / Database | Commercial |
| **Weather Data** | Jam-an / Harian | API | External |
| **Commodity Prices** | Harian | API / CSV | External |
| **Maintenance Schedule** | Mingguan / ad-hoc | Excel / Manual | Engineering |
| **Macro Economic Data** | Bulanan / Kuartalan | CSV | Planning |

### Data Quality Requirements

| Metric | Target |
|---|---|
| **Completeness** | >= 98% |
| **Timeliness** | Delay <= 30 menit untuk data operasional |
| **Consistency** | Tidak ada konflik antar sumber utama |
| **Accuracy** | Tervalidasi dengan source system |

---

## Non-Functional Requirements

### Performance

| Metric | Target |
|---|---|
| **Dashboard Load Time** | < 3 detik |
| **Prediction API Latency** | < 500 ms/request |
| **Batch Prediction** | >= 10.000 record/menit |
| **Concurrent Users** | >= 50 user bersamaan |

### Security

| Aspect | Requirement |
|---|---|
| **Authentication** | SSO / OAuth / SAML |
| **Authorization** | Role-based access control |
| **Encryption** | TLS in transit, AES-256 at rest |
| **Audit Trail** | Semua aktivitas penting tercatat |

### Availability

| Metric | Target |
|---|---|
| **Uptime** | >= 99.5% |
| **RTO** | <= 4 jam |
| **RPO** | <= 1 jam |

---

## User Journey

### Operational User Flow

1. User membuka dashboard operasional.
2. Sistem menampilkan KPI utama hari ini.
3. User melihat grafik prediksi vs realisasi vs batas kapasitas.
4. Jika ada alert, user membuka log alert.
5. User melakukan acknowledge dan tindak lanjut operasional.

### Strategic User Flow

1. User membuka dashboard strategis.
2. User memilih horizon 12 atau 24 bulan.
3. User memilih skenario baseline atau skenario lain.
4. Sistem menghitung ulang proyeksi berdasarkan parameter yang dipilih.
5. User membandingkan hasil dan mengekspor visual untuk rapat/perencanaan.

### Data Upload Flow

1. User mengunggah file data.
2. Sistem memvalidasi schema dan kualitas data.
3. Sistem menjalankan inferensi model.
4. Hasil prediksi ditampilkan pada dashboard atau tersedia untuk diunduh.

---

## UX/UI Requirements

- Dashboard harus responsif dan mudah dibaca di layar desktop standar operasional.
- KPI cards harus menampilkan angka utama secara jelas dan cepat dipahami.
- Warna alert harus konsisten: **hijau = aman**, **kuning = waspada**, **merah = kritis**.
- Grafik harus mendukung tooltip, filter, dan zoom.
- Pengguna dapat berpindah cepat antara tampilan operasional dan strategis.

---

## Reporting & Export

| Requirement ID | Requirement | Priority |
|---|---|---|
| **RP-01** | Export hasil prediksi ke CSV/XLSX | Must Have |
| **RP-02** | Export grafik ke PNG/PDF | Should Have |
| **RP-03** | Download log alert | Should Have |
| **RP-04** | Export hasil skenario untuk presentasi manajemen | Should Have |

---

## Assumptions

- Data historis supply-demand tersedia dan cukup untuk melatih model awal.
- Data maintenance dapat diakses dan cukup andal untuk dimasukkan ke alert engine.
- Ada definisi bisnis yang jelas untuk threshold imbalance, under-supply, dan pressure drop.
- Tim bisnis siap memvalidasi interpretasi output model.

---

## Dependencies

- Ketersediaan data SCADA/operasional.
- Ketersediaan harga komoditas dan data makro dari sumber eksternal.
- Infrastruktur penyimpanan time-series.
- Tim data/IT untuk deployment pipeline dan model.
- Persetujuan keamanan untuk integrasi data operasional.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Kualitas data buruk** | Akurasi forecast menurun | Tambahkan validation layer dan monitoring data quality |
| **Model drift** | Prediksi tidak akurat | Monitoring performa dan retraining terjadwal |
| **Integrasi data maintenance lambat** | Alert tidak optimal | Fase integrasi diprioritaskan sejak awal |
| **Adopsi user rendah** | Manfaat produk tidak maksimal | UAT iteratif dan pelatihan pengguna |
| **Ketergantungan data eksternal** | Dashboard strategis kurang lengkap | Siapkan fallback cache dan indikator kualitas data |

---

## Release Plan

### Phase 1 - MVP

- Data uploader dasar.
- Model forecasting XGBoost baseline.
- Dashboard operasional: KPI cards, line chart, basic alert.
- Evaluasi forecast vs realisasi.

### Phase 2 - Enhanced Planning

- Dashboard strategis 12-24 bulan.
- What-if analysis.
- Fuel switching monitor.
- Export reporting.

### Phase 3 - Optimization

- Tuning model dan threshold alert.
- Advanced notification.
- Scenario management lanjutan.
- Auditability dan observability penuh.

---

## Success Criteria for Launch

Produk dinyatakan siap launch apabila:

- Forecast mencapai target akurasi minimum yang disepakati bisnis.
- Dashboard operasional menampilkan prediksi vs realisasi tanpa isu kritikal.
- Alert utama berfungsi sesuai rule bisnis.
- Modul strategic planning mampu menjalankan minimal 3 skenario utama.
- UAT user utama selesai dan disetujui.

---

## Open Questions

- Apakah model akan memprediksi **demand saja** atau juga **supply** secara independen?
- Sumber data utama untuk **pressure drop** berasal dari sistem apa?
- Apakah dashboard perlu mendukung **multi-region** sejak MVP?
- Seberapa sering skenario strategis perlu diperbarui otomatis?
- Apakah output forecast akan digunakan juga untuk proses komersial atau hanya monitoring?

---

## Appendix

### Glossary

| Term | Definition |
|---|---|
| **MMscfd** | Million Standard Cubic Feet per Day |
| **BBtu** | Billion British Thermal Units |
| **Imbalance Rate** | Persentase selisih antara supply dan demand |
| **Fuel Switching** | Perpindahan konsumsi antar bahan bakar akibat perubahan harga/ekonomi |
| **MAPE** | Mean Absolute Percentage Error |
| **XGBoost** | Algoritma gradient boosting untuk supervised learning |

### Sign-Off

| Role | Name | Date | Signature |
|---|---|---|---|
| **Product Owner** |  |  |  |
| **Business Owner** |  |  |  |
| **Tech Lead** |  |  |  |
| **Data Science Lead** |  |  |  |
