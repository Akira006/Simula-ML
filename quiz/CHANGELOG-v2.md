# Perubahan kuis minat: draf v1 (AI-CONTEXT 14.4) ke v2

Sumber kebenaran: `config/quiz.v2.json`. Angka di bawah dihitung oleh `python -m quiz.src.analyze` dan `python -m quiz.simulation.run`, bukan ditulis tangan.

## Perubahan struktur

| # | Perubahan | Alasan |
| --- | --- | --- |
| 1 | `fieldKey` memakai kunci yang sudah dipakai frontend: `backend, frontend, mobile, data, uiux, product, marketing, finance, accounting, hr, supply-chain, legal` | Kunci di prompt kerja (`back_end`, `front_end`, ...) tidak sama dengan `client/src/constants/fields.ts`. Kontrak frontend tidak boleh berubah. Diuji di `test_field_keys_match_client`. |
| 2 | Q1, Q2, Q3, Q5 masing-masing punya **6 opsi**. Setiap opsi memberi **+2 ke satu bidang utama dan +1 ke satu bidang pendamping**, dan **setiap bidang muncul tepat sekali per soal** | Di v1 jumlah peluang poin per bidang sangat timpang (Data maks. 12, Legal maks. 5). Dengan pola ini setiap bidang punya peluang yang sama di setiap soal. |
| 3 | Di keempat soal itu, setiap bidang menjadi **utama tepat 2 kali dan pendamping tepat 2 kali** | Menyamakan poin maksimum (6 dari empat soal ini) dan sebaran poin semua bidang. |
| 4 | Pasangan utama-pendamping dibuat bervariasi. Hanya 3 pasangan yang muncul dua kali di Q1-Q6 (Akuntansi-Keuangan, Back-End-Mobile, Front-End-Mobile) | Bila dua bidang selalu muncul bersama, kuis tidak bisa membedakannya. |
| 5 | Opsi "Mengerjakan bagian teknis atau kode" (+2 ke Back-End, Front-End, dan Mobile sekaligus) dihapus. Diganti opsi terpisah: logika program dan database (Back-End), tampilan web atau aplikasi (Front-End), aplikasi HP (Mobile) | Opsi itu membuat top-3 mudah berisi tiga bidang tech. Di v1, 84-92% persona Back-End dan Mobile mendapat top-3 yang semuanya tech. |
| 6 | Q6 diubah dari penilaian diri ("Mana yang paling menggambarkan cara kerjamu?") menjadi aktivitas: "Pekerjaan seperti apa yang bikin kamu lupa waktu?". 6 opsi, masing-masing +1 ke dua bidang, semua bidang tepat sekali | Sesuai prinsip 14.4: skenario dan aktivitas, bukan penilaian diri. Q6 v1 tidak punya opsi untuk Mobile dan Keuangan. |
| 7 | Q4 (tools): **satu opsi per bidang**, +1 per opsi, **batas 1 poin per bidang** (`per_field_cap`) | Di v1 Q4 tanpa batas dan condong ke tech, data, dan akuntansi (Data bisa +3 dari Q4 saja, HR/Legal/Supply Chain/Product 0). Dengan v2, mencentang semua opsi memberi +1 ke semua bidang, jadi tidak ada bidang yang menang otomatis. Diuji di `test_q4_check_all_is_neutral`. |
| 8 | Opsi Q4 untuk HR, Supply Chain, dan Legal ditambahkan dengan contoh yang dekat dengan pengalaman mahasiswa (misalnya menyeleksi pendaftar open recruitment kepanitiaan) | Bidang non-tech tidak punya opsi sama sekali di Q4 v1. "LinkedIn" sengaja tidak dipakai untuk HR karena hampir semua mahasiswa memakainya sebagai pencari kerja. |
| 9 | Q8 (jurusan) dipetakan ke 11 kelompok jurusan dengan kata kunci; poin dibatasi +1 per bidang walau cocok dengan beberapa entri. Bila jurusan kosong atau tidak dikenali, Q8 tidak ikut dihitung di pembilang maupun penyebut | Onboarding menyimpan jurusan sebagai teks bebas (`major`, maks. 100 karakter). Setiap bidang bisa mendapat +1 dari minimal satu jurusan, jadi poin maks. tetap sama (9) untuk semua bidang. |
| 10 | Kata kunci "komunikasi" polos diganti "komunikasi massa" | "Desain Komunikasi Visual" sempat ikut cocok dengan entri Ilmu Komunikasi (+1 HR). Diuji di `test_dkv_does_not_match_communication_major`. |

