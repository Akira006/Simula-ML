Diagnosis
Yang paling berat menurut saya query per transaksi. Kalau tiap transaksi butuh 2 query tambahan, ekspor 150.000 transaksi jadi sekitar 300.000 query. Cara ngeceknya: nyalakan pg_stat_statements, jalankan satu ekspor, lihat kolom calls. Kalau calls naik ratusan ribu berarti benar.
Kedua, semua data dan file Excel ditahan di memori. Dari 1 GB ke 7 GB untuk 20 toko, artinya kira-kira 300 MB per ekspor. Buktinya pakai heap snapshot waktu ekspor 10 ribu dan 150 ribu baris, harusnya naik sebanding.
Ketiga, prosesnya jalan di dalam request yang dibatasi 30 detik, padahal butuh 2-4 menit. Buktinya lihat persentase request yang kena timeout per rentang tanggal. Ini saya taruh terakhir karena timeout cuma akibat dari dua penyebab di atas.
Angka 2 query per transaksi itu asumsi saya.

Solusi
Ekspor dijadikan job. Tombol ekspor memanggil POST /exports, dibalas 202 dan id. Job masuk antrean Redis yang sudah ada, lalu dikerjakan proses worker terpisah. Worker baca 1.000 transaksi sekali jalan, item dan kasir diambil dengan satu query per 1.000 transaksi itu, lalu baris langsung ditulis ke file supaya tidak menumpuk di memori. File jadi ditaruh di folder penyimpanan server. Halaman memanggil GET /exports/{id} untuk lihat status, kalau selesai muncul tombol unduh dan notifikasi di aplikasi.

Ketahanan
Kalau gagal dicoba lagi. File lama dibersihkan secara berkala. Nanti sebelum dirilis akan dites bebannya dulu.
