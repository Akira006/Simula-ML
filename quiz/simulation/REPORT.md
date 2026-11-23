# Laporan simulasi bias kuis minat: v1 (draf) vs v2

> **Peringatan utama.** Semua jawaban di laporan ini **sintetis**: jawaban acak seragam dan persona buatan. Simulasi ini hanya memeriksa **bias struktural**, yaitu apakah susunan opsi dan bobot menguntungkan bidang tertentu. Simulasi ini **tidak membuktikan** bahwa kuis cocok untuk mahasiswa sungguhan, bahwa soalnya dipahami dengan benar, atau bahwa saran bidangnya tepat. Bukti itu hanya bisa datang dari uji ke mahasiswa (bagian 7).

Cara mereproduksi (dari folder `ml/`):

```bash
python -m quiz.src.analyze
```

```bash
python -m quiz.simulation.run
```

Angka lengkap: `results/summary.json`, `results/tables.md`, `results/a1_structure.md`. Seed 20261009, sehingga hasil bisa diulang persis. Mesin simulasi (numpy) diuji identik dengan implementasi referensi di `tests/test_simulation_engine.py`.

## 1. Verifikasi dugaan awal (A1)

Dihitung langsung dari `config/quiz.v1.json`, yang mereproduksi draf AI-CONTEXT 14.4 apa adanya.

| Bidang | Poin maks. Q1-Q6 (v1) | Opsi yang memberi poin | Poin harapan bila acak | Poin maks. v2 |
| --- | ---: | ---: | ---: | ---: |
| Data | 12 | 7 | 3,05 | 8 |
| Marketing | 11 | 7 | 2,85 | 8 |
| Back-End | 10 | 7 | 2,41 | 8 |
| UI/UX Design | 10 | 6 | 2,05 | 8 |
| Akuntansi | 10 | 8 | 2,91 | 8 |
| Keuangan | 8 | 5 | 1,65 | 8 |
| Front-End | 7 | 7 | 1,74 | 8 |
| Mobile | 6 | 5 | 1,38 | 8 |
| Supply Chain | 6 | 4 | 1,07 | 8 |
| Product | 5 | 5 | 1,13 | 8 |
| Human Resources | 5 | 4 | 0,85 | 8 |
| Legal | 5 | 3 | 0,89 | 8 |

**Kesimpulan A1:**

1. **Dugaan poin maksimum terbukti, angkanya tepat sama** dengan yang ditulis di prompt (Data 12 sampai Legal 5). Selisih tertinggi dan terendah 7 poin. Dicek di `test_v1_max_points_match_reported_draft`.
2. **Dugaan "tiga bidang tech sekaligus" terbukti, dan lebih luas.** Ada empat opsi yang memberi poin ke Back-End, Front-End, dan Mobile bersamaan (Q1 "bagian teknis atau kode", Q2 "aplikasi yang berjalan lancar", Q4 "code editor atau GitHub", Q5 "membuat aplikasi kecil"). Akibatnya, top-3 persona Back-End berisi tiga bidang tech pada 84,2% kasus, dan persona Mobile 92,1%.
3. **Temuan tambahan: normalisasi v1 tidak menghilangkan bias apa pun.** AI-CONTEXT 14.4 menulis normalisasi "bidang tertinggi = 100%" dipakai "supaya perbedaan jumlah pilihan per bidang tidak bias". Membagi semua bidang dengan bilangan yang sama hanya mengubah skala, sehingga urutan top-3 identik dengan poin mentah. Klaim di dokumen itu keliru.
4. **Temuan tambahan: Mobile tidak pernah bisa mengalahkan Back-End di v1.** Setiap opsi yang memberi poin ke Mobile memberi poin yang sama atau lebih besar ke Back-End, termasuk pemetaan jurusan. Jadi untuk jawaban apa pun, poin Mobile <= poin Back-End. Dengan tie-break urutan bidang, persona Mobile mendapat top-1 **0,0%**. Dicek di `test_v1_structural_problems` (fungsi `dominated_pairs`).
5. **Normalisasi dengan poin maksimum per bidang memperbaiki sebagian besar bias, tetapi tidak semuanya.** Varian "v1 struktur draf + normalisasi poin maks." (soal v1 tidak diubah, tie-break acak) menurunkan selisih maks. dari 25% dari 28,7 pp menjadi 11,6 pp. Namun Akuntansi masih di luar pita (36,6%), top-1 persona Back-End turun ke 56,6% (di bawah target 60%), dan 6,8% responden acak masih mendapat top-3 yang semuanya tech. Penyebab sisanya: rasio "poin harapan / poin maks." masih timpang (tertinggi Akuntansi 0,291, terendah Human Resources 0,170). Karena itu v2 merombak struktur soal. Di v2 poin maksimum semua bidang sama, sehingga normalisasi tidak lagi mengubah urutan dan hanya berfungsi sebagai jaring pengaman bila bobot diubah, serta membuat angka persen bermakna.

