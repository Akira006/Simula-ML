## Diagnosis masalah
1. Untuk setiap transaksi ada query tambahan untuk item dan nama kasir (N+1). Dengan 2.000 transaksi per bulan di toko terbesar jumlah query menjadi sangat banyak dan ini paling berdampak.
2. Semua transaksi dan file .xlsx disusun di memori, sehingga saat 3 toko ekspor bersamaan memori naik ke 90 GB.
3. Ekspor berjalan di dalam request HTTP dengan batas 5 menit, padahal butuh 6 jam.
Untuk membuktikannya saya akan melihat log query dan memantau memori.

## Rancangan solusi
Ekspor dibuat menjadi proses latar belakang memakai antrean di Kafka dan data warehouse Snowflake yang sudah ada.
- POST /api/reports/export membuat permintaan ekspor dan langsung membalas id.
- GET /api/reports/export/{id} untuk mengecek statusnya.
- Worker mengambil data transaksi per bagian memakai LIMIT dan OFFSET, dan item serta kasir diambil dengan JOIN.
- File Excel disimpan di disk server, lalu pengguna mendapat notifikasi di aplikasi kalau file sudah siap.

## Ketahanan dan risiko
Kalau proses gagal, job dicoba lagi 3 kali. File dihapus setelah beberapa hari supaya disk tidak penuh. Jumlah worker dibatasi supaya server tidak terlalu berat. Sebelum rilis dilakukan load test dengan beberapa toko besar yang mengekspor bersamaan.
