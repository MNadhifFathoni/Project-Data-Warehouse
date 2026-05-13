# Project Data Warehouse — Disaster Monitoring Indonesia

ETL Pipeline + Data Warehouse + Dashboard untuk monitoring bencana alam di Indonesia (titik api + gempa bumi) menggunakan data dari **NASA FIRMS** dan **USGS Earthquake**.

---

## 📋 Yang Bisa Dilakukan

| Fitur | Keterangan |
|---|---|
| **Ambil data terbaru** dari NASA FIRMS & USGS API | `python main.py run-etl` |
| **Simpan data ke Data Warehouse** (DuckDB) | `python main.py load-dwh` |
| **Lihat dashboard interaktif** di browser | `streamlit run dashboard/app.py` |
| **Jalankan query analitik** dari terminal | `python main.py query all` |
| **Export data** ke Parquet / CSV | `python main.py build-mart` |
| **Update otomatis** terjadwal | `python scripts/scheduled_run.py` |
| **Jalankan semua** (ETL → DWH → Export) | `python main.py full-pipeline` |
| **Tes kode** dengan pytest | `python -m pytest tests/ -v` |

---

## 📊 Cara Lihat Visualisasi Dashboard

### 1. Jalankan Streamlit

```bash
# Dari folder project
streamlit run dashboard/app.py
```

### 2. Buka Browser

Streamlit akan menampilkan URL seperti:

```
Local URL:   http://localhost:8501
Network URL: http://192.168.1.123:8501
```

Klik **Local URL** (`http://localhost:8501`) untuk membuka dashboard.

### 3. Navigasi Dashboard

Setelah terbuka, di sidebar kiri ada menu navigasi:

| Menu | Halaman |
|---|---|
| **📊 Overview** | Ringkasan semua data: total hotspots, gempa, trend bulanan, provinsi teratas |
| **🔥 Fire Hotspots** | Peta panas interaktif, tren harian, perbandingan provinsi, siang/malam |
| **🌍 Earthquakes** | Peta gempa (lingkaran warna berdasarkan magnitudo), distribusi magnitudo, tsunami |

### 4. Fitur Interaktif Dashboard

- **Peta Fire Hotspots**: Zoom, pan, klik titik untuk detail. Slider untuk mengatur jumlah titik yang ditampilkan.
- **Peta Earthquakes**: Lingkaran merah = ada potensi tsunami. Ukuran lingkaran = magnitudo.
- **Grafik**: Hover untuk melihat nilai detail. Bisa di-zoom area tertentu.
- **Sidebar**: Navigasi antar halaman tanpa reload.

### 5. Troubleshooting Dashboard

```bash
# Jika port 8501 sudah dipakai, ganti port:
streamlit run dashboard/app.py --server.port 8502

# Jika ada error import, pastikan sudah:
uv sync
```

### 6. Deploy ke Streamlit Cloud (Online / Publik)

Dashboard bisa di-deploy gratis ke **Streamlit Community Cloud** agar bisa diakses siapa saja via browser tanpa instalasi.

**Langkah-langkah:**

1. **Push project ke GitHub** (sudah dilakukan):
   ```
   https://github.com/MNadhifFathoni/Project-Data-Warehouse
   ```

