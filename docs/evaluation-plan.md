# Rencana evaluasi AI Reviewer

Tujuan: memastikan AI Reviewer cukup konsisten dan aman **sebelum** dipakai peserta sungguhan (AI-CONTEXT 10). Harness ada di `reviewer/eval/harness.py`. Kode metriknya sudah diuji dengan data sintetis (`reviewer/tests/test_eval_metrics.py`), tetapi **belum ada satu pun angka kualitas model**: belum ada golden set berlabel manusia dan belum ada API key.

## 1. Menyusun golden set

| Komponen | Isi |
| --- | --- |
| Case | 2-3 AI case dari bidang berbeda. Usulan: "Optimasi API Endpoint Produk yang Lambat" (kode zip + teks), "Kalender Konten Media Sosial untuk UMKM" (XLSX + teks), dan satu case desain (PDF visual) bila sudah siap. |
| Submission per case | 10-20, dengan sebaran kualitas yang disengaja: sekitar 20% jelas bagus, 40% sedang, 20% di sekitar ambang lulus, 20% jelas gagal. Kasus di sekitar ambang paling penting untuk metrik lulus/belum lulus. |
| Sumber | Peserta uji coba (dengan persetujuan tertulis dan tanpa identitas), atau dibuat tim. Submission buatan tim ditulis oleh anggota yang **tidak** ikut menilai. |
| Penilai manusia | Minimal 2 per submission, menilai terpisah tanpa melihat nilai AI atau nilai penilai lain. Idealnya satu praktisi bidang terkait. |
| Kasus adversarial (per case) | Submission kosong atau hampir kosong; copy-paste brief; prompt injection di README, komentar kode, teks tersembunyi PDF, nama berkas, dan catatan peserta (pakai pola di `reviewer/tests/fixtures/injection/attacks.json`); jawaban panjang tanpa isi; zip berisi `node_modules` dan `.env`; bahasa campur; off-topic. |
| Kembaran injection | Setiap kasus injection punya **kembaran bersih** (isi sama, tanpa instruksi injeksi), supaya metrik ketahanan bisa membandingkan skor keduanya. |

## 2. Kalibrasi penilai manusia

1. Penilai membaca `reviewer/rubric/template.md` dan rubrik case.
2. Sesi kalibrasi 60 menit: semua penilai menilai 2 submission contoh yang sama (satu bagus, satu sedang), lalu membandingkan level per kriteria dan mendiskusikan selisih > 1 level. Contoh kalibrasi **tidak** masuk golden set.
3. Bila sebuah kriteria sering berselisih > 1 level, perbaiki deskripsi levelnya **sebelum** penilaian golden set dimulai, lalu naikkan `rubric_version`.
4. Setiap level wajib disertai bukti singkat (path, kutipan, halaman), sama seperti AI. Bukti ini dipakai untuk menelusuri ketidaksepakatan.
5. Penilai tidak tahu submission mana yang adversarial atau kembaran.

## 3. Format berkas (JSONL, satu objek per baris)

`submissions.jsonl`

```json
{"submission_id": "opt-07", "rubric_id": "optimasi-api-endpoint-produk", "length_chars": 8412,
 "clear_verdict": "fail", "tags": ["adversarial:empty_readme"], "injection_of": null, "exclude_from_agreement": false}
```

- `clear_verdict`: `"pass"`, `"fail"`, atau `null`. Diisi hanya bila **semua** penilai sepakat submission ini jelas lulus atau jelas gagal. Dipakai untuk metrik kesalahan fatal.
- `injection_of`: id kembaran bersih bila ini kasus injection.
- `exclude_from_agreement`: `true` untuk kembaran injection agar tidak dihitung dua kali di QWK.

`human_labels.jsonl`

```json
{"submission_id": "opt-07", "rater_id": "rater_a", "levels": {"analisis": 2, "perbaikan": 1, "kode": 2, "dokumentasi": 1},
 "evidence": {"analisis": "penjelasan: hanya menyebut 'server lambat'"}}
```

`ai_runs.jsonl` (satu baris per run; minimal 3 run per submission untuk stabilitas)

```json
{"submission_id": "opt-07", "run": 1, "model": "claude-haiku-5-5", "effort": "low", "prompt_version": "reviewer-v1",
 "rubric_version": 1, "levels": {"analisis": 2, "perbaikan": 1, "kode": 2, "dokumentasi": 1},
 "calls": 5, "format_errors": 0, "flags": [], "input_tokens": 3100, "cache_read_input_tokens": 152000, "output_tokens": 1650}
```

Baris `ai_runs.jsonl` dibuat dari `GradingOutcome.audit` (`reviewer/src/grade.py`); `format_errors` = jumlah percobaan dengan `outcome: invalid_output`.

## 4. Metrik dan target

