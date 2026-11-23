# Panduan menulis rubrik AI Case Study

Panduan ini untuk admin yang menyusun rubrik di panel admin (`/admin/cases`). Rubrik yang baik adalah faktor terbesar untuk konsistensi penilaian, baik oleh AI maupun manusia (AI-CONTEXT 4 dan 9). Format berkasnya didefinisikan di `rubric.schema.json`. Contoh terisi penuh ada di `examples/`.

Sebelum AI case terbit, jalankan validator:

```bash
python -m reviewer.src.rubric reviewer/rubric/examples/optimasi-api-endpoint-produk.rubric.json
```

## 1. Mulai dari lima dimensi, lalu sesuaikan

Kerangka umum di CONTEXT.md 4.11 adalah titik awal, bukan daftar wajib:

| Dimensi (`dimension`) | Yang dinilai |
| --- | --- |
| `pemahaman_masalah` | Akar masalah dan konteks bisnis dipahami dengan benar |
| `kualitas_solusi` | Solusi tepat, layak, dan menjawab masalah |
| `penalaran_keputusan` | Pilihan dijelaskan alasannya, alternatif dan risiko dipertimbangkan |
| `eksekusi` | Ketelitian dan kualitas hasil kerja (kode, analisis, desain, angka) |
| `komunikasi` | Deliverable jelas, terstruktur, mudah dipahami pemangku kepentingan |

Ubah nama dimensi menjadi nama kriteria yang spesifik untuk case ("Ketepatan analisis masalah", bukan "Pemahaman masalah"). Boleh menggabungkan dua dimensi dalam satu kriteria bila di case itu keduanya tidak bisa dipisahkan, tetapi tuliskan di `description`.

## 2. Aturan kriteria

1. **3 sampai 5 kriteria.** Lebih dari 5 membuat setiap kriteria terlalu tipis dan menambah satu panggilan LLM per kriteria (biaya dan waktu tunggu). Skema menerima 2-6 sebagai batas keras.
2. **Total bobot tepat 100**, bilangan bulat, setiap bobot 5-60. Bobot terbesar untuk hal yang paling membedakan hasil kerja baik dan buruk di case itu.
3. **Tidak tumpang tindih.** Satu kesalahan di submission seharusnya menurunkan satu kriteria saja. Tulis `out_of_scope` untuk menegaskan batasnya, misalnya kriteria "Kualitas kode" menulis "Ketepatan diagnosis tidak dinilai di sini".
4. **Setiap tugas di brief tercakup.** Bila brief meminta peserta menentukan metrik keberhasilan, harus ada kriteria yang menilainya. Tugas yang tidak dinilai membuat peserta bingung dan AI tidak punya patokan.
5. **`evidence_slots` diisi.** Tuliskan slot mana yang menjadi sumber bukti, supaya AI dan penilai manusia tahu harus melihat ke mana.
6. **Nama kriteria final sebelum terbit.** `name` disalin apa adanya ke hasil (`ICriterionScore.name`) dan ditampilkan ke peserta.

## 3. Deskripsi level 1-5: spesifik per kriteria

Deskripsi umum seperti "Baik: tepat dan rapi" (`client/src/constants/review.ts`) tidak boleh dipakai di AI case. Validator menolak deskripsi yang sama dengan template umum atau yang kembar antar level.

Setiap level harus menjawab: **apa yang terlihat di submission pada level ini?**

| Hindari | Tulis seperti ini |
| --- | --- |
| "Analisis baik" | "Akar masalah (query tanpa indeks) disebut dan dibuktikan dengan satu pengukuran, misalnya waktu respons sebelum dan sesudah" |
| "Kurang lengkap" | "Hanya menyebut gejala ('API lambat') tanpa menunjuk bagian kode atau query penyebabnya" |
| "Sangat kreatif" | "Setidaknya 3 ide konten memanfaatkan momen spesifik audiens (misalnya jam makan siang pekerja kantor) dan bukan template umum" |

Pola yang membantu:

- **Level 1**: bagian itu tidak ada, kosong, atau tidak menjawab tugas.
- **Level 2**: ada, tetapi inti tugas belum terjawab atau ada kekeliruan besar. Sebutkan kekeliruan tipikalnya.
- **Level 3**: inti tugas terjawab, dengan kekurangan yang jelas. Sebutkan kekurangan tipikalnya. Level 3 harus cukup untuk mendekati ambang lulus.
- **Level 4**: tepat dan didukung bukti, dengan sedikit kekurangan.
- **Level 5**: level 4 ditambah sesuatu yang bisa diamati, misalnya mempertimbangkan risiko atau skala. **Jangan** "melampaui harapan" tanpa penjelasan.

Setiap level berbeda dari level di bawahnya dalam **satu atau dua hal yang bisa dicek**, bukan dalam kata sifat.

## 4. Menulis bukti yang bisa diamati (`look_for`)

Bukti yang baik bisa ditunjuk: path berkas, nama fungsi, angka di tabel, halaman PDF, kalimat di isian teks.

- Baik: "Ada pengukuran waktu respons sebelum dan sesudah perubahan (angka dan cara mengukur)."
- Baik: "Setiap baris kalender punya pilar konten, format, dan tujuan."
- Buruk: "Peserta paham konsep indeks." (tidak bisa diamati langsung)
- Buruk: "Tulisan rapi." (subjektif dan bukan bukti)

**Panjang tulisan bukan ukuran kualitas.** Jangan menulis level seperti "penjelasan panjang dan detail". Tulis apa yang harus ada di dalam penjelasan.

## 5. Ambang lulus

Default 60 untuk AI case. Dengan rumus skor `level / 5 x bobot`, submission dengan level 3 di semua kriteria mendapat 60. Artinya **level 3 di semua kriteria = tepat lulus**. Tulis deskripsi level 3 dengan sadar: apakah submission seperti itu memang layak lulus? Bila tidak, naikkan ambang atau perketat level 3. Tinjau ulang setelah distribusi skor golden set diketahui (AI-CONTEXT 10.4).

## 6. Sebelum terbit

- [ ] Validator lolos tanpa error.
- [ ] Dua orang tim menilai 2-3 contoh submission (baik, sedang, buruk) dengan rubrik ini secara terpisah, lalu membandingkan level. Bila berbeda lebih dari 1 level di satu kriteria, perjelas deskripsinya.
- [ ] Case masuk golden set sebelum dipakai peserta sungguhan (`ml/docs/evaluation-plan.md`).
- [ ] `rubric_version` dinaikkan setiap ada perubahan isi. Perubahan rubrik mewajibkan evaluasi ulang (AI-CONTEXT 10.3).
