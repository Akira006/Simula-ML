Aplikasi KasirKu dipakai 8.000 toko. Endpoint GET /api/reports/export?from=&to= membuat file .xlsx berisi semua transaksi pada rentang tanggal tertentu, lalu mengirimkannya sebagai respons. Rata-rata toko punya 300 transaksi per hari; toko besar bisa mencapai 5.000 transaksi per hari.

Cara kerja saat ini: (1) server mengambil seluruh transaksi pada rentang tanggal ke memori lewat satu query, (2) untuk setiap transaksi menjalankan query tambahan untuk item dan nama kasir, (3) menyusun seluruh file .xlsx di memori, (4) baru mengirimkannya. Proses ini berjalan di dalam request HTTP biasa dengan batas waktu 30 detik.

Gejala: ekspor 1 bulan untuk toko besar (sekitar 150.000 transaksi) memakan 2-4 menit dan hampir selalu timeout. Saat 20 toko mengekspor bersamaan di akhir bulan, penggunaan memori server naik dari 1 GB ke 7 GB dan endpoint lain ikut lambat. Dalam sebulan terakhir ada 310 tiket dukungan terkait ekspor gagal.

Tugas: jelaskan minimal tiga penyebab endpoint lambat dan boros memori. Pilih pendekatan perbaikan dan jelaskan alurnya. Jelaskan penanganan kegagalan di tengah proses, pembatasan, kebijakan retensi file, serta cara menguji.