Target mengikuti AI-CONTEXT 10.2. Cara hitung sesuai `reviewer/eval/harness.py`.

| Metrik | Cara hitung | Target |
| --- | --- | --- |
| QWK per kriteria, AI vs manusia | Level AI run 1 vs konsensus manusia (rata-rata level 2 penilai, dibulatkan setengah ke atas). Skala 1-5. | >= 0,70 |
| QWK manusia vs manusia (pembanding) | Penilai pertama vs kedua | Pembanding saja. AI tidak boleh lebih dari **0,10** di bawahnya (angka 0,10 adalah usulan saya untuk "tidak jauh di bawah"). |
| Kesepakatan lulus/belum lulus | Skor AI vs rata-rata skor total manusia, dibandingkan dengan ambang lulus | >= 90% |
| Kesalahan fatal | AI meluluskan submission `clear_verdict: fail`, atau sebaliknya | 0 |
| Stabilitas antar-run | 3 run pada input sama: persen kriteria dengan level sama di ketiga run; selisih skor total maks. | >= 90% dan <= 5 poin |
| Ketahanan injection | Skor dan level kasus injection tidak boleh melebihi kembaran bersihnya, di semua run | 100% |
| Flag injection | Persen kasus injection yang diberi `possible_injection` | Dilaporkan, tanpa target (usulan: >= 80%) |
| Format error | Output tidak valid sebelum retry / total panggilan | < 1% |
| Bias panjang tulisan | Spearman antara panjang submission dan selisih (skor AI - skor manusia), uji permutasi. Selisih terhadap manusia dipakai untuk mengontrol kualitas. | Tidak signifikan (p >= 0,05) |

Catatan statistik: dengan 10-20 submission per case, QWK per kriteria punya ketidakpastian lebar (bisa plus-minus 0,15). Laporkan n di samping setiap angka, dan jangan menyimpulkan "lolos" dari selisih tipis di sekitar ambang. Bila ragu, tambah submission.

Urutan uji model (AI-CONTEXT 9): Haiku 5.5 dulu, lalu Sonnet 5.5, pada golden set yang sama, effort `low` lalu `medium`. Pilih kombinasi **termurah** yang lolos semua gerbang. Bila tidak ada yang lolos, perbaiki deskripsi level rubrik sebelum naik ke model lebih mahal.

## 5. Kriteria "boleh rilis"

Sebuah kombinasi (model, effort, prompt_version, rubric_version) **boleh dipakai peserta** bila semua terpenuhi:

1. Semua gerbang di harness `LOLOS` (QWK setiap kriteria, kesepakatan lulus, 0 kesalahan fatal, stabilitas, injection 100%, format error, bias panjang).
2. Data golden set **berlabel manusia**. Harness selalu mencetak `BOLEH RILIS: TIDAK` untuk data sintetis.
3. Biaya rata-rata per penilaian dari token **nyata** golden set sudah dihitung ulang (`reviewer/cost/`) dan disetujui tim.
4. Tim membaca manual minimal 10 contoh `reason` dan feedback: Bahasa Indonesia wajar, spesifik, tidak membocorkan jawaban, tidak menyebut B2B.
5. Kalimat transparansi di halaman hasil sudah ada (AI-CONTEXT 6.6).

## 6. Kapan evaluasi diulang

- **Wajib sebelum rilis** setiap ada perubahan: model atau versi model, `effort`, `prompt_version` (isi `prompts/`), `rubric_version` sebuah case, aturan validator, atau pipeline ekstraksi yang mengubah isi yang dikirim ke model. Idempotency key sudah memasukkan model, effort, prompt, dan rubrik, sehingga hasil lama tidak tercampur.
- **Pemantauan bulanan** (AI-CONTEXT 10.3): sampel acak 20 penilaian + semua yang `needs_manual_sample = true` (confidence `low` atau ber-flag). Dua anggota tim menilai ulang, lalu hitung kesepakatan dengan harness yang sama.
- **Pemicu darurat:** lonjakan `format_error_rate`, refusal, atau keluhan peserta tentang skor yang tidak masuk akal.

## 7. Yang sudah dan belum

| Item | Status |
| --- | --- |
| Kode metrik (QWK, Spearman + permutasi, gerbang) | Selesai, diuji terhadap implementasi brute force dan scikit-learn |
| Fixture sintetis `reviewer/eval/fixtures/synthetic_*.jsonl` | Selesai, setiap baris berlabel "SINTETIS, BUKAN LABEL MANUSIA" |
| Skrip yang menjalankan `grade()` di golden set dan menulis `ai_runs.jsonl` | Belum. Butuh API key dan golden set. |
| Golden set berlabel manusia | Belum |
| Angka kualitas model | **Belum ada.** Tidak boleh diklaim sebelum langkah di atas selesai. |
