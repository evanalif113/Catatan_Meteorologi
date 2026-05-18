import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.animation as animation
import seaborn as sns
import missingno as msno
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime

sns.set_theme(style="whitegrid")
# %matplotlib inline

# %%
# Konfigurasi database sumber
source_cred = credentials.Certificate("D:/staklimjerukagung-firebase-adminsdk-kcfma-e091165a9b.json")
firebase_admin.initialize_app(source_cred, {
    'databaseURL': 'https://staklimjerukagung-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

# %%
station_ids = ['id-03', 'id-05']

# Input readable date
start_readable_date = "01-01-2025 00:00:00"  # Format: DD-MM-YYYY HH:MM:SS
end_readable_date = "31-12-2026 23:59:59"    # Format: DD-MM-YYYY HH:MM:SS

# Convert readable date to Unix timestamp
start_timestamp = int(datetime.strptime(start_readable_date, "%d-%m-%Y %H:%M:%S").timestamp())
print(start_timestamp)  # Convert to string and print
end_timestamp = int(datetime.strptime(end_readable_date, "%d-%m-%Y %H:%M:%S").timestamp())
print(end_timestamp)  # Convert to string and print

# %%
# Siapkan dictionary kosong untuk menampung DataFrame yang sudah bersih
all_weather_dataframes = {}

print("Memulai proses pengambilan dan pembersihan data dari Firebase...")
print("=" * 65)

for station in station_ids:
    try:
        # 1. TARIK DATA DARI FIREBASE
        ref_path = f'/auto_weather_stat/{station}/data'
        ref_data = db.reference(ref_path)
        query_data = ref_data.order_by_key().start_at(str(start_timestamp)).end_at(str(end_timestamp))
        results = query_data.get()

        if results:
            # 2. KONVERSI KE DATAFRAME
            df = pd.DataFrame.from_dict(results, orient='index')

            # Jika timestamp dari Firebase menjadi Index, turunkan menjadi kolom biasa
            if 'timestamp' not in df.columns:
                df.index.name = 'timestamp'
                df = df.reset_index()

            # 3. PENGECEKAN & PENCARIAN LOKASI NULL PADA TIMESTAMP
            null_mask = df['timestamp'].isnull()
            jumlah_null = null_mask.sum()

            if jumlah_null > 0:
                # Cari lokasi (nomor baris/index) di mana timestamp bernilai null
                lokasi_null = df[null_mask].index.tolist()
                print(f"   ⚠️ Peringatan: Ditemukan {jumlah_null} data NULL di stasiun {station}.")
                print(f"      -> Baris yang rusak: {lokasi_null}")

                # Buang baris yang timestamp-nya null agar tidak membuat error konversi selanjutnya
                df = df.dropna(subset=['timestamp'])
                print("      -> Data NULL telah dihapus.")

            # 4. UBAH TIMESTAMP MENJADI INTEGER
            # Kita ubah ke float dulu untuk jaga-jaga jika Firebase mengirimnya sebagai string '1710000000.0'
            df['timestamp'] = df['timestamp'].astype(float).astype(int)

            # 5. UBAH KE DATETIME UTC+7 (ASIA/BANGKOK ATAU ASIA/JAKARTA)
            # Karena timestamp Anda 10 digit, itu artinya formatnya adalah Detik (unit='s')
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)

            # Konversi ke waktu lokal WIB (+07:00)
            df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Bangkok')

            # Simpan DataFrame yang sudah sempurna ke dalam dictionary
            all_weather_dataframes[station] = df
            print(f"✅ Berhasil: Stasiun {station} siap! ({len(df)} baris data valid)")

        else:
            print(f"⚠️ Kosong: Tidak ada data untuk stasiun {station} pada rentang waktu ini.")

    except Exception as e:
        print(f"❌ Error: Gagal memproses data untuk {station}. Detail: {e}")

print("=" * 65)
print(f"Proses selesai. Data bersih tersedia untuk: {list(all_weather_dataframes.keys())}")

# Untuk melihat hasilnya:
# print(all_weather_dataframes['id-03'].head())
# print(all_weather_dataframes['id-03'].info())

# %%
# 1. Tentukan nama folder target
output_folder = 'raw_data_sensor'

# Buat folder secara otomatis (jika sudah ada, Python tidak akan error berkat exist_ok=True)
os.makedirs(output_folder, exist_ok=True)
print(f"📁 Direktori penyimpanan siap: '{output_folder}/'")
print("=" * 65)

# 2. Loop melalui dictionary yang berisi DataFrame bersih Anda
for station_id, df in all_weather_dataframes.items():
    try:
        # --- MENAMPILKAN DATA ---
        print(f"\n📊 Menampilkan 3 baris pertama untuk stasiun: {station_id}")
        print(df.head(3))  # Menampilkan sebagian kecil data agar layar tidak penuh

        # --- MENYIMPAN DATA KE CSV ---
        # Susun nama file yang rapi
        filename = f"raw_data_{station_id}.csv"
        file_path = os.path.join(output_folder, filename)

        # Eksekusi penyimpanan!
        # Ingat: index=False wajib dipakai agar Pandas tidak membuat kolom angka urut tambahan
        df.to_csv(file_path, index=False)

        print(f"💾 Berhasil diekspor: {filename} ({len(df)} baris)")

    except Exception as e:
        print(f"❌ Gagal memproses atau menyimpan data untuk {station_id}. Detail: {e}")

print("\n" + "=" * 65)
print("🎉 SELURUH PROSES SELESAI! Silakan cek folder Anda di sebelah kiri layar.")

# %%
# 1. Tentukan nama folder tempat data mentah Anda disimpan
folder_path = 'raw_data_sensor'

# Siapkan dictionary kosong untuk menampung DataFrame
all_weather_dataframes = {}

print(f"📂 Memulai proses pembacaan data dari folder '{folder_path}'...")
print("=" * 65)

# 2. Validasi apakah folder benar-benar ada di sistem
if not os.path.exists(folder_path):
    print(f"❌ Fatal Error: Folder '{folder_path}' tidak ditemukan di direktori saat ini!")
else:
    # 3. Cari semua file CSV di dalam folder menggunakan pola *.csv
    pola_pencarian = os.path.join(folder_path, '*.csv')
    daftar_file_csv = glob.glob(pola_pencarian)

    if len(daftar_file_csv) == 0:
        print("⚠️ Peringatan: Folder ditemukan, tetapi tidak ada file berekstensi .csv di dalamnya.")
    else:
        # 4. Loop untuk membaca setiap file yang ditemukan
        for file_path in daftar_file_csv:
            try:
                # Ambil nama file dari jalurnya
                nama_file = os.path.basename(file_path)

                # Ekstrak station_id dari nama file
                station_id = nama_file.replace('.csv', '').split('_')[-1]

                # Eksekusi pembacaan data CSV
                df = pd.read_csv(file_path)

                # --- PENTING: KONVERSI ULANG WAKTU ---
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                elif df.index.name == 'timestamp':
                    df.index = pd.to_datetime(df.index)

                # Masukkan kembali ke dalam dictionary
                all_weather_dataframes[station_id] = df

                print(f"✅ Berhasil memuat: {nama_file} -> Stasiun '{station_id}' ({len(df)} baris data)")

            except Exception as e:
                print(f"❌ Gagal membaca file '{nama_file}'. Detail Error: {e}")

print("=" * 65)
print("Proses Muat Data Selesai! Data siap dilanjutkan ke tahap Reindexing dan Filtering.")

# Untuk memvalidasi hasilnya, Anda bisa melakukan print seperti biasa:
# print(all_weather_dataframes['id-03'].info())

# %%
import missingno as msno
import matplotlib.pyplot as plt

print("🔍 MEMULAI INSPEKSI MISSING VALUES KE SEMUA STASIUN...")

# Looping melalui setiap stasiun (key) dan tabel datanya (value)
for station_id, df in all_weather_dataframes.items():

    print(f"📊 REPORT STASIUN: {station_id.upper()}")

    # Cek apakah DataFrame kosong
    if df.empty:
        print(f"⚠️ Peringatan: Data untuk stasiun {station_id} kosong!")
        continue

    # 1. Mengecek nilai null dalam DataFrame stasiun saat ini
    print("\n=== 1. Jumlah Missing Values ===")
    print(df.isnull().sum())

    # 2. Menampilkan persentase missing values
    print("\n=== 2. Persentase Missing Values ===")
    missing_percentage = (df.isnull().sum() / len(df)) * 100
    print(missing_percentage.apply(lambda x: f"{x:.2f}%"))

    # 3. Menampilkan baris-baris yang mengandung nilai null
    print("\n=== 3. Inspeksi Baris Null ===")
    null_rows = df[df.isnull().any(axis=1)]
    print(f"Jumlah baris kotor (mengandung minimal 1 NaN): {len(null_rows)} baris dari total {len(df)} baris.")

    if len(null_rows) > 0:
        print("\nContoh 5 baris yang mengandung null:")
        print(null_rows.head(5))
    else:
        print("✅ LUAR BIASA! Tabel ini 100% bersih tanpa ada data yang bolong.")

    # 4. Visualisasi missing values menggunakan missingno
    print(f"\n=== 4. Peta Visual Missing Values ({station_id}) ===")

    fig = plt.figure(figsize=(12, 5))
    ax = fig.add_subplot(111)

    msno.matrix(df, ax=ax, sparkline=False, fontsize=10)

    ax.set_title(f"Distribusi Missing Values - {station_id.upper()}", fontsize=16, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.show()

print("\n" + "=" * 60)
print("SELURUH INSPEKSI SELESAI!")

# %%
import matplotlib.pyplot as plt
import pandas as pd

def plot_station_trends(data_dict, column_to_plot, freq='d', agg_method='mean'):
    """
    Membuat plot tren perbandingan dengan metode agregasi dinamis.
    """
    # 1. Konfigurasi Label Frekuensi
    freq_config = {
        'd': {'label': 'Harian', 'xlabel': 'Tanggal', 'code': 'D'},
        'h': {'label': 'Per Jam', 'xlabel': 'Waktu (Jam)', 'code': 'H'},
        'min': {'label': 'Per Menit', 'xlabel': 'Waktu (Menit)', 'code': 'min'}
    }

    selected_freq = freq_config.get(freq, freq_config['d'])

    # 2. Konfigurasi Label Agregasi
    agg_labels = {
        'mean': 'Rata-rata',
        'median': 'Median (Nilai Tengah)',
        'max': 'Maksimum (Tertinggi)',
        'min': 'Minimum (Terendah)',
        'sum': 'Total Akumulasi'
    }
    agg_display_name = agg_labels.get(agg_method, agg_method.capitalize())

    # Mulai Plotting
    plt.figure(figsize=(15, 7))
    plot_berhasil = False

    # Loop stasiun
    for station_id, df in data_dict.items():
        if column_to_plot not in df.columns:
            print(f"⚠️ Peringatan: Kolom '{column_to_plot}' tidak ada di {station_id}. Skip.")
            continue

        temp_df = df.copy()

        # --- Pastikan timestamp bisa diakses ---
        if 'timestamp' not in temp_df.columns and temp_df.index.name == 'timestamp':
            temp_df = temp_df.reset_index()

        if not pd.api.types.is_datetime64_any_dtype(temp_df['timestamp']):
            temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'])

        # --- Paksa kolom target menjadi numerik murni ---
        temp_df[column_to_plot] = pd.to_numeric(temp_df[column_to_plot], errors='coerce')

        # 3. PROSES GROUPING & AGREGASI DINAMIS
        time_col = f'time_group_{freq}'
        temp_df[time_col] = temp_df['timestamp'].dt.floor(selected_freq['code'])

        trend_data = temp_df.groupby(time_col)[column_to_plot].agg(agg_method).dropna().reset_index()

        if trend_data.empty:
            print(f"⚠️ Peringatan: Data agregasi untuk {station_id} kosong.")
            continue

        plt.plot(
            trend_data[time_col],
            trend_data[column_to_plot],
            label=station_id,
            alpha=0.8,
        )
        plot_berhasil = True

    # 4. Mempercantik Visualisasi
    plt.xlabel(selected_freq['xlabel'], fontsize=12)
    plt.ylabel(f"{agg_display_name} {column_to_plot.replace('_', ' ').capitalize()}", fontsize=12)
    plt.title(f"Perbandingan {agg_display_name} {column_to_plot} ({selected_freq['label']})",
              fontsize=14, fontweight='bold')

    if plot_berhasil:
        plt.legend()
    else:
        plt.text(
            0.5, 0.5,
            'TIDAK ADA DATA VALID UNTUK DITAMPILKAN',
            ha='center', va='center', fontsize=16, color='red',
            transform=plt.gca().transAxes
        )

    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()

# CARA PEMANGGILAN:
# plot_station_trends(all_weather_dataframes, 'temperature', freq='h', agg_method='max')

# %%
# --- 1. Membuat Plot Rata-rata PER JAM ---
print("Menampilkan plot perbandingan per jam...")
plot_station_trends(all_weather_dataframes, 'temperature', freq='min', agg_method='mean')
plot_station_trends(all_weather_dataframes, 'humidity', freq='min', agg_method='mean')
plot_station_trends(all_weather_dataframes, 'pressure', freq='min', agg_method='mean')
plot_station_trends(all_weather_dataframes, 'rainrate', freq='min', agg_method='max')

# %%
# --- 2. Membuat Plot Rata-rata PER HARI ---
print("\nMenampilkan plot perbandingan per hari...")
plot_station_trends(all_weather_dataframes, 'temperature', freq='d', agg_method='mean')
plot_station_trends(all_weather_dataframes, 'humidity', freq='d', agg_method='mean')
plot_station_trends(all_weather_dataframes, 'pressure', freq='d', agg_method='mean')
plot_station_trends(all_weather_dataframes, 'dew', freq='d', agg_method='mean')

# %%
plot_station_trends(all_weather_dataframes, 'rainrate', freq='min', agg_method='max')

# %%
cuaca5 = all_weather_dataframes['id-05']

# %%
cuaca5.describe()

# %%
import pandas as pd
import numpy as np

# =======================================================
# 1. PERSIAPAN DATA WAKTU (PENTING!)
# =======================================================
if 'timestamp' in cuaca5.columns:
    cuaca5['timestamp'] = pd.to_datetime(cuaca5['timestamp'])
    cuaca5 = cuaca5.sort_values('timestamp').set_index('timestamp')

# =======================================================
# 2. DETEKSI INCREMENT & PENANGANAN RESET ALAT
# =======================================================
cuaca5['delta_raw'] = cuaca5['rainrate'].diff()

cuaca5['actual_increment'] = np.where(
    cuaca5['delta_raw'] < 0,
    cuaca5['rainrate'],
    cuaca5['delta_raw']
)
cuaca5['actual_increment'] = cuaca5['actual_increment'].fillna(0).clip(lower=0)

# =======================================================
# 3. FILTER OUTLIER (HARD PHYSICAL THRESHOLD)
# =======================================================
BATAS_MAKSIMAL_PER_MENIT = 3.0

kondisi_outlier = cuaca5['actual_increment'] > BATAS_MAKSIMAL_PER_MENIT
jumlah_outlier = kondisi_outlier.sum()

print(f"🚨 Terdeteksi {jumlah_outlier} titik outlier (goyangan palsu / lonjakan tak wajar)!")

cuaca5.loc[kondisi_outlier, 'actual_increment'] = 0.0

# =======================================================
# 4. PEMBULATAN TIP (STANDARISASI KE 0.3)
# =======================================================
KONSTANTA_TIP = 0.3
cuaca5['tips_count'] = np.round(cuaca5['actual_increment'] / KONSTANTA_TIP)
cuaca5['increment_fixed'] = cuaca5['tips_count'] * KONSTANTA_TIP

# =======================================================
# 5. REKONSTRUKSI AKUMULASI PER JAM
# =======================================================
cuaca5['rainrate'] = cuaca5.groupby(cuaca5.index.floor('h'))['increment_fixed'].cumsum()

# =======================================================
# 6. AGREGASI HARIAN / PER JAM
# =======================================================
df_hourly = cuaca5.resample('h').agg({
    'rainrate': 'max',
    'temperature': 'mean',
    'humidity': 'mean',
    'pressure': 'mean',
    'dew': 'mean'
})

# Tampilkan hasil
print("✅ Pembersihan dan Agregasi Selesai!")
print(df_hourly.head(10))

# %%
# Set Style biar ganteng
sns.set(style="whitegrid")

plt.figure(figsize=(15, 6))

# A. PLOT DATA
plt.plot(df_hourly.index, df_hourly['rainrate'], color='dodgerblue', lw=1, label='Curah Hujan (mm/jam)')
plt.fill_between(df_hourly.index, df_hourly['rainrate'], color='dodgerblue', alpha=0.3)

# B. PERCANTIK
plt.title('Hietograf: Distribusi Curah Hujan Per Jam', fontsize=16, fontweight='bold')
plt.ylabel('Curah Hujan (mm)', fontsize=12)
plt.xlabel('Waktu', fontsize=12)
plt.legend(loc='upper right')

# Format Tanggal di Sumbu X biar rapi
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d-%b-%Y'))
plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
plt.xticks(rotation=45)

plt.tight_layout()
plt.show()

# %%
df_hourly.tail(500)

# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# ==============================================================================
# 0. PERSIAPAN DATA ERA5 (OPEN-METEO)
# ==============================================================================
era5_path = r'D:\Github\Catatan_Meteorologi\Analisis_Meteorologi\open_meteo_jerukagung\cuaca_jerukagung.csv'

print("🌍 Memuat Data ERA5...")
df_era5 = pd.read_csv(era5_path)

# Deteksi kolom waktu yang sesuai dengan dataset
time_candidates = ['date', 'time', 'timestamp']
time_col_era5 = next((c for c in time_candidates if c in df_era5.columns), None)
if time_col_era5 is None:
    raise ValueError("Kolom waktu tidak ditemukan di cuaca_jerukagung.csv. Diharapkan salah satu dari: 'date', 'time', 'timestamp'.")

df_era5[time_col_era5] = pd.to_datetime(df_era5[time_col_era5], errors='coerce')

n_invalid_times = df_era5[time_col_era5].isna().sum()
if n_invalid_times > 0:
    print(f"⚠️ Terdapat {n_invalid_times} baris dengan nilai tanggal/waktu tidak valid. Baris tersebut akan dihapus.")
    df_era5 = df_era5.dropna(subset=[time_col_era5])

df_era5 = df_era5.sort_values(time_col_era5).set_index(time_col_era5)

# Jika timezone-aware, seragamkan ke Asia/Bangkok lalu buang timezone
if getattr(df_era5.index, 'tz', None) is not None:
    df_era5.index = df_era5.index.tz_convert('Asia/Bangkok')
    try:
        df_era5.index = df_era5.index.tz_localize(None)
    except Exception:
        df_era5.index = pd.DatetimeIndex(df_era5.index.astype('datetime64[ns]'))

# Sesuaikan nama kolom agar cocok dengan pipeline
if 'dewpoint' in df_era5.columns and 'dew' not in df_era5.columns:
    df_era5 = df_era5.rename(columns={'dewpoint': 'dew'})

# Mapping nama kolom sumber ke kolom target
era5_mapping = {
    'temperature': 'temperature',
    'humidity': 'humidity',
    'pressure': 'pressure',
    'dew': 'dew',
    'rainrate': 'rain_mm',
}

print(f"✅ ERA5 Siap! Dimensi: {df_era5.shape}")
print("=" * 65)

# ==============================================================================
# 1. FUNGSI PIPELINE: REINDEXING MUTLAK + HAMPEL + IMPUTASI HIBRIDA
# ==============================================================================
def bersihkan_data_hourly_hibrida(df_hourly, df_era5_reference, start_time, end_time):
    """
    Melakukan Reindexing MUTLAK (berdasarkan input user), Hampel Filter,
    Imputasi Spline untuk lubang kecil, dan Substitusi ERA5 untuk lubang besar.
    """
    print(f"⚙️ Memulai Pipeline Hibrida | Rentang: {start_time} s.d {end_time}")

    # --- TAHAP 1: REINDEXING MUTLAK ---
    master_index = pd.date_range(start=start_time, end=end_time, freq='H')

    df_reindexed = df_hourly.reindex(master_index)
    df_reindexed.index.name = 'timestamp'

    # Simpan versi mentah untuk perbandingan plot
    df_raw = df_reindexed.copy()

    # --- TAHAP 2: HAMPEL FILTER & IMPUTASI HIBRIDA ---
    kolom_sensor = ['temperature', 'humidity', 'pressure', 'dew']
    window = 12
    n_sigmas = 3

    for col in kolom_sensor:
        if col in df_reindexed.columns:
            rolling_median = df_reindexed[col].rolling(window=window, center=True).median()
            deviasi = np.abs(df_reindexed[col] - rolling_median)
            mad = deviasi.rolling(window=window, center=True).median()
            threshold = n_sigmas * 1.4826 * mad
            outlier_idx = deviasi > threshold

            df_reindexed.loc[outlier_idx, col] = np.nan

            df_reindexed[col] = df_reindexed[col].interpolate(
                method='pchip',
                limit=4,
                limit_direction='forward'
            )

            nama_kolom_era5 = era5_mapping.get(col)
            if nama_kolom_era5 and nama_kolom_era5 in df_era5_reference.columns:
                df_reindexed[col] = df_reindexed[col].fillna(df_era5_reference[nama_kolom_era5])

            df_reindexed[col] = df_reindexed[col].bfill().ffill()

    # --- TAHAP 3: PENANGANAN KHUSUS HUJAN (ASIMILASI ERA5) ---
    kolom_hujan = ['rain_mm', 'rainfall', 'rainrate']
    for col in kolom_hujan:
        if col in df_reindexed.columns:
            nama_kolom_era5 = era5_mapping.get(col)
            if nama_kolom_era5 and nama_kolom_era5 in df_era5_reference.columns:
                df_reindexed[col] = df_reindexed[col].fillna(df_era5_reference[nama_kolom_era5])

            df_reindexed[col] = df_reindexed[col].fillna(0.0)

    print("✅ Pipeline Selesai! Data sudah Terstandarisasi Mutlak (PCHIP + ERA5).")
    return df_raw, df_reindexed

# ==============================================================================
# 2. FUNGSI VISUALISASI SEBELUM VS SESUDAH
# ==============================================================================
def plot_sebelum_sesudah(df_raw, df_clean, nama_kolom, satuan, start_time=None, end_time=None):
    if start_time and end_time:
        df_raw_plot = df_raw.loc[start_time:end_time]
        df_clean_plot = df_clean.loc[start_time:end_time]
        judul_waktu = f"({start_time} s.d {end_time})"
    else:
        df_raw_plot = df_raw
        df_clean_plot = df_clean
        judul_waktu = "(Semua Data)"

    plt.figure(figsize=(15, 6))

    # Plot Data Mentah
    plt.plot(
        df_raw_plot.index, df_raw_plot[nama_kolom],
        color='red', alpha=0.4, label='Sebelum (Kotor / Alat Mati / Belum Ada)',
        marker='x', markersize=4, linestyle='--'
    )

    # Plot Data Bersih (IoT + ERA5)
    plt.plot(
        df_clean_plot.index, df_clean_plot[nama_kolom],
        color='blue', linewidth=2, label='Sesudah (Hampel + PCHIP + ERA5)'
    )

    plt.title(f'Efek Pembersihan & Asimilasi Data: {nama_kolom.capitalize()} {judul_waktu}', fontsize=14, fontweight='bold')
    plt.ylabel(f'{nama_kolom.capitalize()} ({satuan})', fontsize=12)
    plt.xlabel('Waktu', fontsize=12)
    plt.legend(fontsize=11, loc='best')
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.tight_layout()
    plt.show()

# ==============================================================================
# 🚀 CARA PENGGUNAAN (EKSEKUSI)
# ==============================================================================

# 1. Tentukan batas waktu mutlak Anda
start_global = '2025-01-01 00:00:00'
end_global = '2025-12-31 23:59:59'

# 2. Eksekusi fungsi dengan memasukkan data IoT, ERA5, dan batas waktu
# df_raw_03, df_clean_03 = bersihkan_data_hourly_hibrida(df_hourly, df_era5, start_global, end_global)

# 3. Plot hasilnya
# plot_sebelum_sesudah(df_raw_03, df_clean_03, 'temperature', '°C', start_global, end_global)

# %%
df_raw_05, df_clean_05 = bersihkan_data_hourly_hibrida(df_hourly, df_era5, start_global, end_global)

# %%
df_clean_05.head(20)

# %%
# 2. Plot hasilnya sesuai rentang waktu Anda
start_time = '2025-01-01 00:00:00'
end_time = '2025-01-31 23:59:59'

plot_sebelum_sesudah(df_raw_05, df_clean_05, 'temperature', '°C', start_time, end_time)
plot_sebelum_sesudah(df_raw_05, df_clean_05, 'humidity', '%', start_time, end_time)
plot_sebelum_sesudah(df_raw_05, df_clean_05, 'pressure', 'hPa', start_time, end_time)
plot_sebelum_sesudah(df_raw_05, df_clean_05, 'dew', '°C', start_time, end_time)
plot_sebelum_sesudah(df_raw_05, df_clean_05, 'rainrate', 'mm/jam', start_time, end_time)