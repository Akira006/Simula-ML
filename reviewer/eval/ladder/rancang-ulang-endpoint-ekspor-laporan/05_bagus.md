## Ringkasan
Ekspor dipindah dari request HTTP ke job latar belakang di Redis yang sudah ada, data dibaca bertahap, dan file ditulis secara streaming. Perubahan ini tidak butuh layanan data warehouse dan bisa dikerjakan 3 engineer.

## Diagnosis masalah (urut dampak)
1. N+1 query. Tiap transaksi memicu query untuk item dan nama kasir. Bila dua query per transaksi, 150.000 transaksi menghasilkan sekitar 300.000 query. Dengan asumsi 0,5 ms per query, ini saja sekitar 150 detik, sesuai gejala 2-4 menit. Bukti: pg_stat_statements (kolom calls dan total_exec_time) sebelum dan sesudah satu ekspor; jumlah calls harus naik sekitar 300.000.
2. Seluruh data dan workbook berada di memori. Kenaikan dari 1 GB ke 7 GB untuk 20 ekspor berarti sekitar 300 MB per ekspor, jadi memori tumbuh linear terhadap jumlah baris. Bukti: heap profile saat ekspor 10.000, 50.000, dan 150.000 baris; kalau hipotesis benar, grafiknya lurus.
3. Proses panjang menempati request HTTP. Batas 30 detik pasti terlewati oleh proses 2-4 menit, lalu pengguna menekan ulang sehingga beban bertambah. Bukti: histogram durasi endpoint, jumlah status timeout, dan jumlah permintaan ulang toko yang sama dalam 5 menit.
4. Kemungkinan index tidak cocok. Bukti: EXPLAIN (ANALYZE, BUFFERS) pada query utama; bila ada sequential scan, hipotesis benar. Ini dampak terkecil karena hanya satu query.
Semua angka per query di atas adalah asumsi dan harus diukur dulu.

## Rancangan solusi
### Alternatif yang dipertimbangkan
- Menaikkan timeout dan RAM: cepat, tetapi 40 toko bersamaan tetap menghabiskan memori. Ditolak.
- Streaming langsung di respons HTTP: hemat memori, tetapi koneksi 1 menit lebih rawan putus di jaringan toko. Ditolak untuk rentang besar.
- Job latar belakang: menambah kerumitan (status, pembersihan file), tetapi pemilik toko sudah setuju menunggu asalkan diberi tahu. Dipilih.

### Kontrak API
- POST /api/reports/exports, body {from, to}, header Idempotency-Key. Balasan 202 {exportId, status: "queued"}. Rentang di atas 12 bulan dibalas 422. Permintaan sama yang masih berjalan membalas exportId yang sama (200).
- GET /api/reports/exports/{id}: 200 {status: queued|processing|done|failed, progress, errorCode, expiresAt}. Toko lain mendapat 404.
- GET /api/reports/exports/{id}/download: 302 ke URL bertanda tangan 10 menit; 409 bila belum selesai; 410 bila kedaluwarsa.
- Endpoint lama dipertahankan 1 rilis, lalu membalas 410 dengan petunjuk.

### Alur
Tombol ditekan -> baris export_jobs dibuat (PostgreSQL sebagai sumber status) -> id masuk antrean Redis -> worker terpisah dari proses API mengambil job -> data dibaca 2.000 baris per batch dengan keyset pagination (created_at, id) sampai batas waktu saat job dibuat -> item dan kasir diambil per batch dengan WHERE transaction_id = ANY(...) -> baris ditulis dengan streaming writer xlsx ke file sementara -> file diunggah ke volume disk khusus yang dibagi API dan worker -> status done -> notifikasi di aplikasi dan email.
Query turun dari sekitar 300.000 menjadi sekitar 225 (75 batch x 3). Memori per job dibatasi satu batch, target di bawah 60 MB. Excel membatasi 1.048.576 baris per sheet, jadi data dipecah per sheet bila lebih dari 1 juta baris.
Index: CREATE INDEX CONCURRENTLY pada transactions (store_id, created_at, id).

## Ketahanan dan risiko
- Gagal di tengah: worker menulis heartbeat tiap 10 detik. Job tanpa heartbeat 60 detik dikembalikan ke antrean. File xlsx tidak bisa dilanjutkan dari tengah, jadi dibuat ulang dari awal ke file sementara baru; file baru hanya dipakai setelah lengkap. Coba ulang 3 kali dengan jeda 30 detik, 2 menit, 10 menit, lalu failed dan pengguna diberi tombol coba lagi.
- Redis mati: status tetap aman di PostgreSQL; penyapu tiap 5 menit memasukkan ulang job queued.
- Keadilan antar toko: 1 job aktif dan 5 job per hari per toko, 4 worker global, antrean kecil (di bawah 20.000 baris) dan besar terpisah agar toko kecil tidak menunggu toko besar.
- Beban database: worker memakai pool 4 koneksi dan statement_timeout 20 detik.
- Retensi: file dihapus setelah 7 hari, metadata 90 hari, URL berlaku 10 menit agar data penjualan tidak bocor.
- Uji beban: data sintetis 150.000 transaksi x 20 toko. Lulus bila semua ekspor selesai di bawah 10 menit, memori worker di bawah 500 MB, p95 endpoint lain naik kurang dari 10%. Uji gagal: hentikan paksa worker di tengah proses, matikan Redis 1 menit, penuhi disk.
- Rilis: feature flag 5% toko, 25%, lalu semua. Ukur tiket dukungan (sekarang 310 per bulan) dengan target di bawah 30. Rollback dengan mematikan flag.
- Risiko tersisa: 4 worker dapat membentuk antrean di akhir bulan. Bila satu job 2 menit, 20 job selesai sekitar 10 menit, masih sesuai target tetapi tanpa cadangan.
