# Hasil model biaya AI Reviewer (dibuat otomatis)

Harga: https://platform.claude.com/docs/en/about-claude/pricing (diambil 2026-10-09). Per 1 juta token, USD.

| Model | Input | Cache write 5m | Cache read | Output |
| --- | ---: | ---: | ---: | ---: |
| Claude Haiku 5.5 (prompt <= 100,000) | $0.1 | $0.125 | $0.01 | $0.5 |
| Claude Haiku 5.5 (prompt > 100.000) | $0.5 | $0.625 | $0.05 | $2.5 |
| Claude Sonnet 5.5 | $2.0 | $2.5 | $0.1 | $10.0 |
| Claude Opus 5.5 | $4.0 | $5.0 | $0.2 | $20.0 |

## Asumsi

```json
{
  "criteria": 5,
  "criterion_block_tokens": 600,
  "feedback_input_tokens": 3000,
  "output_profiles": {
    "hemat": {
      "criterion": 300,
      "feedback": 400,
      "note": "JSON saja, thinking minimal. Total 1.900 token, dekat asumsi AI-CONTEXT (1.500)."
    },
    "dengan_thinking": {
      "criterion": 1200,
      "feedback": 1000,
      "note": "Thinking adaptif aktif di ketiga model dan ditagih sebagai output. Angka ini tebakan; ukur di golden set."
    }
  },
  "aicontext_output_tokens": 1500,
  "retry_rate": 0.0
}
```

## 1. Per penilaian

### Profil output: hemat

| Skenario | Model | AI-CONTEXT 12 (1 panggilan) | 6 panggilan tanpa cache | 6 panggilan dengan cache | Dengan cache / AI-CONTEXT | Tanpa cache / dengan cache |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Isian teks saja (10 rb) | Claude Haiku 5.5 | $0.0018 | $0.0066 | $0.0032 | 1.83x | 2.05x |
| Isian teks saja (10 rb) | Claude Sonnet 5.5 | $0.0350 | $0.1310 | $0.0600 | 1.71x | 2.18x |
| Isian teks saja (10 rb) | Claude Opus 5.5 | $0.0700 | $0.2620 | $0.1200 | 1.71x | 2.18x |
| Dokumen atau kode zip (40 rb) | Claude Haiku 5.5 | $0.0047 | $0.0215 | $0.0082 | 1.72x | 2.64x |
| Dokumen atau kode zip (40 rb) | Claude Sonnet 5.5 | $0.0950 | $0.4310 | $0.1470 | 1.55x | 2.93x |
| Dokumen atau kode zip (40 rb) | Claude Opus 5.5 | $0.1900 | $0.8620 | $0.2940 | 1.55x | 2.93x |
| Mendekati batas 5.5 (60 rb) | Claude Haiku 5.5 | $0.0067 | $0.0316 | $0.0115 | 1.70x | 2.76x |
| Mendekati batas 5.5 (60 rb) | Claude Sonnet 5.5 | $0.1350 | $0.6310 | $0.2050 | 1.52x | 3.08x |
| Mendekati batas 5.5 (60 rb) | Claude Opus 5.5 | $0.2700 | $1.26 | $0.4100 | 1.52x | 3.08x |

### Profil output: dengan_thinking

| Skenario | Model | AI-CONTEXT 12 (1 panggilan) | 6 panggilan tanpa cache | 6 panggilan dengan cache | Dengan cache / AI-CONTEXT | Tanpa cache / dengan cache |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Isian teks saja (10 rb) | Claude Haiku 5.5 | $0.0018 | $0.0091 | $0.0058 | 3.29x | 1.58x |
| Isian teks saja (10 rb) | Claude Sonnet 5.5 | $0.0350 | $0.1820 | $0.1110 | 3.17x | 1.64x |
| Isian teks saja (10 rb) | Claude Opus 5.5 | $0.0700 | $0.3640 | $0.2220 | 3.17x | 1.64x |
| Dokumen atau kode zip (40 rb) | Claude Haiku 5.5 | $0.0047 | $0.0241 | $0.0107 | 2.25x | 2.25x |
| Dokumen atau kode zip (40 rb) | Claude Sonnet 5.5 | $0.0950 | $0.4820 | $0.1980 | 2.08x | 2.43x |
| Dokumen atau kode zip (40 rb) | Claude Opus 5.5 | $0.1900 | $0.9640 | $0.3960 | 2.08x | 2.43x |
| Mendekati batas 5.5 (60 rb) | Claude Haiku 5.5 | $0.0067 | $0.0341 | $0.0140 | 2.07x | 2.44x |
| Mendekati batas 5.5 (60 rb) | Claude Sonnet 5.5 | $0.1350 | $0.6820 | $0.2560 | 1.90x | 2.66x |
| Mendekati batas 5.5 (60 rb) | Claude Opus 5.5 | $0.2700 | $1.36 | $0.5120 | 1.90x | 2.66x |

