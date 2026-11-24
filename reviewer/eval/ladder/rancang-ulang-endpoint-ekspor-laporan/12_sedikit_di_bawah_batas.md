1. Diagnosis
Ada tiga penyebab: setiap transaksi memicu query tambahan untuk item dan kasir, seluruh transaksi beserta file Excel ditampung di memori, dan prosesnya berjalan di dalam request 30 detik. Saya akan membuktikannya lewat monitoring server dan melihat log.

2. Solusi
Proses ekspor dipindah ke background job memakai Redis yang sudah ada. POST /export membuat job dan membalas id job. Worker mengambil transaksi sedikit demi sedikit, dengan item dan kasir diambil lewat JOIN supaya tidak ada query per transaksi. Kalau sudah selesai, pengguna diberi notifikasi dan bisa mengunduh filenya.

3. Ketahanan
Job yang gagal diulang maksimal 3 kali dengan jeda 5 menit. Jumlah ekspor dibatasi supaya server tidak terlalu berat. File dibersihkan secara berkala. Pengujian dilakukan sebelum rilis.

Saya memilih background job karena pemilik toko tidak keberatan menunggu asal diberi tahu, jadi tidak perlu dipaksa selesai dalam 30 detik.