## 2. Jawaban acak seragam

**Model jawaban:** setiap soal pilihan tunggal dijawab acak seragam; setiap tools di Q4 dicentang dengan peluang 1/2 (bila tidak ada yang tercentang, "Belum ada"); Q8 kosong. N = 20.000 per varian.

**Pita toleransi 15-35%** untuk tingkat masuk top-3 adalah pilihan saya: plus-minus 10 poin persen dari nilai seimbang 25% (3 dari 12). Dengan N = 20.000, galat sampling sekitar plus-minus 0,6 poin persen, jadi bidang di luar pita menandakan masalah struktural, bukan kebetulan.

| Bidang | v1 top-3 | v1 top-1 | v1 tie acak top-3 | v2 top-3 | v2 top-1 | v2 top-3 CI 95% |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Back-End | 48,7% ⚠ | 18,1% | 38,7% | 24,0% | 8,5% | 23,4-24,6% |
| Front-End | 24,9% | 2,9% | 18,7% | 24,7% | 8,4% | 24,1-25,3% |
| Mobile | 9,4% ⚠ | 0,0% | 8,0% | 24,6% | 7,8% | 24,0-25,2% |
| Data | 53,7% ⚠ | 26,6% | 50,5% | 25,1% | 8,5% | 24,5-25,7% |
| UI/UX Design | 31,0% | 10,7% | 30,3% | 25,0% | 8,1% | 24,4-25,6% |
| Product | 11,1% ⚠ | 1,1% | 11,3% | 24,8% | 8,3% | 24,2-25,4% |
| Marketing | 45,4% ⚠ | 19,0% | 48,0% | 25,1% | 8,4% | 24,6-25,8% |
| Keuangan | 16,4% | 3,1% | 19,9% | 25,5% | 8,5% | 24,9-26,1% |
| Akuntansi | 43,0% ⚠ | 16,1% | 49,1% | 25,2% | 8,0% | 24,6-25,8% |
| Human Resources | 3,6% ⚠ | 0,3% | 5,8% | 25,2% | 8,6% | 24,6-25,8% |
| Supply Chain | 7,8% ⚠ | 1,6% | 11,5% | 24,9% | 8,3% | 24,3-25,5% |
| Legal | 4,9% ⚠ | 0,5% | 8,3% | 25,7% | 8,7% | 25,1-26,3% |

⚠ = di luar pita 15-35%. "v2" = konfigurasi final (aturan klaster aktif).

| Varian | Bidang di luar pita | Selisih maks. dari 25% | Top-3 semuanya tech | Top-1 seri persis |
| --- | --- | ---: | ---: | ---: |
| v1 draf, tie-break urutan bidang | 9 dari 12 | 28,7 pp | 6,2% | 26,9% |
| v1 draf, tie-break acak | 9 dari 12 | 25,5 pp | 4,3% | 26,9% |
| v1 struktur draf + normalisasi poin maks., tie-break acak | 1 dari 12 (Akuntansi 36,6%) | 11,6 pp | 6,8% | 14,6% |
| v2 (a) tanpa aturan klaster | tidak ada | 0,7 pp | 1,2% | 35,4% |
| v2 (a) dengan tie-break urutan bidang | tidak ada | 9,1 pp | 3,2% | 35,4% |
| **v2 final (b), aturan klaster** | **tidak ada** | **1,0 pp** | **0,1%** | 35,4% |

pp = poin persen. Pembanding "top-3 semuanya tech" bila top-3 diambil acak dari 12 bidang: 1/220 = 0,45%.

**Kesimpulan:** di v1, 9 dari 12 bidang di luar pita. Data masuk top-3 pada 53,7% responden acak, Human Resources hanya 3,6% (rasio hampir 15 kali). Di v2 semua bidang berada di 24,0-25,7%, dan tidak ada yang keluar dari pita. Normalisasi saja sudah memperbaiki sebagian besar ketimpangan v1 (28,7 pp menjadi 11,6 pp), dan perombakan struktur di v2 menghilangkan sisanya. Tie-break juga penting: karena poin berupa bilangan bulat, top-1 seri persis pada 35% responden acak. Dengan struktur v2 yang sama, mengganti tie-break rotasi dengan tie-break "urutan bidang" menaikkan tingkat masuk top-3 Back-End dari 24,3% ke 34,1% (+9,8 pp).

