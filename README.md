# Simula ML/LLM: kuis minat v2 dan desain AI Reviewer

Pekerjaan tim ML/LLM untuk dua fitur di `AI-CONTEXT.md`: **kuis minat** (bagian 14.4) dan **AI Reviewer** (bagian 5-12). Semua kode baru ada di folder ini. `client/` dan `AI-CONTEXT.md` tidak diubah; usulan perubahan ditulis di [`docs/PROPOSED-CHANGES.md`](docs/PROPOSED-CHANGES.md).

Dokumentasi lengkap proyek: [`docs/DOKUMENTASI.md`](docs/DOKUMENTASI.md) (Bahasa Indonesia) dan [`docs/DOCUMENTATION.md`](docs/DOCUMENTATION.md) (English).

> **Belum ada panggilan LLM sungguhan.** Tidak ada `ANTHROPIC_API_KEY` di lingkungan pengembangan, jadi semua tes memakai `MockClient`. Tidak ada klaim apa pun tentang kualitas model di repo ini.

## Menjalankan

Python 3.11+ (diuji dengan 3.12.4). Semua perintah dijalankan dari folder `ml/`.

```bash
pip install -r requirements.txt
```

```bash
python -m pytest
```

| Perintah | Hasil |
| --- | --- |
| `python -m quiz.src.analyze` | Analisis struktur kuis v1 dan v2 langsung dari config (A1) |
| `python -m quiz.simulation.run` | Simulasi bias, menulis `quiz/simulation/results/` (sekitar 15 detik) |
| `python -m quiz.test_vectors.generate` | Membuat ulang test vector setelah config kuis berubah |
| `python -m reviewer.src.rubric reviewer/rubric/examples/optimasi-api-endpoint-produk.rubric.json` | Validasi rubrik |
| `python -m reviewer.cost.cost_model` | Model biaya, menulis `reviewer/cost/results.md` |
| `python -m reviewer.eval.harness --rubrics reviewer/rubric/examples --submissions reviewer/eval/fixtures/synthetic_submissions.jsonl --human reviewer/eval/fixtures/synthetic_human_labels.jsonl --ai reviewer/eval/fixtures/synthetic_ai_runs.jsonl` | Harness evaluasi pada data **sintetis** (hanya menguji kode metrik) |

Untuk memakai Claude API: salin `.env.example` menjadi `.env`, isi `ANTHROPIC_API_KEY`, pasang `anthropic`. `reviewer.src.llm_client.make_client()` otomatis memilih `AnthropicClient` bila kunci ada. Model dan effort diambil dari `reviewer/config/models.json`, bukan dari kode.

## Struktur

```
ml/
  docs/        PROPOSED-CHANGES.md, ai-system-design.md, evaluation-plan.md
  quiz/
    config/          quiz.v2.json (sumber kebenaran), quiz.v1.json (reproduksi draf, pembanding)
    src/             config.py, scoring.py (referensi), analyze.py
    tests/           unit test, kecocokan mesin simulasi, test vector
    test_vectors/    vectors.json (45 kasus) + generate.py
    simulation/      engine.py, run.py, REPORT.md, results/
    CHANGELOG-v2.md
  reviewer/
    rubric/          template.md, rubric.schema.json, examples/ (rubrik + data case)
    schemas/         criterion_result.schema.json, feedback_result.schema.json
    prompts/v1/      system.md, case.md, criterion.md, feedback_system.md, feedback.md, builder.py
    src/             score.py, validate.py, rubric.py, llm_client.py, grade.py
    config/          models.json
    cost/            pricing.json, cost_model.py, REPORT.md, results.md
    eval/            metrics.py, harness.py, make_synthetic.py, fixtures/ (SINTETIS)
    tests/
```

## Ringkasan temuan

### Kuis minat: v1 (draf AI-CONTEXT 14.4) vs v2