2. **Buka** [Streamlit Community Cloud](https://streamlit.io/cloud) → klik **Sign in with GitHub**

3. **Klik "New app"** → pilih repository `MNadhifFathoni/Project-Data-Warehouse`

4. **Konfigurasi:**
   - **Branch**: `master`
   - **Main file path**: `dashboard/app.py`
   - **Click "Deploy"**

5. **Set secrets** (`.env` untuk API key):
   - Settings → Secrets → Tambah:
   ```toml
   FIRMS_MAP_KEY = "20fd9a932d5532c30c85afc4eee7afb3"
   ```

6. **Tunggu build selesai** (~5-10 menit pertama, lebih cepat untuk update berikutnya)

7. **Dashboard online!** URL akan seperti:
   ```
   https://project-data-warehouse.streamlit.app/
   ```

**Catatan:** Data DuckDB tidak ikut push ke GitHub (ukuran besar, ada di `.gitignore`). Streamlit Cloud akan rebuild database dari CSV staging saat pertama deploy. Pastikan CSV staging sudah ada.

---

## 🖥️ Semua Cara Menggunakan Project

### Setup Awal

```bash
# 1. Install Python (>= 3.12) dan uv
#    https://docs.astral.sh/uv/

# 2. Clone / buka folder project
cd project-data-warehouse

# 3. Install semua dependencies
uv sync

# 4. Set API Key NASA FIRMS
#    Daftar gratis di: https://firms.modaps.eosdis.nasa.gov/api/map_key
echo FIRMS_MAP_KEY=your_key_here > .env

# 5. (Opsional) Download shapefile provinsi
#    Natural Earth admin 1 otomatis didownload saat pertama load-dwh
```

### 1️⃣ Mengambil Data dari API (Staging ETL)

Menarik data fire hotspot dan gempa dari API dan menyimpannya sebagai CSV.

```bash
# Ambil semua data 2023-2025
python main.py run-etl

# Ambil data periode tertentu
python main.py run-etl --start 2025-01-01 --end 2025-06-30

# Ambil data dari sumber tertentu saja
python main.py run-etl --sources VIIRS_NOAA21_NRT

# Ambil data gempa saja (skip fire)
python main.py run-etl --sources VIIRS_NOAA21_NRT --start 2026-01-01 --end 2026-12-31
```

### 2️⃣ Membangun Data Warehouse (DWH)

Memindahkan data dari CSV ke DuckDB dengan struktur Star Schema.

```bash
# Full load (hapus database lama + load ulang semua)
python main.py load-dwh

# Load hanya data baru (incremental)
python main.py load-dwh --incremental

# Load hanya fire hotspots
python main.py load-dwh --no-eq

# Load hanya earthquake
python main.py load-dwh --no-fire

# Reset tracker + reload (misal setelah ada perubahan shapefile)
python main.py load-dwh --incremental --reset-tracker fire

# Init schema saja (tanpa load data)
python main.py init-dwh
```

### 3️⃣ Melihat Data Lewat Terminal (Query)

Menjalankan query analitik langsung di terminal tanpa dashboard.

```bash
# Lihat semua hasil query
python main.py query all

# Lihat provinsi dengan hotspot terbanyak
python main.py query top_provinces_hotspot

# Lihat provinsi dengan gempa terbanyak
python main.py query top_provinces_earthquake

# Lihat tren bulanan fire hotspots
python main.py query monthly_fire_trend

# Lihat tren bulanan gempa
python main.py query monthly_eq_trend

# Lihat perbandingan deteksi antar satelit
python main.py query satellite_comparison

# Lihat hari dengan event terbanyak
python main.py query days_with_most_events
```

### 4️⃣ Export Data (Data Mart)

Mengexport hasil agregasi ke format Parquet dan CSV untuk analisis lebih lanjut di Excel, Python, atau BI tools.

```bash
# Export semua format (Parquet + CSV)
python main.py build-mart

# Export hanya Parquet
python main.py build-mart --format parquet

# Export hanya CSV
python main.py build-mart --format csv
```

Hasil export ada di `data/mart/`:

| File | Isi |
|---|---|
| `v_hotspot_daily.parquet` / `.csv` | Jumlah hotspot per hari per provinsi |
| `v_earthquake_daily.parquet` / `.csv` | Jumlah gempa per hari per provinsi |
| `v_monthly_trend.parquet` | Tren bulanan hotspot vs gempa |
| `v_high_risk_zones.parquet` | Zona risiko tinggi (grid-based) |

### 5️⃣ Menjalankan Semua Sekaligus (Full Pipeline)

ETL → DWH → Mart dalam satu perintah.

```bash
python main.py full-pipeline
```

### 6️⃣ Update Data Terjadwal (Scheduling)

Untuk update data mingguan/bulanan secara otomatis.

```bash
# Manual run (ambil data 2 minggu terakhir)
python scripts/scheduled_run.py

# Ambil data 4 minggu terakhir
python scripts/scheduled_run.py --weeks 4

# Skip API fetch (jalankan ulang DWH + Mart saja)
python scripts/scheduled_run.py --skip-etl

# Dengan log file
python scripts\scheduled_run.py --log-file logs\update.log
```

**Setup Windows Task Scheduler:**
1. Buka **Task Scheduler** → Create Task
2. Name: `DWH Update`, run whether user is logged on or not
3. Trigger: Daily / Weekly
4. Action: Start a program
   - Program: `C:\path\to\.venv\Scripts\python.exe`
   - Arguments: `scripts\scheduled_run.py --weeks 2`
   - Start in: `C:\path\to\project`

**Setup Linux Cron:**
```bash
# Setiap Minggu jam 02:00
0 2 * * 0 cd /path/to/project && .venv/bin/python scripts/scheduled_run.py --weeks 2 >> logs/scheduler.log 2>&1
```

### 7️⃣ Menjalankan Tes (Testing)

```bash
# Semua test
python -m pytest tests/ -v

# Test spesifik
python -m pytest tests/test_transform_firms.py -v
python -m pytest tests/test_transform_usgs.py -v
python -m pytest tests/test_geo_utils.py -v
python -m pytest tests/test_dwh_schema.py -v
```

### 8️⃣ Melihat Langsung Data DuckDB (Advanced)

Untuk eksplorasi data langsung dari DuckDB.

```bash
# Buka DuckDB CLI
python -c "import duckdb; duckdb.connect('data/dwh/disaster.duckdb')"
```

Atau dari Python:
```python
from dwh.dwh_loader import DWHLoader
loader = DWHLoader()
loader.init_schema()

# Query custom
df = loader.run_sql("SELECT province_name, COUNT(*) as total FROM dwh.fact_fire_hotspot f JOIN dwh.dim_location l ON f.location_key = l.location_key GROUP BY province_name ORDER BY total DESC")
print(df)
loader.close()
```

---

## 🗃️ Arsitektur Data Warehouse (Star Schema)

### Diagram Alur Data

```
┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────┐
│ NASA FIRMS   │──▶│ Staging (CSV)    │──▶│ DuckDB DWH       │──▶│ Data Mart    │
│ USGS         │   │ Bronze Layer     │   │ Silver Layer     │   │ Gold Layer   │
└──────────────┘   └──────────────────┘   └──────────────────┘   └──────────────┘
```

### 3-Layer Architecture

| Layer | Storage | Deskripsi |
|---|---|---|
| **Bronze** (Staging) | `data/staging/*.csv` | Data mentah dari API, per bulan per sumber |
| **Silver** (DWH) | `data/dwh/disaster.duckdb` | DuckDB database dengan Star Schema |
| **Gold** (Mart) | `data/mart/*.parquet` & `.csv` | Agregasi siap-pakai untuk analisis |

### Star Schema Design

```
┌──────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  dim_date    │◄────│  fact_fire_hotspot  │────►│  dim_location   │
│              │     │                     │     │                 │
│ date_key     │     │ frp, brightness     │     │ location_key    │
│ full_date    │     │ scan, track         │     │ longitude       │
│ year, month  │     │ confidence          │     │ latitude        │
│ quarter      │     │ daynight            │     │ province_name   │
│ day_of_week  │     └────────┬────────────┘     │ province_code   │
└──────────────┘              │                  │ grid_cell_id    │
                              │                  └─────────────────┘
                              ▼
                    ┌──────────────────┐
                    │ dim_satellite    │
                    │  _source         │
                    │                  │
                    │ src_key, sensor  │
                    │ satellite_source │
                    └──────────────────┘


┌──────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  dim_date    │◄────│  fact_earthquake    │────►│  dim_location   │
│              │     │                     │     └─────────────────┘
│              │     │ mag, depth, felt    │
│              │     │ cdi, mmi, tsunami   │     ┌─────────────────┐
│              │     │ sig, nst, dmin      │────►│  dim_event_type  │
│              │     │ place, title        │     │                 │
└──────────────┘     └─────────────────────┘     │ earthquake      │
                                                 │ quarry          │
                                                 │ explosion       │
                                                 └─────────────────┘
```

### Ukuran Data Saat Ini

| Tabel | Jumlah Baris |
|---|---|
| `fact_fire_hotspot` | **104,550** titik api |
| `fact_earthquake` | **1,802** gempa bumi |
| `dim_location` | **104,039** koordinat unik |
| `dim_date` | **4,018** hari (2020-2030) |

---

## 📈 Contoh Insight dari Dashboard

### Fire Hotspots per Provinsi (2025)

| Provinsi | Titik Api | Rata-rata FRP |
|---|---|---|
| Kalimantan Barat | 19,353 | 13.7 |
| Nusa Tenggara Timur | 12,540 | 7.7 |
| Kalimantan Timur | 5,991 | 8.8 |
| Sumatera Utara | 4,119 | 7.8 |
| Riau | 3,938 | 7.7 |

### Puncak Kejadian

- **Hotspot terbanyak dalam sehari**: 22 September 2025 (3,109 events)
- **Gempa terbesar**: M 6.7 (Juli 2025)
- **Bulan dengan hotspot terbanyak**: September 2025 (22,491 titik)
- **Deteksi malam hari**: Rata-rata FRP lebih tinggi dari siang hari

---

## 🛠️ Data Sources

| Source | API URL | Data |
|---|---|---|
| **NASA FIRMS** | [firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov) | Fire hotspots via MODIS & VIIRS |
| **USGS Earthquake** | [earthquake.usgs.gov](https://earthquake.usgs.gov) | Earthquake events >= M0+ |
| **Natural Earth** | [naturalearthdata.com](https://www.naturalearthdata.com) | Province boundaries (admin 1) |

**Bounding Box Indonesia:** `lat: -11 s.d 6, lon: 95 s.d 141`

---

## 📁 Struktur Folder Project

```
project-data-warehouse/
├── main.py                       # CLI entry point (semua perintah)

├── streaming/                     # (Bronze) ETL: API → CSV
│   ├── config.py
│   ├── pipeline.py
│   ├── extract/                  # FIRMSClient, USGSClient
│   ├── transform/                # FirmsTransformer, UsgsTransformer
│   └── load/                     # StagingLoader (CSV writer)

├── dwh/                          # (Silver) DWH Layer
│   ├── config.py
│   ├── schema.py                 # DDL + Data Mart Views
│   ├── dwh_loader.py             # ETL: CSV → DuckDB
│   ├── geo_utils.py              # Reverse geocoding (shapefile + grid)
│   └── queries.py                # Query SQL siap pakai

├── dashboard/                    # Streamlit Dashboard
│   ├── app.py                    # Main entry (side bar navigation)
│   ├── utils.py                  # Query helper (cached, DB connection)
│   └── pages/
│       ├── overview.py           # 📊 Halaman ringkasan
│       ├── fire_hotspots.py      # 🔥 Analisis titik api
│       └── earthquakes.py        # 🌍 Analisis gempa

├── mart/                         # (Gold) Data Mart
│   └── build_mart.py             # Export views → Parquet / CSV

├── scripts/
│   ├── scheduled_run.py          # Scheduler: ETL → DWH → Mart
│   └── run_scheduled.bat         # Windows batch wrapper

├── tests/                        # Unit Tests (pytest)
│   ├── conftest.py               # Sample data fixtures
│   ├── test_transform_firms.py   # 8 tests
│   ├── test_transform_usgs.py    # 8 tests
│   ├── test_geo_utils.py         # 8 tests
│   └── test_dwh_schema.py        # 6 tests

├── data/
│   ├── staging/                  # Raw CSV (bronze)
│   │   ├── fire_hotspots/
│   │   └── earthquakes/
│   ├── shapefile/                # Indonesia boundary
│   ├── dwh/disaster.duckdb       # DuckDB database
│   └── mart/                     # Parquet & CSV exports

├── logs/                         # Log scheduler
├── .env                          # API key
├── pyproject.toml                # Dependencies
└── README.md
```

---

## 🔜 Roadmap

- [x] **Staging Layer** (Bronze) — ETL API → CSV
- [x] **DWH Layer** (Silver) — DuckDB Star Schema
- [x] **Data Mart** (Gold) — Aggregated views + Parquet export
- [x] **Province-level shapefile** — Natural Earth admin 1 (33 provinces)
- [x] **Visualisasi** — Streamlit dashboard interaktif (3 pages)
- [x] **Incremental loading** — file-level tracker + dedup by event_id
- [x] **Scheduling** — `scripts/scheduled_run.py` + Task Scheduler / cron
- [x] **Unit tests** — 30 pytest, 4 test modules

---

## 📋 Prerequisites

- **Python** >= 3.12
- **uv** — package manager ([docs.astral.sh/uv](https://docs.astral.sh/uv/))
- **FIRMS API key** — daftar gratis di [firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov/api/map_key)