## 3. Persona sintetis

**Model persona:** di setiap soal pilihan tunggal, persona memilih opsi dengan bobot tertinggi untuk bidangnya dengan peluang 80% (bila tidak ada opsi untuk bidangnya di soal itu, memilih acak), dan memilih acak dengan peluang 20% (`eps` = 0,2). Di Q4, tools bidangnya dicentang dengan peluang 80%, tools lain 15%. N = 2.000 per bidang.

**Target:** masuk top-3 >= 90% dan top-1 >= 60%, sesuai usulan awal. Saya tidak mengubahnya: target ini longgar untuk persona yang 80% konsisten, dan v2 melampauinya dengan jarak lebar, sehingga menaikkan target tidak akan mengubah keputusan.

| Persona | v1 top-1 | v1 top-3 | v2 top-1 | v2 top-3 | v2 + jurusan yang cocok, top-1 | v2 seri persis | v2 selisih <= 1 poin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Back-End | 98,8% | 100,0% | 95,9% | 99,3% | 96,5% | 3,2% | 11,9% |
| Front-End | 71,9% | 99,8% | 95,5% | 99,1% | 97,0% | 3,4% | 10,8% |
| Mobile | **0,0%** ⚠ | 96,3% | 93,6% | 99,2% | 94,4% | 4,2% | 13,7% |
| Data | 99,6% | 100,0% | 96,0% | 99,2% | 97,2% | 2,6% | 9,4% |
| UI/UX Design | 98,4% | 99,9% | 95,8% | 99,5% | 97,6% | 2,4% | 10,1% |
| Product | 47,3% ⚠ | 94,2% | 95,5% | 99,2% | 97,8% | 3,4% | 10,2% |
| Marketing | 99,1% | 99,9% | 95,9% | 99,2% | 97,8% | 3,2% | 10,1% |
| Keuangan | 87,8% | 99,0% | 96,0% | 99,3% | 98,0% | 3,5% | 11,9% |
| Akuntansi | 90,3% | 99,9% | 95,6% | 99,6% | 97,5% | 3,6% | 11,1% |
| Human Resources | 63,8% | 89,3% ⚠ | 95,5% | 99,2% | 96,7% | 3,7% | 11,1% |
| Supply Chain | 81,5% | 96,2% | 96,0% | 99,7% | 97,5% | 2,9% | 10,2% |
| Legal | 40,8% ⚠ | 88,2% ⚠ | 95,7% | 99,6% | 98,2% | 3,5% | 10,2% |

⚠ = di bawah target. Di v1, empat persona gagal target (Mobile, Product, Human Resources, Legal). Di v2 tidak ada yang gagal; top-1 terendah 93,6% (Mobile).

**Ketahanan terhadap noise** (nilai terendah di antara 12 persona):

| eps | v1 min top-1 | v1 min top-3 | v2 min top-1 | v2 min top-3 |
| ---: | ---: | ---: | ---: | ---: |
| 0,1 | 0,0% | 94,8% | 98,8% | 99,9% |
| 0,2 | 0,0% | 87,9% | 94,5% | 99,2% |
| 0,3 | 0,0% | 80,2% | 87,4% | 96,9% |
| 0,4 | 0,0% | 68,7% | 78,0% | 92,7% |

Bahkan bila persona menjawab acak 40% dari waktu, v2 masih memenuhi kedua target untuk semua bidang. Baris eps 0,2 sedikit berbeda dari tabel persona di atas (misalnya 94,5% vs 93,6%) karena memakai seed lain (20261009 + 2000); selisih ini adalah variasi sampling, bukan perbedaan model.

## 4. Keputusan aturan keragaman top-3 (klaster)

Dua pendekatan dibandingkan dengan simulasi yang sama:

- **(a)** tanpa aturan klaster;
- **(b)** maksimal 2 bidang dari klaster `tech` (Back-End, Front-End, Mobile) di top-3, kecuali bidang tech ketiga unggul >= 2 poin dari kandidat non-tech berikutnya.

