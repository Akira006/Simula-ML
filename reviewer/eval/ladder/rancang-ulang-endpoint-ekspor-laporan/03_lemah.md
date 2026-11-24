Diagnosis
Endpoint ekspor lambat karena datanya banyak, apalagi untuk toko besar. Server juga kekurangan memori sehingga waktu banyak toko ekspor bersamaan jadi lambat semua. Batas waktu 30 detik juga terlalu pendek.

Solusi
Menurut saya server perlu di-upgrade, RAM dinaikkan menjadi 32 GB dan batas waktu request dinaikkan menjadi 10 menit supaya ekspor toko besar sempat selesai. Query juga perlu dioptimasi dan diberi index. Selain itu hasil ekspor bisa disimpan di cache Redis supaya kalau diminta lagi tidak perlu dibuat ulang. Endpoint tetap sama yaitu GET /api/reports/export. Pengguna diberi loading supaya tahu prosesnya sedang berjalan.

Risiko
Kalau gagal pengguna tinggal klik ekspor lagi. Nanti diuji dulu sebelum dirilis supaya tidak ada error.