Dari `python -m quiz.simulation.run` (20.000 responden acak per varian, 2.000 persona sintetis per bidang, seed 20261009). **Jawaban sintetis: ini hanya menguji bias struktural, bukan bukti kuis cocok untuk mahasiswa sungguhan.**

| Metrik | v1 draf | v2 |
| --- | ---: | ---: |
| Poin maks. per bidang (tanpa jurusan) | 5-12 | 8 untuk semua |
| Bidang di luar pita 15-35% masuk top-3 (acak) | 9 dari 12 | 0 dari 12 |
| Rentang masuk top-3 (acak) | 3,6% (HR) - 53,7% (Data) | 24,0% - 25,7% |
| Persona: top-1 terendah | 0,0% (Mobile) | 93,6% (Mobile) |
| Persona: top-3 terendah | 88,2% (Legal) | 99,1% (Front-End) |
| Persona gagal target (top-3 >= 90%, top-1 >= 60%) | 4 dari 12 | 0 dari 12 |
| Persona Back-End dengan top-3 semuanya tech | 84,2% | 9,0% |
| Pergeseran top-3 terbesar karena satu bobot +/-1 | 15,1 pp | 6,6 pp |

Temuan utama:

1. **Dugaan bias terbukti.** Poin maksimum v1 persis seperti yang diduga (Data 12 ... Legal 5), dan opsi "teknis" memberi poin ke tiga bidang tech sekaligus.
2. **Normalisasi v1 tidak menolong.** "Bidang tertinggi = 100%" hanya mengubah skala, bukan urutan. Normalisasi dengan poin maksimum per bidang, diterapkan ke soal v1 apa adanya, sudah menurunkan selisih maks. dari 25% (28,7 pp menjadi 11,6 pp). Tetapi Akuntansi masih di luar pita dan top-1 persona Back-End tinggal 56,6%, jadi struktur soal tetap harus dirombak.
3. **Mobile tidak pernah bisa mengalahkan Back-End di v1** untuk jawaban apa pun (setiap opsi yang memberi poin Mobile memberi poin Back-End yang sama atau lebih besar).
4. **v2 menyelesaikannya lewat struktur simetris** (setiap bidang muncul tepat sekali per soal), normalisasi dengan poin maksimum, dan tie-break yang tidak memihak. Aturan maks. 2 bidang tech di top-3 menambah keragaman dengan biaya kecil (hit top-3 turun 0,05-0,15 pp untuk persona tech), tetapi itu keputusan nilai yang perlu disetujui tim.

Laporan lengkap dan rencana uji 10-20 mahasiswa: [`quiz/simulation/REPORT.md`](quiz/simulation/REPORT.md).

### AI Reviewer

1. **Skor identik dengan frontend.** `reviewer/src/score.py` dibandingkan dengan `client/src/lib/score.ts` asli yang dijalankan Node: 0 selisih di 565 kasus poin dan 606 kasus total. Replika naif dengan `round()` Python akan salah di kasus x,5 (misalnya 92,5).
2. **Urutan prompt diubah**: kriteria yang dinilai ditaruh paling akhir supaya submission bisa dibaca dari cache (AI-CONTEXT 6.2 menaruh rubrik sebelum submission).
3. **Biaya di AI-CONTEXT 12 terlalu rendah**: tabelnya dihitung sebagai satu panggilan. Dengan 5 kriteria + feedback dan cache: 1,5-1,8x (output hemat) sampai 1,9-3,3x (output dengan thinking), dengan syarat panggilan feedback tidak menyertakan submission utuh. Bila menyertakan submission: 2,3-3,9x. Lihat [`reviewer/cost/REPORT.md`](reviewer/cost/REPORT.md).
4. **Batas structured output**: `maxItems` dan `maxLength` tidak didukung provider, jadi evidence 1-3 dan reason sekitar 60 kata ditegakkan validator lokal.
5. **Injection**: 6 jenis serangan (README, teks tersembunyi, komentar kode, nama berkas yang menutup `</submission>`, tag yang disamarkan zero-width, catatan peserta) dinetralkan di builder dan diberi flag. Ketahanan model sendiri belum diuji.