| Metrik | (a) | (b) |
| --- | ---: | ---: |
| Selisih maks. top-3 dari 25%, jawaban acak | 0,7 pp | 1,0 pp |
| Hit top-3 bidang target, persona (terendah) | 99,1% | 99,1% |
| Hit top-3 persona Back-End / Mobile | 99,35% / 99,30% | 99,30% / 99,15% |
| Persona Back-End dengan top-3 semuanya tech | 59,1% | 9,0% |
| Persona Front-End dengan top-3 semuanya tech | 2,4% | 0,1% |
| Persona Mobile dengan top-3 semuanya tech | 60,6% | 36,5% |

**Keputusan: (b), dengan trade-off yang perlu disetujui tim.**

- **Yang didapat:** "top-3 semuanya tech" turun tajam untuk persona Back-End (59,1% ke 9,0%) dan Mobile (60,6% ke 36,5%). Mahasiswa yang condong ke tech lebih sering melihat satu bidang di luar tech sebagai bahan eksplorasi.
- **Yang dikorbankan, kecil tetapi nyata:**
  - Hit top-3 bidang target turun sedikit untuk persona tech (Back-End -0,05 pp, Mobile -0,15 pp). Aturan ini bisa mendorong bidang target sendiri keluar dari posisi ketiga bila bidang itu adalah tech ketiga.
  - Keseimbangan jawaban acak sedikit memburuk (0,7 pp ke 1,0 pp), tetapi masih jauh di dalam pita.
  - Tiga saran tidak lagi selalu urut skor: bidang tech yang disisihkan bisa punya skor lebih tinggi daripada saran ketiga yang ditampilkan. Skornya tetap terlihat di `fieldScores`.
- **Ini keputusan nilai, bukan temuan data.** Simulasi tidak menunjukkan bahwa top-3 yang semuanya tech itu buruk bagi mahasiswa. Yang ditunjukkan hanya bahwa aturan ini menambah keragaman dengan biaya kecil. Bila tim lebih memilih urutan skor murni, ganti `diversity` di config ke `{"type": "none"}` (varian (a)), naikkan versi, dan buat ulang test vector.

Persona Mobile masih 36,5% karena bidang tech ketiganya sering unggul >= 2 poin, dan dalam kasus itu aturan sengaja tidak memaksa.

Catatan: hanya klaster `tech` yang beranggota 3 bidang. Bila tim menambah klaster lain (misalnya Keuangan + Akuntansi), aturannya otomatis berlaku, tetapi simulasi harus diulang.

## 5. Sensitivitas bobot (+/-1)

Setiap bobot yang ada (> 0) di soal pilihan tunggal dan Q4 diubah +1 dan -1, satu per satu: 144 perubahan untuk v2, 136 untuk v1. Setiap perubahan dinilai ulang dengan bilangan acak yang sama (20.000 responden acak dan 500 persona per bidang), tanpa aturan klaster, supaya yang terukur adalah efek bobot itu sendiri.

**v2:** baseline selisih maks. 1,0 pp; top-1 persona terendah 94,2%. Baseline ini berbeda dari bagian 2-3 (0,7 pp dan 93,6%) karena memakai sampel lain (seed + 7, 500 persona per bidang), yang dipakai bersama oleh semua perubahan supaya perbandingannya adil.

| Perubahan paling sensitif | Pergeseran top-3 terbesar | Bidang |
| --- | ---: | --- |
| `q6_a` Back-End 1 -> 0 | 6,6 pp | Back-End |
| `q2_b` Back-End 1 -> 0 | 6,3 pp | Back-End |
| `q5_a` Back-End 1 -> 0 | 6,3 pp | Back-End |
| `q2_c` Front-End 1 -> 0 | 6,2 pp | Front-End |
| `q6_c` Front-End 1 -> 0 | 6,1 pp | Front-End |

Pola v2: yang paling sensitif adalah **menghapus bobot pendamping (+1)**, karena itu merusak simetri (bidang tersebut kehilangan satu peluang poin). Pergeseran terbesar 6,6 pp, masih di dalam pita 15-35%. Top-1 persona terendah dari semua 144 perubahan tetap >= 94,2%. Artinya v2 tidak rapuh terhadap salah setel satu bobot, tetapi **setiap perubahan bobot harus menjaga simetri** (setiap bidang tetap utama 2 kali dan pendamping 2 kali). Tes `test_v2_is_structurally_symmetric` akan gagal bila simetri rusak.

**v1:** baseline selisih maks. 28,9 pp (28,7 pp di bagian 2; beda sampel, alasan sama seperti di atas). Bobot paling sensitif semuanya di **Q4**: misalnya `q4_code` Front-End 1 -> 2 menggeser 15,1 pp, dan `q4_acc` Akuntansi 2 -> 1 menggeser 11,9 pp. Penyebabnya Q4 multi-select tanpa batas. Tidak ada satu pun perubahan +/-1 yang membuat persona Mobile v1 lolos target top-1 (tetap 0-0,4%), karena masalahnya struktural, bukan satu bobot.

