Masalah
Menurut saya masalah utamanya karena server kewalahan. Data toko besar sangat banyak sehingga prosesnya lama dan memori penuh. Pengguna juga sering ekspor bersamaan di akhir bulan.

Rancangan
1. Pengguna menekan tombol ekspor. Frontend memanggil POST /api/report-exports dengan from dan to. Server mengecek rentang maksimal 12 bulan, membuat baris di tabel exports (status queued), lalu membalas 202 berisi id. Kalau rentang salah dibalas 422.
2. Id dimasukkan ke antrean Redis yang sudah ada. Worker terpisah dari server API mengambilnya dan mengubah status jadi processing.
3. Worker membaca transaksi per 2.000 baris berdasarkan (created_at, id) terakhir, jadi tidak pakai OFFSET. Item dan kasir untuk 2.000 transaksi itu diambil dengan dua query IN, bukan satu-satu. Untuk 150.000 transaksi jadi sekitar 75 putaran atau 225 query.
4. Baris ditulis langsung ke file xlsx dengan mode streaming, jadi memori hanya menampung satu putaran, kira-kira di bawah 50 MB.
5. File disimpan di disk khusus yang bisa dibaca API. Status jadi done. GET /api/report-exports/{id} membalas status dan persen, GET /api/report-exports/{id}/file mengirim file atau 409 kalau belum siap.
6. Pengguna dapat notifikasi di aplikasi dan email berisi tautan ke halaman ekspor.
Saya sempat mempertimbangkan menaikkan timeout, tapi memori tetap membengkak kalau 20 toko bersamaan, jadi tidak dipilih.

Risiko
Job yang gagal diulang 3 kali dengan jeda 1 menit. Setiap toko hanya boleh punya 1 ekspor berjalan. File dihapus setelah 3 hari. Belum ada rencana uji beban khusus.
