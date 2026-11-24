# Eksperimen prompt reviewer-v1.1 (24 November 2026): TIDAK dipakai

Tujuan: menstabilkan pemilihan level dan mencegah feedback menulis solusi jadi. Isi perubahan ada di `reviewer-v1.1.patch`.

Uji: case web `optimasi-api-endpoint-produk`, satu submission buatan (`claude_live_test.go` di repo web), Claude Haiku 5.5, effort `low`. "Harapan" ditetapkan Claude dari teks rubrik sebelum uji, **bukan label manusia**.

| Kriteria | Harapan | v1 (2 run) | v1.1 (3 run) |
| --- | ---: | --- | --- |
| Ketepatan analisis masalah | 3 | 3, 3 | 3, 3, 3 |
| Efektivitas perbaikan | 3 | 3, 3 | 4, 3, 4 |
| Kualitas kode | 4 | 3, 4 | 3, 3, 4 |
| Kejelasan dokumentasi | 4 | 4, 4 | 4, 4, 4 |
| Skor total | 67 | 63, 67 | 70, 63, 74 |
| Selisih skor antar-run (target <= 5) | | 4 | 11 |
| Feedback menyebut teknik di luar brief | | 2 dari 2 | 2 dari 3 |

Kesimpulan: v1.1 tidak memperbaiki stabilitas dan masih menyebut `LIMIT/OFFSET`. Jumlah run terlalu kecil untuk menyimpulkan v1.1 lebih buruk, tetapi tidak ada alasan memakainya.

Dugaan penyebab (belum diuji): deskripsi level di rubrik ambigu. Contoh: "Efektivitas perbaikan" tidak punya level untuk dua dari tiga penyebab yang diperbaiki, dan "Kualitas kode" level 3 dan 4 hanya dibedakan oleh "cukup rapi" dan "rapi".