## Test vector lintas bahasa

`quiz/test_vectors/vectors.json` berisi 45 kasus (seri, aturan klaster, Q4, Q8, jawaban ideal tiap bidang, jawaban acak, dan 4 input tidak valid). Implementasi kuis di TypeScript (frontend) atau Go (backend) harus menjalankan setiap kasus dan menghasilkan objek `expected` yang **identik**, termasuk urutan saran, persen, teks alasan, dan `tieLike`, atau menolak kasus `expectedError` di soal yang sama. Ini satu-satunya cara memastikan semua implementasi memberi saran yang sama untuk jawaban yang sama. Perbandingan skor memakai pecahan eksak dan pembulatan bilangan bulat supaya tidak ada selisih float. Bila `quiz.v2.json` berubah, tes `test_vectors_match_current_config_file` gagal sampai vector dibuat ulang dan versi dinaikkan.

## Sumber setiap angka

| Angka | Sumber |
| --- | --- |
| Poin maksimum, dominasi Mobile <= Back-End | Dihitung dari `quiz/config/*.json` oleh `quiz/src/analyze.py`; dicek di `quiz/tests/test_scoring.py` |
| Semua angka simulasi kuis | `quiz/simulation/results/summary.json` (seed tetap) |
| Kecocokan skor | `reviewer/tests/fixtures/score_ts_reference.json`, hasil Node v24.21.0 menjalankan `client/src/lib/score.ts` |
| Harga, pengali cache, tier Haiku | https://platform.claude.com/docs/en/about-claude/pricing, dibuka 2026-10-09 (`reviewer/cost/pricing.json`) |
| ID model, default effort | https://platform.claude.com/docs/en/about-claude/models/overview.md, dibuka 2026-10-09 |
| Parameter structured output dan batas skema | https://platform.claude.com/docs/en/build-with-claude/structured-outputs, dibuka 2026-10-09 |
| `cache_control`, maks. 4 breakpoint, minimum 512 token, cache tersedia setelah respons pertama mulai | https://platform.claude.com/docs/en/build-with-claude/prompt-caching, dibuka 2026-10-09 |
| Biaya per penilaian dan bulanan | `reviewer/cost/cost_model.py`, dengan asumsi token yang tertulis di `reviewer/cost/REPORT.md` (bukan pengukuran) |
| Target evaluasi | AI-CONTEXT 10.2; ambang "selisih QWK <= 0,10" adalah usulan |
| Pita 15-35% dan target persona 90%/60% | Pilihan penulis, alasannya di `quiz/simulation/REPORT.md` |

## Asumsi kerja

- Folder `client/` tidak ada di folder kerja. Kontrak frontend dibaca dari `Simula-main.zip` di folder Downloads (diekstrak ke folder sementara, hanya dibaca).
- `fieldKey` mengikuti `client/src/constants/fields.ts` (`backend`, `uiux`, `supply-chain`, ...), bukan `back_end`, `front_end`, ... seperti di prompt kerja.
- Contoh rubrik API memakai 4 kriteria dan bobot dari data tiruan client (sama dengan AI-CONTEXT 6.4), agar cocok dengan UI.

## Yang belum dikerjakan

- Panggilan Claude API sungguhan, golden set, dan angka kualitas model (butuh API key dan label manusia).
- Paket `anthropic` belum dipasang; `AnthropicClient` diuji dengan SDK palsu (bentuk parameter dan parsing respons), bukan terhadap API.
- Pipeline input: ekstraktor PDF/DOCX/XLSX, aturan zip, penghitung token resmi, dan blok PDF visual untuk slot desain (desain ada di `docs/ai-system-design.md` bagian 7).
- Service HTTP, antrean, dan endpoint internal (desain di `docs/ai-system-design.md` bagian 3).
- Pertanyaan teks bebas berbasis LLM di kuis (P1, sengaja tidak dibangun).