## 2. Rincian satu penilaian (dengan cache, profil hemat, 60 ribu token)

| Model | Panggilan 1 (tulis cache) | Panggilan 2-5 (baca cache) | Feedback | Total |
| --- | ---: | ---: | ---: | ---: |
| Claude Haiku 5.5 | $0.0077 | $0.0032 | $0.0005 | $0.0115 |
| Claude Sonnet 5.5 | $0.1542 | $0.0408 | $0.0100 | $0.2050 |
| Claude Opus 5.5 | $0.3084 | $0.0816 | $0.0200 | $0.4100 |

## 3. Bulanan (dengan cache)

### Profil output: hemat

| Skenario | Model | 1.000 penilaian | 10.000 penilaian | Rumus AI-CONTEXT 12 per skenario, tanpa retry (1.000 / 10.000) |
| --- | --- | ---: | ---: | --- |
| Isian teks saja | Claude Haiku 5.5 | $3.20 | $32.00 | $1.75 / $17.50 |
| Isian teks saja | Claude Sonnet 5.5 | $60.00 | $600 | $35.00 / $350 |
| Isian teks saja | Claude Opus 5.5 | $120 | $1,200 | $70.00 / $700 |
| Dokumen atau kode zip | Claude Haiku 5.5 | $8.15 | $81.50 | $4.75 / $47.50 |
| Dokumen atau kode zip | Claude Sonnet 5.5 | $147 | $1,470 | $95.00 / $950 |
| Dokumen atau kode zip | Claude Opus 5.5 | $294 | $2,940 | $190 / $1,900 |
| Mendekati batas 5.5 | Claude Haiku 5.5 | $11.45 | $114 | $6.75 / $67.50 |
| Mendekati batas 5.5 | Claude Sonnet 5.5 | $205 | $2,050 | $135 / $1,350 |
| Mendekati batas 5.5 | Claude Opus 5.5 | $410 | $4,100 | $270 / $2,700 |

### Profil output: dengan_thinking

| Skenario | Model | 1.000 penilaian | 10.000 penilaian | Rumus AI-CONTEXT 12 per skenario, tanpa retry (1.000 / 10.000) |
| --- | --- | ---: | ---: | --- |
| Isian teks saja | Claude Haiku 5.5 | $5.75 | $57.50 | $1.75 / $17.50 |
| Isian teks saja | Claude Sonnet 5.5 | $111 | $1,110 | $35.00 / $350 |
| Isian teks saja | Claude Opus 5.5 | $222 | $2,220 | $70.00 / $700 |
| Dokumen atau kode zip | Claude Haiku 5.5 | $10.70 | $107 | $4.75 / $47.50 |
| Dokumen atau kode zip | Claude Sonnet 5.5 | $198 | $1,980 | $95.00 / $950 |
| Dokumen atau kode zip | Claude Opus 5.5 | $396 | $3,960 | $190 / $1,900 |
| Mendekati batas 5.5 | Claude Haiku 5.5 | $14.00 | $140 | $6.75 / $67.50 |
| Mendekati batas 5.5 | Claude Sonnet 5.5 | $256 | $2,560 | $135 / $1,350 |
| Mendekati batas 5.5 | Claude Opus 5.5 | $512 | $5,120 | $270 / $2,700 |

