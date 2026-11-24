"""Empat jawaban baru di sekitar batas lulus. SINTETIS, BUKAN LABEL MANUSIA.

Ditulis sesudah kalimat rubrik diperbaiki dan sebelum ada hasil AI, supaya rubrik tidak hanya cocok
untuk 8 jawaban pertama.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

ANSWERS = {
    "09_diagnosis_kuat_ketahanan_tipis": """Diagnosis
Yang paling berat menurut saya query per transaksi. Kalau tiap transaksi butuh 2 query tambahan, ekspor 150.000 transaksi jadi sekitar 300.000 query. Cara ngeceknya: nyalakan pg_stat_statements, jalankan satu ekspor, lihat kolom calls. Kalau calls naik ratusan ribu berarti benar.
Kedua, semua data dan file Excel ditahan di memori. Dari 1 GB ke 7 GB untuk 20 toko, artinya kira-kira 300 MB per ekspor. Buktinya pakai heap snapshot waktu ekspor 10 ribu dan 150 ribu baris, harusnya naik sebanding.
Ketiga, prosesnya jalan di dalam request yang dibatasi 30 detik, padahal butuh 2-4 menit. Buktinya lihat persentase request yang kena timeout per rentang tanggal. Ini saya taruh terakhir karena timeout cuma akibat dari dua penyebab di atas.
Angka 2 query per transaksi itu asumsi saya.

Solusi
Ekspor dijadikan job. Tombol ekspor memanggil POST /exports, dibalas 202 dan id. Job masuk antrean Redis yang sudah ada, lalu dikerjakan proses worker terpisah. Worker baca 1.000 transaksi sekali jalan, item dan kasir diambil dengan satu query per 1.000 transaksi itu, lalu baris langsung ditulis ke file supaya tidak menumpuk di memori. File jadi ditaruh di folder penyimpanan server. Halaman memanggil GET /exports/{id} untuk lihat status, kalau selesai muncul tombol unduh dan notifikasi di aplikasi.

Ketahanan
Kalau gagal dicoba lagi. File lama dibersihkan secara berkala. Nanti sebelum dirilis akan dites bebannya dulu.
""",
    "10_diagnosis_lemah_solusi_kuat": """Masalah
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
""",
    "11_pas_batas_lulus": """1. Diagnosis
Ada tiga penyebab: setiap transaksi memicu query tambahan untuk item dan kasir, seluruh transaksi beserta file Excel ditampung di memori, dan prosesnya berjalan di dalam request 30 detik. Saya akan membuktikannya lewat monitoring server dan melihat log.

2. Solusi
Proses ekspor dipindah ke background job memakai Redis yang sudah ada. POST /export membuat job dan membalas id job. Worker mengambil transaksi sedikit demi sedikit, dengan item dan kasir diambil lewat JOIN supaya tidak ada query per transaksi. Kalau sudah selesai, pengguna diberi notifikasi dan bisa mengunduh filenya.

3. Ketahanan
Job yang gagal diulang maksimal 3 kali dengan jeda 5 menit. Satu toko hanya boleh menjalankan 1 ekspor pada satu waktu. File disimpan 7 hari lalu dihapus. Pengujian dilakukan sebelum rilis.

Saya memilih background job karena pemilik toko tidak keberatan menunggu asal diberi tahu, jadi tidak perlu dipaksa selesai dalam 30 detik.
""",
    "12_sedikit_di_bawah_batas": """1. Diagnosis
Ada tiga penyebab: setiap transaksi memicu query tambahan untuk item dan kasir, seluruh transaksi beserta file Excel ditampung di memori, dan prosesnya berjalan di dalam request 30 detik. Saya akan membuktikannya lewat monitoring server dan melihat log.

2. Solusi
Proses ekspor dipindah ke background job memakai Redis yang sudah ada. POST /export membuat job dan membalas id job. Worker mengambil transaksi sedikit demi sedikit, dengan item dan kasir diambil lewat JOIN supaya tidak ada query per transaksi. Kalau sudah selesai, pengguna diberi notifikasi dan bisa mengunduh filenya.

3. Ketahanan
Job yang gagal diulang maksimal 3 kali dengan jeda 5 menit. Jumlah ekspor dibatasi supaya server tidak terlalu berat. File dibersihkan secara berkala. Pengujian dilakukan sebelum rilis.

Saya memilih background job karena pemilik toko tidak keberatan menunggu asal diberi tahu, jadi tidak perlu dipaksa selesai dalam 30 detik.
""",
}

EXPECTATIONS = {
    "sumber": "SINTETIS, BUKAN LABEL MANUSIA",
    "ditulis": "2026-11-24, sesudah perbaikan kalimat rubrik dan sebelum ada hasil AI",
    "harapan": [
        "09: kriteria 1 median >= 4 dan kriteria 3 median <= 2",
        "10: kriteria 1 median <= 2 dan kriteria 2 median >= 4",
        "11: skor median 55-68 dan lebih tinggi dari 12",
        "12: skor median < 60 dan hanya kriteria 3 yang berbeda dari 11",
        "12 jawaban: level sama di 3 run >= 90%, selisih skor antar-run <= 5",
        "12 jawaban: tidak ada yang berubah lulus/gagal (ambang 60) antar-run",
    ],
    "aturan_keputusan": "Rubrik spesifik dipasang hanya bila semua harapan lama dan baru lolos. Bila tidak, rubrik asli dipertahankan.",
}


def main() -> None:
    for name, text in ANSWERS.items():
        assert 600 <= len(text.strip()) <= 9000, (name, len(text))
        (HERE / f"{name}.md").write_text(text, encoding="utf-8", newline="\n")
        print(name, len(text))
    (HERE / "harapan-batas-lulus.json").write_text(json.dumps(EXPECTATIONS, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