## 6. Keterbatasan

- **Model jawaban acak tidak mencerminkan populasi nyata.** Mahasiswa sungguhan tidak menjawab seragam. Contohnya, mahasiswa IT jauh lebih mungkin pernah memakai tools di Q4 daripada mahasiswa hukum. Distribusi saran di data nyata akan mengikuti komposisi pengguna, dan itu wajar.
- **Persona menganggap opsi "berbobot tertinggi untuk bidangnya" adalah yang dipilih orang di bidang itu.** Ini mengasumsikan teks opsi dipahami sesuai maksud penulis. Asumsi inilah yang paling perlu diuji ke mahasiswa.
- **Pasangan pendamping (+1) dipilih penulis**, dan beberapa terasa lemah (lihat `CHANGELOG-v2.md`). Simulasi tidak bisa menilai apakah pasangan itu masuk akal.
- Q7 (keyakinan) tidak memengaruhi skor, jadi tidak disimulasikan. Q8 hanya disimulasikan untuk persona dengan jurusan yang cocok.

## 7. Rencana uji ke 10-20 mahasiswa (AI-CONTEXT 16.3 no. 7)

**Tujuan:** mengecek hal yang tidak bisa dicek simulasi: apakah soal dipahami, apakah saran terasa masuk akal, dan apakah ada opsi yang membingungkan.

**Peserta:** 10-20 mahasiswa tingkat akhir atau fresh graduate, dengan sebaran bidang yang merata. Minimal satu orang per bidang, dan 3-5 orang yang **belum yakin** bidangnya (sasaran utama kuis). Hindari hanya merekrut teman tim atau satu jurusan.

**Prosedur (sekitar 20 menit per orang):**

1. Sebelum kuis, tanya bidang yang mereka minati (boleh "belum tahu") dan seberapa yakin (1-5).
2. Mereka mengerjakan kuis sambil berpikir keras (*think-aloud*). Catat soal yang membuat ragu dan berapa lama tiap soal.
3. Tunjukkan saran 3 bidang beserta alasannya.
4. Wawancara singkat dengan pertanyaan di bawah.
5. Simpan jawaban kuis mentah, bidang yang dinyatakan, dan saran yang keluar (tanpa nama) untuk dianalisis.

**Pertanyaan untuk peserta:**

1. Ada soal atau opsi yang membingungkan atau terasa tidak cocok dengan pengalamanmu? Yang mana?
2. Pernahkah kamu merasa terpaksa memilih opsi yang sebenarnya tidak menggambarkanmu? Di soal mana?
3. Apakah ada pilihan yang menurutmu hilang?
4. Di Q4 (tools), apakah contohnya kamu kenal? Ada tools yang kamu pakai tapi tidak ada di daftar?
5. Dari 3 saran bidang, mana yang terasa paling tepat dan mana yang paling meleset? Kenapa?
6. Apakah alasan yang ditampilkan ("Kamu sering ... dan ...") sesuai dengan jawabanmu?
7. Kalau hasilnya "X dan Y sama-sama cocok", apakah itu membantu atau membingungkan?
8. Setelah melihat saran, apakah kamu akan mempertahankan, mengubah, atau mengabaikannya? Kenapa?
9. Apakah ada kata atau nada yang terasa menghakimi atau membuatmu tidak nyaman?
10. Berapa lama rasanya kuis ini? Terlalu panjang di bagian mana?

**Yang diukur dan dicatat:**

- Persentase peserta yang bidang pilihannya sendiri (bila sudah punya) muncul di top-3 saran.
- Persentase yang mempertahankan setidaknya satu bidang saran (setara metrik "tingkat penerimaan saran" di AI-CONTEXT 14.8).
- Opsi yang disebut membingungkan oleh 2 orang atau lebih, untuk ditulis ulang.
- Waktu pengerjaan (target sekitar 2 menit, sesuai tautan "Ikuti kuis minat (2 menit)").

**Batasan uji:** 10-20 orang terlalu sedikit untuk menyimpulkan akurasi secara statistik. Hasilnya dipakai untuk memperbaiki redaksi dan menemukan opsi yang bermasalah, bukan untuk mengklaim bahwa kuis "terbukti akurat". Setiap perubahan bobot setelah uji harus menaikkan `version` dan menjalankan ulang simulasi ini.
