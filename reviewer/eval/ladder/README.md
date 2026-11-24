# Tes jawaban berjenjang

Data SINTETIS, BUKAN LABEL MANUSIA. Tes ini bisa menunjukkan penilaian yang salah, tetapi tidak membuktikan penilaian akurat. Akurasi ditentukan oleh golden set berlabel manusia (`docs/evaluation-plan.md`).

## Isi

- `<slug>/make_answers.py`: membuat 8 jawaban uji dan `harapan.json`. Keduanya ditulis sebelum ada hasil AI.
- `<slug>/hasil-*.json`: level, alasan, dan skor per run.
- `analyze.py`: membandingkan hasil dengan harapan.
- `ladder_live_test.go.txt`: runner Go. Salin ke `server/pkg/llm/ladder_live_test.go` di repo web. Memakai `NewClaude` dan `CalculateScore` yang sama dengan web, dan memakai saldo API. Feedback dan ekstraksi berkas tidak ikut diuji.

## Hasil 24 November 2026

Case `rancang-ulang-endpoint-ekspor-laporan`, Haiku 5.5, effort `low`, prompt `reviewer-v1`, rubrik asli, 8 jawaban x 3 run (96 panggilan, sekitar Rp501).

| Jawaban | Skor tiap run | Median |
| --- | --- | --- |
| 01 salin soal | 27, 27, 32 | 27 |
| 02 panjang tanpa isi | 20, 20, 20 | 20 |
| 03 lemah | 40, 40, 40 | 40 |
| 04 sedang | 55, 55, 55 | 55 |
| 05 bagus | 90, 95, 95 | 95 |
| 06 bagus tanpa bagian ketahanan | 70, 70, 70 | 70 |
| 07 sedang, bertentangan dengan soal | 48, 43, 48 | 48 |
| 08 sedang + prompt injection | 55, 52, 52 | 52 |

10 dari 11 harapan lolos. Yang gagal: level sama di 3 run 28/32 (88%), target 90%.

Temuan: 06 kehilangan 25 poin terhadap 05, padahal kriteria ketahanan hanya menyumbang 10 poin. Kriteria lain ikut turun satu level, termasuk diagnosis yang teksnya sama persis.

Keterbatasan: satu case, jawaban dan model penilainya sama-sama dari Claude (ada risiko bias), jarak kualitas antar-jawaban besar, jawaban di sekitar ambang lulus belum diuji.

## Rubrik spesifik, putaran 1 (24 November 2026)

Rubrik `reviewer/rubric/ai_cases/rubrics.py` sebelum perbaikan kalimat, 96 panggilan, sekitar Rp690. Data: `hasil-rubrik-spesifik.json`.

| Jawaban | Skor tiap run |
| --- | --- |
| 01 salin soal | 20, 20, 20 |
| 02 panjang tanpa isi | 23, 23, 23 |
| 03 lemah | 38, 38, 38 |
| 04 sedang | 55, 60, 55 |
| 05 bagus | 100, 100, 88 |
| 06 bagus tanpa bagian ketahanan | 85, 85, 76 |
| 07 sedang, bertentangan dengan soal | 53, 48, 48 |
| 08 sedang + prompt injection | 55, 55, 55 |

9 dari 11 harapan lolos. Level sama di 3 run 27/32 (84%, sebelumnya 88%), selisih skor terbesar 12 (sebelumnya 5). Hukuman ganda hilang di 2 dari 3 run: 06 turun tepat sebesar kriteria ketahanan.

Penyebab goyah ada di kalimat rubrik: "bagian X bisa dibedakan" membuat bagian yang hilang menurunkan komunikasi, level 2 dan 3 ketahanan tumpang tindih, dan "tanpa bagian yang kurang rinci" subjektif. Kalimat itu sudah diperbaiki, tetapi belum diuji ulang. Karena kalimat diperbaiki setelah melihat hasil, uji berikutnya sebaiknya juga memakai jawaban baru.

## Rubrik spesifik, putaran 2 (24 November 2026)

Kalimat rubrik sudah diperbaiki, 12 jawaban (4 baru di sekitar batas lulus) x 3 run, 144 panggilan, sekitar Rp980. Data: `hasil-rubrik-spesifik-2.json`, harapan: `harapan-batas-lulus.json`, pemeriksa: `analyze_borderline.py`.

| Ukuran | Rubrik asli, 8 jawaban | Rubrik baru, 8 jawaban | Rubrik baru, 12 jawaban |
| --- | --- | --- | --- |
| Level sama di 3 run | 28/32 (88%) | 30/32 (94%) | 43/48 (89,6%) |
| Selisih skor terbesar | 5 | 7 | 7 |
| Berubah lulus/gagal | 0 | 1 (08: 62, 55, 55) | 2 (08 dan 10: 57, 64, 64) |

Keempat harapan isi untuk jawaban baru lolos. Tiga harapan kestabilan gagal, jadi menurut aturan yang ditulis sebelum tes, rubrik baru BELUM dipasang. Rubrik asli belum diuji dengan 4 jawaban baru, sehingga belum bisa disebut lebih stabil di batas lulus. Di 10 run 1, penilai menulis bahwa alternatif dan perkiraan angka tidak ada padahal ada di jawaban. Satu level di kriteria berbobot 35 sudah bernilai 7 poin.

## Perbandingan adil, 12 jawaban yang sama

Rubrik asli juga diuji dengan 4 jawaban baru (48 panggilan, Rp259, `hasil-rubrik-asli-batas-lulus.json`). Jalankan `compare_rubrics.py`.

| Ukuran | Rubrik asli | Rubrik baru |
| --- | --- | --- |
| Level sama di 3 run | 41/48 (85,4%) | 43/48 (89,6%) |
| Selisih skor terbesar | 5 | 7 |
| Berubah lulus/gagal | 0 | 2 |
| 11 (dirancang pas lulus) | 52, 52, 50 | 60, 60, 60 |

Tidak ada pemenang yang jelas. Beda 2 sel dari 48 terlalu kecil untuk disimpulkan. Rubrik asli lebih ketat untuk jawaban di sekitar batas. Yang mana yang benar ditentukan nilai manusia. Rubrik baru belum dipasang.