## Perubahan aturan skoring

| # | Perubahan | Alasan |
| --- | --- | --- |
| 11 | Normalisasi: `poin bidang / poin maksimum yang dapat dicapai bidang itu`, bukan `poin / poin tertinggi pengguna` | Normalisasi v1 hanya mengubah skala dan **tidak mengubah urutan sama sekali**, jadi tidak mengurangi bias. Diterapkan ke struktur v1, normalisasi poin maks. sudah menurunkan selisih maks. dari 28,7 ke 11,6 pp, tetapi tidak cukup (lihat `simulation/REPORT.md` bagian 1 butir 5). Di v2 poin maks. semua bidang sama, jadi normalisasi ini tidak mengubah urutan; fungsinya jaring pengaman bila bobot diubah dan membuat persen bermakna. |
| 12 | Tie-break berjenjang: (1) jumlah jawaban +2 untuk bidang itu, (2) rotasi berdasarkan jawaban, (3) urutan bidang | Dengan poin bilangan bulat, top-1 seri persis di 35% responden acak. Dengan struktur v2, tie-break urutan bidang saja menaikkan tingkat masuk top-3 Back-End dari 24,3% ke 34,1% (+9,8 pp). Rotasi berbasis jawaban tetap deterministik tetapi tidak memihak: selisih maks. dari 25% 0,7-1,0 pp. |
| 13 | `tieLike: true` dan `tiedFieldKeys` bila skor bidang teratas sama persis (`tie_margin_points: 0`) | Persona sintetis seri 2,4-4,2%, dan selisih 1 poin terjadi pada 9-14%. Margin 1 poin akan terlalu sering menampilkan "sama-sama cocok" untuk jawaban yang sebenarnya jelas. |
| 14 | Aturan klaster: maksimal 2 bidang dari klaster `tech` (Back-End, Front-End, Mobile) di top-3, kecuali bidang ketiga unggul >= 2 poin dari kandidat non-tech berikutnya | Menurunkan "top-3 semuanya tech" pada persona Back-End dari 59,1% ke 9,0% dan pada persona Mobile dari 60,6% ke 36,5%. Biayanya kecil: hit top-3 bidang target turun 0,05 pp (Back-End) dan 0,15 pp (Mobile), dan tiga saran tidak selalu urut skor. Menganggap top-3 semuanya tech kurang baik adalah keputusan nilai yang perlu disetujui tim (`simulation/REPORT.md` bagian 4). |
| 15 | Hanya bidang dengan poin > 0 yang boleh muncul sebagai saran | Menghindari saran "0% cocok". |
| 16 | Persen dibulatkan setengah ke atas dengan aritmetika bilangan bulat; perbandingan skor memakai pecahan eksak | Agar implementasi TS/Go menghasilkan angka identik (lihat `test_vectors/`). |

## Perubahan teks

Semua soal dan opsi ditulis ulang agar berbasis skenario atau aktivitas, memakai "kamu", dan tidak menyebut tes psikologi, kepribadian, atau bakat (diuji di `test_no_psychological_test_terms`). Beberapa pasangan pendamping (+1) masih terasa lemah secara makna dan perlu diuji ke mahasiswa:

- Q1 "Memeriksa aturan tugas dan menjaga kesepakatan kelompok": Legal +2, HR +1.
- Q3 "Promosi, media sosial, dan cara admin melayani chat pembeli": Marketing +2, HR +1.
- Q5 "Mempelajari cara perusahaan merekrut dan menyusun tim proyek": HR +2, Product +1.
- Q2 "Kampanye yang ramai dibicarakan dan halaman promonya ramai dikunjungi": Marketing +2, Front-End +1.

## Kapan `version` dinaikkan

Lihat `versioning_policy` di `config/quiz.v2.json`. Ringkasnya: perubahan apa pun yang bisa mengubah skor untuk jawaban yang sama menaikkan MAJOR (3.0.0) dan mengharuskan test vector dibuat ulang. Tes `test_vectors_match_current_config_file` gagal bila config berubah tanpa membuat ulang vector.
