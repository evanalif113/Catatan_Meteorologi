import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime  # Untuk konversi timestamp ke human-readable
import pandas as pd

# Konfigurasi database sumber
source_cred = credentials.Certificate("D:/staklimjerukagung-firebase-adminsdk-kcfma-e091165a9b.json")
firebase_admin.initialize_app(source_cred, {
    'databaseURL': 'https://staklimjerukagung-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

# 1. INPUT RENTANG WAKTU (Human Readable)
input_waktu_mulai = input("Masukkan waktu mulai (format: DD-MM-YYYY HH:MM:SS): ")
input_waktu_selesai = input("Masukkan waktu selesai (format: DD-MM-YYYY HH:MM:SS): ")
input_station_id = input("Masukkan station_id yang ingin diupdate: ")
format_waktu = "%d-%m-%Y %H:%M:%S"

# 2. KONVERSI KE UNIX TIMESTAMP
unix_mulai = int(datetime.strptime(input_waktu_mulai, format_waktu).timestamp())
unix_selesai = int(datetime.strptime(input_waktu_selesai, format_waktu).timestamp())

print(f"Mencari data dari UNIX {unix_mulai} hingga {unix_selesai}...")

# 3. QUERY RENTANG WAKTU DI FIREBASE
path_utama = f'/auto_weather_stat/{input_station_id}/data'  # Sesuaikan dengan station_id yang diinput
ref = db.reference(path_utama)

# Mencari folder yang namanya (key) berada di antara unix_mulai dan unix_selesai
hasil_query = ref.order_by_key().start_at(str(unix_mulai)).end_at(str(unix_selesai)).get()

# 4. EKSEKUSI UPDATE
if hasil_query:
    print(f"Ditemukan {len(hasil_query)} data. Memulai update...")
    for unix_key, val in hasil_query.items():
        try:
            # Langsung tembak ke alamat spesifik dan ubah rain_rate
            db.reference(f"{path_utama}/{unix_key}").update(
                {'rainfall': 0.0,
                 'rainrate': 0.0})
            print(f"✅ Sukses: Folder {unix_key} diupdate.")
        except Exception as e:
            print(f"❌ Error pada {unix_key}: {e}")
            
else:
    print("⚠️ Tidak ada data dalam rentang waktu tersebut.")