# Model biaya AI Reviewer

Skrip: `python -m reviewer.cost.cost_model` (dari folder `ml/`). Tabel lengkap yang dibuat otomatis ada di `results.md`. Harga di `pricing.json` disalin dari halaman pricing resmi Anthropic (https://platform.claude.com/docs/en/about-claude/pricing), dibuka **2026-10-09**.

> Semua angka di laporan ini adalah **perhitungan dari asumsi token**, bukan pengukuran. Belum ada panggilan API sungguhan (tidak ada API key). Ganti asumsi dengan token nyata dari golden set sebelum dipakai untuk pitch (AI-CONTEXT 16.3 no. 6).

## Harga yang dipakai (per 1 juta token)

| Model | Input | Cache write 5 menit | Cache read | Output |
| --- | ---: | ---: | ---: | ---: |
| Claude Haiku 5.5 (prompt <= 100.000 token) | $0,10 | $0,125 | $0,01 | $0,50 |
| Claude Haiku 5.5 (prompt > 100.000 token) | $0,50 | $0,625 | $0,05 | $2,50 |
| Claude Sonnet 5.5 | $2 | $2,50 | $0,10 | $10 |
| Claude Opus 5.5 | $4 | $5 | $0,20 | $20 |

Pengali yang perlu diperhatikan (dikutip dari halaman pricing):

- Cache write 5 menit = 1,25x harga input. Cache read = 0,1x untuk Haiku 5.5, tetapi **0,05x untuk Sonnet 5.5 dan Opus 5.5**.
- Tier Haiku 5.5 dihitung dari **seluruh** token input satu request, termasuk cache read dan cache write. Dengan batas 60.000 token per submission (AI-CONTEXT 5.5), setiap panggilan tetap di bawah 100.000 token. Bila batas dinaikkan mendekati 100.000, harga Haiku naik 5 kali lipat untuk panggilan itu.
- Harga AI-CONTEXT bagian 9 (input dan output) **cocok** dengan halaman resmi. Yang belum ada di AI-CONTEXT adalah harga cache.

## Asumsi

| Asumsi | Nilai | Alasan |
| --- | --- | --- |
| Jumlah kriteria | 5 | Sesuai skenario yang diminta. Contoh rubrik API punya 4, jadi angka ini sedikit konservatif. |
| Prefix yang di-cache | 10 rb / 40 rb / 60 rb token | Sistem + case + submission. Dianggap sama dengan "token input" di tabel AI-CONTEXT 12. |
| Blok kriteria (tidak di-cache) | 600 token per panggilan | Nama, deskripsi, 5 deskripsi level, instruksi akhir. |
| Panggilan berurutan | Ya, jeda < 5 menit | Desain antrean (6.1). Cache hanya tersedia setelah respons pertama mulai, jadi panggilan paralel tidak dapat cache hit. |
| Cache hit | Panggilan ke-2 sampai ke-5 | Panggilan ke-1 menulis cache (1,25x). |
| Panggilan feedback | 3.000 token input, tanpa cache, tanpa submission utuh | Skema output feedback berbeda. Dokumentasi structured outputs: mengganti `output_config.format` membatalkan prompt cache. |
| Output, profil "hemat" | 300 per kriteria + 400 feedback = 1.900 | Mendekati asumsi AI-CONTEXT (1.500). |
| Output, profil "dengan thinking" | 1.200 per kriteria + 1.000 feedback = 7.000 | Halaman models overview resmi menulis thinking ketiga model "Adaptive" (Opus 5.5: "always on"), jadi thinking aktif secara default dan ditagih sebagai output. Di Haiku 5.5 dan Sonnet 5.5 thinking bisa dikurangi atau dimatikan dengan pengaturan tertentu (belum diuji). Angka 1.200 dan 1.000 adalah tebakan. |
| Percobaan ulang | 0% | Belum ada data. Tambahkan setelah golden set. |

## Verifikasi tabel AI-CONTEXT bagian 12

AI-CONTEXT 12 tidak menyebut jumlah panggilan, tetapi angkanya cocok (setelah pembulatan) dengan rumus **satu panggilan, tanpa cache, output 1.500 token**. Contoh Sonnet 5.5 dengan 60 ribu token: 60.000 x $2/1jt + 1.500 x $10/1jt = $0,135, ditulis "±$0,14". Haiku 5.5 dengan 10 ribu token: $0,00175, ditulis "±$0,002". Jadi tabel itu **tidak** mencerminkan pola 6 panggilan.

## Hasil per penilaian

Profil output **hemat**:

| Skenario | Model | AI-CONTEXT 12 | 6 panggilan tanpa cache | 6 panggilan dengan cache | Dengan cache dibanding AI-CONTEXT |
| --- | --- | ---: | ---: | ---: | ---: |
| Isian teks (10 rb) | Haiku 5.5 | $0,0018 | $0,0066 | $0,0032 | 1,83x |
| Isian teks (10 rb) | Sonnet 5.5 | $0,035 | $0,131 | $0,060 | 1,71x |
| Dokumen/kode (40 rb) | Haiku 5.5 | $0,0047 | $0,0215 | $0,0082 | 1,72x |
| Dokumen/kode (40 rb) | Sonnet 5.5 | $0,095 | $0,431 | $0,147 | 1,55x |
| Batas 5.5 (60 rb) | Haiku 5.5 | $0,0067 | $0,0316 | $0,0115 | 1,70x |
| Batas 5.5 (60 rb) | Sonnet 5.5 | $0,135 | $0,631 | $0,205 | 1,52x |

Profil output **dengan thinking**: rasio dengan cache terhadap AI-CONTEXT naik menjadi **1,90x-3,29x** (Sonnet 60 rb: $0,256; Haiku 10 rb: $0,0058). Opus 5.5 selalu tepat 2x Sonnet 5.5 karena semua harganya 2x.

Rincian satu penilaian Sonnet 5.5, 60 ribu token, profil hemat: panggilan pertama (menulis cache) **$0,154**, empat panggilan berikutnya (membaca cache) **$0,041**, feedback **$0,010**, total **$0,205**. Tiga perempat biaya ada di panggilan pertama.

## Kesimpulan

1. **Dugaan tim terkonfirmasi arahnya, tetapi besarnya sedikit lebih tinggi.** Tabel AI-CONTEXT 12 dihitung sebagai satu panggilan sehingga terlalu rendah. Dengan pola 6 panggilan dan cache, biaya per penilaian **1,5-1,8x** angka AI-CONTEXT bila output kecil (dugaan tim 1,3-1,5x), dan **1,9-3,3x** bila thinking menambah output menjadi sekitar 7.000 token. Rasio terendah (1,52x) ada di Sonnet dengan submission besar, karena cache read Sonnet hanya 0,05x. Rasio Haiku lebih tinggi (1,70-1,83x) karena cache read-nya 0,1x dan porsi output relatif lebih besar.
2. **Kalimat "belum termasuk penghematan dari prompt caching" di AI-CONTEXT 12 menyesatkan.** Dibanding satu panggilan, pola 6 panggilan dengan cache tetap **lebih mahal**. Tanpa cache, 6 panggilan sekitar 3,7-4,7x angka AI-CONTEXT (output hemat) atau 5,1-5,2x (dengan thinking). Cache menekannya menjadi 1,5-1,8x atau 1,9-3,3x.
3. **Semua angka "dengan cache" mengandaikan panggilan feedback tanpa submission utuh** (usulan B5 di `docs/PROPOSED-CHANGES.md`). Bila feedback menyertakan submission, cache tidak terpakai untuk panggilan itu karena skemanya berbeda. Contohnya, Sonnet 5.5 dengan 60 ribu token naik dari $0,205 ke sekitar $0,325. Kelipatannya terhadap AI-CONTEXT menjadi 2,3-2,6x (output hemat) dan 2,8-3,9x (dengan thinking).
4. **Output adalah variabel terbesar yang belum diketahui.** Porsi output dalam biaya per penilaian: 8-32% di profil hemat, dan 25-63% di profil dengan thinking (tertinggi untuk isian teks 10 ribu token, karena prefix-nya kecil). `effort` yang rendah dan pengukuran token nyata di golden set adalah prioritas sebelum angka bulanan dipakai untuk pitch.
5. **Estimasi CONTEXT.md bagian 6 ($0,005-0,05 per review AI) tidak cocok dengan model mana pun.** Haiku 5.5: $0,003-0,014 per penilaian; Sonnet 5.5: $0,06-0,26, tergantung ukuran submission dan output.

## Bulanan (dengan cache)

Profil hemat:

Kolom terakhir adalah rumus AI-CONTEXT 12 (satu panggilan) yang dihitung ulang **per skenario**, tanpa percobaan ulang. Tabel bulanan AI-CONTEXT 12 sendiri memakai rata-rata ±$0,005 (Haiku) dan ±$0,10 (Sonnet) per penilaian **termasuk percobaan ulang**, yaitu ±$5 / ±$50 dan ±$100 / ±$1.000. Model ini memakai 0% percobaan ulang.

| Skenario | Model | 1.000 penilaian | 10.000 penilaian | Rumus AI-CONTEXT 12 per skenario (1.000 / 10.000) |
| --- | --- | ---: | ---: | --- |
| Isian teks | Haiku 5.5 | $3,20 | $32 | $1,75 / $17,50 |
| Isian teks | Sonnet 5.5 | $60 | $600 | $35 / $350 |
| Dokumen/kode | Haiku 5.5 | $8,15 | $81,50 | $4,75 / $47,50 |
| Dokumen/kode | Sonnet 5.5 | $147 | $1.470 | $95 / $950 |
| Batas 5.5 | Haiku 5.5 | $11,45 | $114 | $6,75 / $67,50 |
| Batas 5.5 | Sonnet 5.5 | $205 | $2.050 | $135 / $1.350 |

Profil dengan thinking:

| Skenario | Model | 1.000 penilaian | 10.000 penilaian |
| --- | --- | ---: | ---: |
| Isian teks | Haiku 5.5 | $5,75 | $57,50 |
| Isian teks | Sonnet 5.5 | $111 | $1.110 |
| Dokumen/kode | Haiku 5.5 | $10,70 | $107 |
| Dokumen/kode | Sonnet 5.5 | $198 | $1.980 |
| Batas 5.5 | Haiku 5.5 | $14 | $140 |
| Batas 5.5 | Sonnet 5.5 | $256 | $2.560 |

Belum termasuk percobaan ulang dan pajak. Angka Opus 5.5 ada di `results.md`.

## Cara menekan biaya (urut dari dampak terbesar)

1. Ukur token output nyata dan pilih `effort` serendah mungkin yang lolos golden set.
2. Pertahankan batas token per submission (5.5) dan penyaringan zip. Biaya hampir sebanding dengan ukuran prefix pada panggilan pertama.
3. Jangan menjalankan panggilan kriteria paralel: cache baru tersedia setelah respons pertama mulai.
4. Pertimbangkan cache 1 jam (`ttl: "1h"`, 2x harga input) hanya untuk blok sistem + case bila banyak peserta mengerjakan case yang sama dalam satu jam. Untuk submission tidak perlu, karena 5 panggilan selesai dalam beberapa menit.
5. Hasil ulang untuk submission identik dan pembatasan pemakaian (8) sudah ada di desain.
