"""Rubrik spesifik untuk 16 AI case (scripts/seed/data/ai_cases.json di repo web).

Aturan: setiap level membedakan diri lewat hal yang bisa dicek, level 3 = tepat lulus, satu kekurangan
hanya dinilai di satu kriteria. Nama kriteria dan bobot sama dengan seed. Deskripsi level hanya dibaca
penilai AI, sehingga boleh memuat acuan hitungan.
"""

ONLY = "Kekurangan di bagian lain tidak dinilai di sini."


def comm(parts: str, reader: str, extra: str) -> tuple[str, list[str]]:
    """Kriteria komunikasi: struktur dan kejelasan saja, bukan kelengkapan atau kebenaran isi."""
    return (
        f"Dinilai struktur, keruntutan, dan kejelasan alasan untuk {reader}, hanya dari bagian yang ditulis. Bagian tugas yang tidak ditulis, kebenaran, dan kelengkapan isi dinilai di kriteria lain.",
        [
            f"Tidak ada tulisan buatan peserta yang bisa diikuti: kosong, menyalin soal, atau tidak membahas {parts}.",
            f"Ada tulisan tentang {parts}, tetapi bagian yang ditulis bercampur atau sebagian besar berupa kalimat umum yang bisa dipakai untuk kasus apa pun.",
            f"Bagian yang ditulis bisa dibedakan dan merujuk data kasus, tetapi pilihan atau klaim utama sebagian besar tanpa alasan. Tidak adanya salah satu dari {parts} tidak menurunkan level.",
            f"Level 3 terpenuhi, dan hampir semua pilihan utama disertai alasan; istilah dan satuan konsisten; {reader} bisa mengikuti tanpa bertanya urutannya.",
            f"Level 4 terpenuhi, dan {extra}.",
        ],
    )


RUBRICS: dict[str, dict[str, tuple[str, list[str]]]] = {
    "rancang-ulang-endpoint-ekspor-laporan": {
        "Ketepatan diagnosis": (
            f"Penyebab lambat dan boros memori dikenali, diurutkan menurut dampak, dan disertai rencana pembuktian. {ONLY}",
            [
                "Tidak ada penyebab yang disebut, atau hanya menyalin gejala dari soal.",
                "Penyebab masih umum (data banyak, server kurang kuat, timeout pendek) atau hanya satu penyebab yang menunjuk langkah proses di kasus.",
                "Minimal tiga penyebab menunjuk langkah proses di kasus (query tambahan per transaksi, semua data atau file di memori, proses panjang di dalam request), tetapi urutan dampak tanpa alasan atau cara membuktikan masih umum.",
                "Level 3 terpenuhi, urutan dampak diberi alasan dari data kasus, dan minimal dua penyebab punya cara pembuktian spesifik (misalnya jumlah query, profil memori, query plan).",
                "Level 4 terpenuhi, minimal tiga penyebab punya cara pembuktian spesifik, penyebab terbesar punya perkiraan angka dampak, dan asumsi ditandai sebagai asumsi.",
            ],
        ),
        "Kualitas rancangan solusi": (
            "Pendekatan sesuai batasan dan alur lengkap dari tombol ditekan sampai unduhan. Penanganan gagal, pembatasan, retensi, dan uji beban dinilai di kriteria Ketahanan.",
            [
                "Tidak ada rancangan buatan peserta.",
                "Proses tetap di dalam request (misalnya hanya menambah RAM, timeout, atau cache), atau bergantung pada layanan yang dilarang batasan kasus.",
                "Ekspor dipindah ke proses latar belakang dengan komponen yang ada dan data diambil bertahap, tetapi minimal dua hal ini belum jelas: kontrak API, cara memproses data, tempat file, notifikasi.",
                "Kontrak API (endpoint, status, respons), pemrosesan bertahap tanpa query per transaksi, penyusunan file hemat memori, tempat file, dan notifikasi semuanya ada; paling banyak satu yang hanya disebut tanpa penjelasan.",
                "Level 4 terpenuhi, minimal satu alternatif dibandingkan beserta alasan ditolak, dan ada perkiraan jumlah query atau memori setelah perbaikan.",
            ],
        ),
        "Ketahanan dan penanganan risiko": (
            f"Penanganan gagal, pembatasan per toko, retensi file, dan uji beban akhir bulan. {ONLY}",
            [
                "Keempat aspek tidak dibahas, atau hanya pernyataan bahwa sistem akan andal.",
                "Satu atau dua aspek konkret. Konkret berarti ada angka atau langkah kerja; dihapus setelah beberapa hari, worker dibatasi, atau dilakukan load test tanpa angka atau langkah belum konkret.",
                "Tiga aspek konkret menurut arti di level 2, sedangkan aspek keempat tidak ada atau belum konkret.",
                "Keempat aspek konkret menurut arti di level 2.",
                "Level 4 terpenuhi, menjelaskan keadaan saat worker mati di tengah proses, dan uji beban punya kriteria lulus yang terukur dari data kasus.",
            ],
        ),
        "Kejelasan komunikasi": comm("diagnosis, rancangan, dan ketahanan", "engineer lain", "minimal dua trade-off dijelaskan untung dan ruginya serta asumsi dipisahkan dari fakta kasus"),
    },
    "halaman-produk-lambat-di-hp-entry-level": {
        "Ketepatan diagnosis": (
            f"Penyebab dikaitkan dengan metrik yang tepat (LCP, TBT/INP, CLS) memakai data kasus. {ONLY}",
            [
                "Tidak ada penyebab yang disebut, atau hanya mengulang angka dari soal.",
                "Kurang dari tiga penyebab spesifik, atau sebagian besar dikaitkan dengan metrik yang salah.",
                "Tiga penyebab dari data kasus dengan metrik yang benar, atau empat penyebab dengan satu atau dua kaitan metrik yang salah atau kosong.",
                "Minimal empat penyebab dengan metrik yang benar (acuan: gambar besar ke LCP, JavaScript ke TBT/INP, banner tanpa dimensi ke CLS, font memblokir render ke LCP), masing-masing memakai angka kasus.",
                "Level 4 terpenuhi, dampak antarpenyebab dibandingkan, data lab dibedakan dari data lapangan, dan ada cara memastikan elemen LCP atau penyebab layout shift.",
            ],
        ),
        "Kualitas perbaikan dan prioritas": (
            f"Teknik tepat dan urutannya masuk akal terhadap dampak, usaha, dan kapasitas 2 orang selama 3 minggu. {ONLY}",
            [
                "Tidak ada perbaikan yang disebut.",
                "Perbaikan umum (optimasi gambar, kurangi JavaScript) tanpa teknik, atau mengubah desain secara drastis.",
                "Minimal tiga perbaikan dengan teknik yang benar, tetapi urutan tanpa alasan atau perkiraan dampak sebagian besar tidak ada.",
                "Minimal empat perbaikan dengan teknik spesifik (misalnya gambar responsif, pemecahan bundle, font-display, dimensi tetap), urutan berdasarkan dampak dan usaha, dan perkiraan dampak tiap perbaikan.",
                "Level 4 terpenuhi, dibagi ke jadwal 3 minggu untuk 2 orang, ada yang sengaja ditunda beserta alasannya, dan risiko tiap perbaikan besar (misalnya gambar LCP tidak boleh lazy load) dibahas.",
            ],
        ),
        "Target dan pemantauan": (
            f"Target metrik, verifikasi sebelum rilis, dan pencegahan penurunan. {ONLY}",
            [
                "Target, verifikasi, dan pemantauan tidak ada.",
                "Hanya satu dari tiga bagian yang dibahas, atau target tanpa angka.",
                "Target berangka untuk minimal dua metrik, dan salah satu dari verifikasi atau pemantauan masih umum.",
                "Target berangka untuk LCP, INP atau TBT, dan CLS; verifikasi memakai kondisi yang sama dengan data kasus; pemantauan menyebut alat atau data lapangan.",
                "Level 4 terpenuhi, ada batas otomatis (misalnya performance budget di CI) dengan angka, dan target dikaitkan dengan tenggat rilis promo atau konversi.",
            ],
        ),
        "Kejelasan komunikasi": comm("diagnosis, perbaikan, dan target", "tim non-teknis", "setiap istilah teknis diberi arti singkat dan ada ringkasan dampak bagi bisnis"),
    },
    "aplikasi-sering-crash-setelah-update": {
        "Kualitas analisis dan hipotesis": (
            f"Masalah dikelompokkan dan dikaitkan dengan perubahan versi 4.2 beserta cara verifikasi. {ONLY}",
            [
                "Tidak ada analisis, atau hanya mengulang data soal.",
                "Hanya satu kelompok masalah yang dikaitkan dengan perubahan versi 4.2, atau kaitannya keliru.",
                "Minimal tiga kelompok (crash memori, crash notifikasi, ANR, baterai) dan minimal dua dikaitkan benar dengan perubahan 4.2, tetapi verifikasi masih umum.",
                "Keempat kelompok dibahas, kaitannya benar (prefetch atau pustaka gambar ke memori, sinkronisasi di thread utama ke ANR, lokasi tiap 2 detik ke baterai), dan minimal tiga punya cara verifikasi spesifik.",
                "Level 4 terpenuhi, diakui bahwa penyebab crash notifikasi tidak langsung terlihat dari daftar perubahan, dan prioritas memakai porsi crash serta perangkat terdampak.",
            ],
        ),
        "Mitigasi dan perbaikan": (
            f"Mitigasi sebelum akhir pekan dan perbaikan permanen yang cocok dengan 5 hari kerja ditambah review toko. {ONLY}",
            [
                "Tidak ada langkah mitigasi atau perbaikan.",
                "Hanya mitigasi atau hanya perbaikan permanen, atau bergantung pada hal yang mustahil (misalnya menarik versi dari pengguna yang sudah memperbarui).",
                "Mitigasi dan perbaikan permanen ada untuk minimal dua kelompok masalah, tetapi urutan, penanggung jawab, atau waktu review toko belum dihitung.",
                "Mitigasi cepat (misalnya konfigurasi jarak jauh, menghentikan rollout, hotfix kecil) dan perbaikan permanen mencakup minimal tiga kelompok, lengkap dengan urutan, pihak terlibat, dan jadwal yang menghitung review toko.",
                "Level 4 terpenuhi, ada rencana bila perbaikan belum siap saat promo, dan komunikasi ke pengguna selama masa transisi dijelaskan.",
            ],
        ),
        "Strategi rilis dan pemantauan": (
            f"Rollout bertahap, feature flag, ambang pemantauan, dan kriteria rollback. {ONLY}",
            [
                "Tidak ada usulan proses rilis.",
                "Hanya satu dari empat unsur, atau semuanya tanpa angka.",
                "Dua atau tiga unsur dibahas, minimal satu punya angka.",
                "Keempat unsur dibahas dengan persentase tahap dan ambang berangka (misalnya crash-free sessions).",
                "Level 4 terpenuhi, setiap tahap punya lama tunggu dan syarat lanjut, serta ada pengujian perangkat RAM rendah sebelum rilis.",
            ],
        ),
        "Kejelasan komunikasi": comm("analisis, mitigasi, dan proses rilis", "tim lintas fungsi", "ada urutan prioritas dengan waktu dan penanggung jawab yang bisa langsung dijalankan"),
    },
    "penjualan-turun-mendadak-cari-penyebab": {
        "Ketepatan analisis data": (
            f"Dekomposisi pendapatan, hitungan, dan segmen penyebab. {ONLY}",
            [
                "Tidak ada hitungan atau segmen yang disebut.",
                "Ada hitungan tetapi sebagian besar keliru, atau segmen penyebab utama salah.",
                "Segmen mobile dan tahap checkout ke pembayaran dikenali, tetapi dekomposisi tidak lengkap atau ada satu kesalahan hitung yang tidak mengubah kesimpulan.",
                "Ketiga faktor dihitung benar (acuan: kunjungan sekitar -1,7%, konversi sekitar -24%, nilai pesanan sekitar -1,4%) dan segmen serta tahap funnel dibuktikan dengan angka. Pembagian rupiah boleh berbeda karena urutan metode.",
                "Level 4 terpenuhi, kontribusi order mobile dihitung (acuan: sekitar 860 dari 922 order hilang), dan metode atau efek interaksi dekomposisi dijelaskan.",
            ],
        ),
        "Kekuatan bukti dan penalaran": (
            f"Bukti, hipotesis alternatif, dan batas keyakinan. {ONLY}",
            [
                "Tidak ada kesimpulan, atau kesimpulan tanpa bukti.",
                "Kesimpulan disebut tetapi bukti hanya satu atau bertentangan dengan data.",
                "Minimal dua bukti data dikaitkan dengan rilis checkout atau dompet digital, tetapi hipotesis alternatif atau batas keyakinan belum ada.",
                "Minimal dua bukti, minimal dua hipotesis alternatif disingkirkan dengan data, dan batas keyakinan disebut.",
                "Level 4 terpenuhi, membedakan korelasi dari sebab, serta menyebut data yang kurang (misalnya versi OS) atau bahwa kenaikan gagal bayar dompet digital 2% ke 14% belum tentu menjelaskan seluruh penurunan 66% ke 41%.",
            ],
        ),
        "Kualitas rekomendasi": (
            f"Tindakan segera, ukuran pemulihan, analisis lanjutan, dan perkiraan dampak. {ONLY}",
            [
                "Tidak ada rekomendasi.",
                "Rekomendasi umum (perbaiki checkout, tingkatkan promosi) tanpa ukuran.",
                "Tindakan segera konkret, dan salah satu dari ukuran pemulihan, analisis lanjutan, atau perkiraan dampak belum ada.",
                "Keempat bagian ada, tindakan diprioritaskan, dan perkiraan dampak memakai hitungan (acuan: sekitar Rp175 juta per minggu bila konversi mobile kembali 2,5%).",
                "Level 4 terpenuhi, ukuran pemulihan punya ambang dan tenggat, dan ada langkah bila hipotesis ternyata salah.",
            ],
        ),
        "Kejelasan penyampaian": comm("hitungan, penyebab, dan rekomendasi", "pemangku kepentingan non-teknis", "kesimpulan ada di awal dan setiap angka penting diberi arti bagi bisnis"),
    },
    "evaluasi-usability-form-pengajuan": {
        "Kualitas identifikasi masalah": (
            f"Masalah usability dengan bukti, heuristik, dan tingkat keparahan. {ONLY}",
            [
                "Tidak ada masalah yang dikenali selain mengulang soal.",
                "Kurang dari tiga masalah, atau sebagian besar tanpa bukti dari data.",
                "Tiga atau empat masalah berbukti, atau lima masalah tetapi heuristik atau keparahan banyak yang kosong.",
                "Minimal lima masalah berbeda, masing-masing punya bukti kasus, heuristik yang cocok, dan tingkat keparahan.",
                "Level 4 terpenuhi, keparahan diberi dasar (jumlah peserta, data berhenti, atau dampak), dan bukti analitik dihubungkan dengan hasil uji atau kutipan.",
            ],
        ),
        "Kualitas usulan desain": (
            f"Perbaikan untuk masalah teratas sesuai batasan regulator dan layar ponsel. {ONLY}",
            [
                "Tidak ada usulan desain.",
                "Usulan umum (buat lebih sederhana), atau menghapus isian yang wajib dikumpulkan.",
                "Minimal tiga dari lima aspek (struktur langkah, tata letak, teks bantuan, validasi, pesan error) dibahas, dan semua isian tetap dikumpulkan, tetapi sebagian tanpa contoh.",
                "Kelima aspek dibahas dan menjawab masalah teratas, ada contoh teks atau pesan error, dan pertimbangan layar ponsel disebut.",
                "Level 4 terpenuhi, pembagian isian ke langkah dijelaskan beserta alasannya, dan ada penanganan simpan sementara atau kegagalan unggah KTP.",
            ],
        ),
        "Rencana pengukuran": (
            f"Metrik, target, dan uji lanjutan. {ONLY}",
            [
                "Tidak ada metrik, target, atau rencana uji.",
                "Metrik disebut tanpa target, atau target tanpa cara mengukur.",
                "Minimal dua metrik dengan target berangka, tetapi rencana uji lanjutan masih umum.",
                "Metrik utama (misalnya penyelesaian dari 27,7%) dan metrik per titik berhenti punya target berangka, serta rencana uji menyebut metode dan jumlah peserta atau sampel.",
                "Level 4 terpenuhi, ada metrik pengaman (misalnya kesalahan data) dan kriteria keputusan bila target tidak tercapai.",
            ],
        ),
        "Kejelasan komunikasi": comm("masalah, usulan, dan pengukuran", "tim produk dan engineering", "setiap usulan bisa dilacak ke masalah yang dijawabnya"),
    },
    "prioritas-fitur-dengan-sumber-daya-terbatas": {
        "Kualitas analisis prioritas": (
            f"Kerangka penilaian dipakai konsisten untuk tujuh permintaan dengan data kasus. {ONLY}",
            [
                "Tidak ada penilaian fitur.",
                "Sebagian fitur dinilai tanpa kerangka, atau total usaha melebihi kapasitas yang tersedia.",
                "Minimal lima fitur dinilai dengan kerangka dan pilihan muat dalam 12 minggu-engineer, tetapi asumsi atau sebagian skor tidak dijelaskan.",
                "Ketujuh fitur dinilai konsisten, asumsi ditulis, data retensi dan survei dipakai, dan pilihan muat dalam 12 minggu-engineer (16 dikurangi 4).",
                "Level 4 terpenuhi, jumlah permintaan dibedakan dari dampak ke target, dan keputusan diuji bila satu asumsi penting berubah.",
            ],
        ),
        "Keputusan dan manajemen trade-off": (
            f"Keputusan tegas untuk B dan G, risiko, serta jawaban atas keberatan. {ONLY}",
            [
                "Tidak ada keputusan.",
                "Keputusan ada, tetapi B atau G tidak dibahas, atau alasannya hanya selera.",
                "B dan G diputuskan dengan alasan dari data, tetapi risiko atau keberatan pendukungnya belum dijawab.",
                "B dan G diputuskan tegas, kapasitas atau biaya agregator dipakai sebagai alasan, dan minimal dua risiko atau trade-off disebut.",
                "Level 4 terpenuhi, ada jalan tengah atau syarat untuk meninjau ulang B, dan keberatan pimpinan serta marketing dijawab masing-masing.",
            ],
        ),
        "Metrik dan rencana rilis": (
            f"Metrik utama, metrik pengaman, target, dan cara peluncuran. {ONLY}",
            [
                "Tidak ada metrik atau rencana rilis.",
                "Metrik umum tanpa target, atau hanya rencana rilis.",
                "Metrik utama berangka sesuai target kuartal, tetapi metrik pengaman atau cara peluncuran masih umum.",
                "Metrik utama dan pengaman punya angka, dan peluncuran bertahap atau eksperimen dijelaskan ukurannya.",
                "Level 4 terpenuhi, ada kriteria lanjut atau berhenti, dan disebut bahwa retensi pengguna pengingat (38% dibanding 21%) belum tentu hubungan sebab akibat.",
            ],
        ),
        "Kejelasan komunikasi": comm("analisis, keputusan, dan metrik", "pimpinan", "ringkasan keputusan bisa dibaca terpisah dan memuat apa yang dikerjakan, ditunda, dan ditolak"),
    },
    "kampanye-produk-baru-anggaran-terbatas": {
        "Kualitas strategi dan pesan": (
            f"Audiens, insight, pesan inti, dan pembeda dari pesaing. {ONLY}",
            [
                "Tidak ada audiens atau pesan.",
                "Audiens sangat luas, atau pesan hanya menonjolkan sehat seperti pesaing.",
                "Audiens memakai data kasus dan ada pesan inti, tetapi insight atau pembeda dari pesaing lemah.",
                "Audiens spesifik, insight menjelaskan situasi atau alasan membeli, pesan inti satu kalimat, dan pembeda dari pesaing dijelaskan.",
                "Level 4 terpenuhi, ada contoh penerapan pesan di minimal dua kanal dan alasan mengapa segmen lain tidak dipilih.",
            ],
        ),
        "Rencana kanal dan anggaran": (
            f"Alokasi Rp30 juta per kanal dan minggu sesuai jadwal minimarket. {ONLY}",
            [
                "Tidak ada alokasi anggaran.",
                "Alokasi melebihi Rp30 juta, atau mengarahkan pembeli ke minimarket sebelum minggu ke-3.",
                "Total Rp30 juta dibagi per kanal dengan alasan, tetapi pembagian per minggu atau jadwal minimarket belum jelas.",
                "Total tepat Rp30 juta per kanal dan per minggu, jadwal minimarket minggu ke-3 dipakai, dan pilihan kanal memakai data kasus.",
                "Level 4 terpenuhi, dihitung bahwa iklan CPA Rp28.000 tidak sebanding margin sekitar Rp5.130 per botol (atau kesimpulan setara), dan ada cadangan atau aturan pengalihan anggaran.",
            ],
        ),
        "KPI dan rencana evaluasi": (
            f"KPI per tahap funnel, target, evaluasi mingguan, dan tindakan. {ONLY}",
            [
                "Tidak ada KPI.",
                "KPI hanya satu tahap atau tanpa angka.",
                "KPI berangka di minimal dua tahap funnel, tetapi evaluasi mingguan atau tindakan saat di bawah target masih umum.",
                "KPI berangka di minimal tiga tahap funnel, evaluasi mingguan punya data yang dilihat, dan ada tindakan bila di bawah target.",
                "Level 4 terpenuhi, kewajaran target 40.000 botol diuji dengan hitungan, dan tindakan punya ambang angka.",
            ],
        ),
        "Kejelasan komunikasi": comm("strategi, anggaran, dan KPI", "tim dua orang", "ada jadwal atau tabel kerja mingguan dengan penanggung jawab"),
    },
    "kelayakan-investasi-mesin-produksi": {
        "Ketepatan perhitungan": (
            f"NPV, payback, dan hitungan sensitivitas dengan langkah terlihat. {ONLY}",
            [
                "Tidak ada perhitungan.",
                "NPV dan payback salah atau tidak dihitung.",
                "Salah satu dari NPV atau payback benar, atau keduanya benar tanpa langkah; sensitivitas sebagian salah atau belum ada.",
                "NPV (acuan: sekitar Rp12,3 juta) dan payback (acuan: sekitar 3,4 tahun) benar dengan langkah; minimal dua dari tiga angka sensitivitas benar (acuan: -10% sekitar -Rp12,9 juta, -20% sekitar -Rp38,1 juta, batas sekitar Rp66,6 juta per tahun).",
                "Semua angka acuan level 4 benar dengan langkah, dan asumsi hitungan (arus kas akhir tahun, nilai sisa nol) ditulis.",
            ],
        ),
        "Kualitas analisis risiko": (
            "Arti hasil sensitivitas dan risiko permintaan. Kebenaran angka dinilai di kriteria Ketepatan perhitungan.",
            [
                "Tidak ada analisis risiko.",
                "Risiko disebut umum tanpa dikaitkan dengan arus kas atau NPV.",
                "Dijelaskan bahwa NPV peka terhadap penurunan arus kas, tetapi batas kelayakan atau risiko pesanan yang belum tentu kembali belum dibahas.",
                "Batas arus kas minimum ditafsirkan sebagai ruang penurunan yang tipis (acuan: sekitar 5%), dan risiko pesanan ditolak yang belum tentu kembali dibahas.",
                "Level 4 terpenuhi, ada cara menguji permintaan sebelum membeli, dan kemungkinan skenario dibandingkan.",
            ],
        ),
        "Kualitas rekomendasi": (
            f"Keputusan beli, tunda, atau ubah rencana yang sesuai hasil hitung, dana darurat, dan alternatif. {ONLY}",
            [
                "Tidak ada rekomendasi.",
                "Rekomendasi bertentangan dengan hitungan peserta, atau dana darurat diabaikan.",
                "Rekomendasi tegas dan sejalan dengan hitungan, tetapi dana darurat atau alternatif hanya disinggung.",
                "Rekomendasi tegas, dihitung bahwa sisa dana Rp70 juta di bawah minimal Rp100 juta, dan minimal satu alternatif pendanaan atau pembelian bertahap dibahas.",
                "Level 4 terpenuhi, ada syarat atau angka pemicu untuk mengubah keputusan dan langkah berikutnya bagi pemilik.",
            ],
        ),
        "Kejelasan komunikasi": comm("perhitungan, risiko, dan rekomendasi", "pemilik non-keuangan", "NPV dan payback dijelaskan artinya dengan bahasa sehari-hari dan keputusan ada di awal"),
    },
    "rekonsiliasi-bank-dan-jurnal-penyesuaian": {
        "Ketepatan rekonsiliasi": (
            f"Pengelompokan lima item dan saldo disesuaikan dua sisi. {ONLY}",
            [
                "Tidak ada rekonsiliasi.",
                "Kurang dari tiga item di sisi yang benar, atau saldo akhir dipaksakan sama.",
                "Tiga atau empat item di sisi dan tanda yang benar, atau semua benar tetapi hanya satu sisi yang dihitung.",
                "Kelima item di sisi dan tanda yang benar, kedua sisi sama (acuan: Rp54.050.000), dengan paling banyak satu salah tulis yang tidak mengubah hasil.",
                "Level 4 tanpa kesalahan, setiap item diberi alasan klasifikasi, dan kesamaan kedua sisi dibuktikan eksplisit.",
            ],
        ),
        "Ketepatan jurnal penyesuaian": (
            f"Akun, sisi debit-kredit, jumlah, dan alasan item yang tidak dijurnal. {ONLY}",
            [
                "Tidak ada jurnal.",
                "Paling banyak satu jurnal benar, atau setoran dalam perjalanan atau cek beredar ikut dijurnal.",
                "Dua dari tiga jurnal benar, atau ketiganya benar tetapi alasan item tidak dijurnal tidak ada.",
                "Ketiga jurnal benar (acuan: beban administrasi 350.000 debit, kas kredit; kas 150.000 debit, pendapatan bunga kredit; kas 350.000 debit, beban listrik kredit) dan alasan dua item tidak dijurnal dijelaskan.",
                "Level 4 terpenuhi, jurnal memuat tanggal dan nomor akun, dan pengaruhnya ke saldo kas Rp54.050.000 ditunjukkan.",
            ],
        ),
        "Pengendalian internal": (
            f"Kelemahan dan perbaikan praktis. {ONLY}",
            [
                "Tidak ada kelemahan atau perbaikan.",
                "Kelemahan atau perbaikan disebut umum tanpa kaitan ke kasus.",
                "Perangkapan tugas atau rekonsiliasi yang terlambat dikenali, dan ada satu atau dua perbaikan konkret.",
                "Kedua kelemahan itu dikenali, risikonya dijelaskan, dan minimal tiga perbaikan praktis diusulkan.",
                "Level 4 terpenuhi, perbaikan punya pelaksana dan frekuensi, serta sesuai untuk usaha kecil (misalnya kontrol pengganti bila staf terbatas).",
            ],
        ),
        "Kejelasan dan kerapian": comm("rekonsiliasi, jurnal, dan pengendalian", "pemeriksa atau auditor", "setiap angka bisa ditelusuri ke nomor item di soal dan format jurnal seragam"),
    },
    "turnover-karyawan-baru-enam-bulan-pertama": {
        "Kualitas analisis akar masalah": (
            f"Akar masalah dibedakan dari gejala, didukung data dan pembanding enam cabang. {ONLY}",
            [
                "Tidak ada analisis, atau hanya mengulang angka.",
                "Hanya gejala (turnover tinggi, gaji rendah) atau satu penyebab tanpa data.",
                "Minimal dua akar masalah didukung data exit interview, tetapi pembanding enam cabang atau pola bulan ke-2 dan ke-3 belum dipakai.",
                "Minimal dua akar masalah dibedakan dari gejala, memakai data exit interview, waktu keluar, dan pelajaran dari enam cabang.",
                "Level 4 terpenuhi, ada cara membuktikan penyebab dan keterbatasan data disebut (misalnya hanya 112 responden atau cabang baik bisa berbeda karena hal lain).",
            ],
        ),
        "Kualitas rancangan program": (
            f"Program 90 hari yang muat di Rp150 juta, 3 orang HR, dan kepala toko yang sibuk. {ONLY}",
            [
                "Tidak ada program.",
                "Kegiatan umum (pelatihan, motivasi), atau biaya jelas melebihi Rp150 juta.",
                "Program konkret dan menjawab akar masalah, tetapi dua dari empat hal belum jelas: aktivitas, penanggung jawab, jadwal, biaya.",
                "Aktivitas, penanggung jawab, jadwal 90 hari, dan biaya ada; total tidak melebihi Rp150 juta; beban kepala toko dibatasi secara konkret.",
                "Level 4 terpenuhi, rincian biaya bisa dijumlah (misalnya per cabang atau per karyawan), dan masalah jadwal kerja berubah ditangani langsung.",
            ],
        ),
        "Metrik dan evaluasi": (
            f"Metrik, target, pengumpulan data, dan uji coba bertahap. {ONLY}",
            [
                "Tidak ada metrik.",
                "Metrik tanpa target, atau target tanpa cara mengumpulkan data.",
                "Target turnover berangka dan satu metrik lain, tetapi uji coba atau pengumpulan data masih umum.",
                "Target berangka dengan tenggat, minimal satu metrik awal sebelum 6 bulan, cara kumpul data, dan uji coba di sejumlah cabang.",
                "Level 4 terpenuhi, ada cabang pembanding dan kriteria lanjut, atau manfaat dihitung terhadap biaya Rp6,5 juta per karyawan.",
            ],
        ),
        "Kejelasan komunikasi": comm("akar masalah, program, dan metrik", "manajemen", "ada ringkasan masalah, biaya, dan hasil yang diharapkan di awal"),
    },
    "stok-menumpuk-di-satu-gudang": {
        "Ketepatan perhitungan inventori": (
            f"Cakupan stok, penjualan hilang, transfer, safety stock, dan reorder point. {ONLY}",
            [
                "Tidak ada perhitungan.",
                "Hanya cakupan stok yang benar, atau sebagian besar hitungan salah.",
                "Cakupan (acuan: Jakarta 40 hari, Surabaya 3,2 hari) dan penjualan hilang (acuan: sekitar 2.750 unit) benar, tetapi transfer, safety stock, atau reorder point salah atau tanpa langkah.",
                "Cakupan dan penjualan hilang benar; transfer punya langkah dan muat kapasitas 6.000; safety stock dan reorder point kedua gudang benar untuk tingkat layanan yang ditulis (acuan 95% dan lead time 7 hari: Jakarta sekitar 262 dan 2.362; Surabaya sekitar 306 dan 2.056). Tingkat layanan atau periode lain boleh bila konsisten.",
                "Level 4 terpenuhi, dan periode pembelian 2 minggu ikut dihitung (acuan periode lindung 21 hari) atau penjualan selama transfer 2 hari diperhitungkan.",
            ],
        ),
        "Kualitas kebijakan dan rencana": (
            f"Kebijakan sederhana sesuai kapasitas, minimum pesanan, dan siklus 2 minggu. {ONLY}",
            [
                "Tidak ada kebijakan.",
                "Kebijakan umum (pantau stok), atau melanggar kapasitas Surabaya atau minimum 5.000 unit.",
                "Ada aturan pengisian per gudang yang tidak melanggar batasan, tetapi minimum pesanan atau siklus 2 minggu belum ditangani.",
                "Aturan per gudang jelas (kapan dan berapa), kapasitas 6.000, minimum 5.000, dan siklus 2 minggu semuanya ditangani.",
                "Level 4 terpenuhi, aturan bisa dijalankan staf tanpa hitungan rumit, dan ada cara membagi kiriman antargudang serta menangani stok lebih dari 90 hari.",
            ],
        ),
        "Analisis biaya dan risiko": (
            f"Perbandingan biaya transfer, simpan, dan penjualan hilang beserta pemantauan. {ONLY}",
            [
                "Tidak ada perbandingan biaya atau risiko.",
                "Hanya satu jenis biaya dihitung, atau perbandingan tanpa angka.",
                "Dua jenis biaya dihitung, tetapi yang ketiga, risiko, atau pemantauan belum ada.",
                "Ketiga biaya dibandingkan dengan angka (acuan: margin hilang Rp85.000 per unit dibanding transfer Rp1.500), dan ada risiko serta indikator pantau.",
                "Level 4 terpenuhi, indikator punya ambang dan penanggung jawab, atau dampak pada stok Jakarta setelah transfer ikut dinilai.",
            ],
        ),
        "Kejelasan komunikasi": comm("hitungan, kebijakan, dan biaya", "staf gudang", "ada tabel atau langkah singkat berisi angka yang dipakai staf sehari-hari"),
    },
    "review-klausul-kontrak-vendor-berisiko": {
        "Ketepatan identifikasi risiko": (
            f"Risiko hukum dan bisnis keempat klausul beserta prinsip yang relevan. {ONLY}",
            [
                "Tidak ada risiko yang dikenali.",
                "Paling banyak dua klausul dibahas, atau risikonya keliru.",
                "Keempat klausul dibahas, tetapi sebagian hanya sisi bisnis atau hukum, atau prinsipnya tidak disebut.",
                "Keempat klausul punya risiko hukum dan bisnis yang benar, dan minimal tiga dikaitkan dengan prinsip relevan (misalnya pelindungan data pribadi, tujuan terbatas, keseimbangan para pihak).",
                "Level 4 terpenuhi, dampak memakai angka kasus (misalnya batas 1 bulan sekitar Rp75 juta dibanding kerugian Rp300 juta), dan hal yang perlu dicek ahli hukum ditandai.",
            ],
        ),
        "Kualitas usulan revisi": (
            f"Redaksi pengganti yang jelas, seimbang, dan realistis. {ONLY}",
            [
                "Tidak ada usulan redaksi.",
                "Hanya arahan (perlu diperbaiki) tanpa redaksi, atau redaksi untuk paling banyak satu klausul.",
                "Redaksi untuk dua atau tiga klausul, atau empat klausul tetapi sebagian kabur atau sangat berat sebelah.",
                "Redaksi untuk keempat klausul, jelas hak dan kewajibannya, dan memuat angka atau batas waktu pada klausul yang membutuhkannya.",
                "Level 4 terpenuhi, ada posisi cadangan untuk klausul sulit dan pengecualian batas tanggung jawab (misalnya kebocoran data).",
            ],
        ),
        "Prioritas dan strategi negosiasi": (
            f"Urutan risiko, yang harus dimenangkan, kompromi, dan kondisi tenggat 10 hari. {ONLY}",
            [
                "Tidak ada prioritas.",
                "Urutan tanpa alasan, atau semua klausul dianggap sama penting.",
                "Urutan dengan alasan, tetapi yang harus dimenangkan atau yang bisa dikompromikan belum jelas.",
                "Urutan beralasan, klausul wajib menang dan bisa kompromi dipisahkan, dan ada tawaran kompromi konkret.",
                "Level 4 terpenuhi, memperhitungkan vendor tunggal dalam anggaran dan tenggat 10 hari, serta ada langkah bila vendor menolak.",
            ],
        ),
        "Kejelasan komunikasi": comm("risiko, revisi, dan negosiasi", "manajemen non-hukum", "ringkasan satu paragraf untuk manajemen memuat risiko terbesar dan keputusan yang diminta"),
    },
    "penetrasi-segmen-baru-dan-proposal-kemitraan": {
        "Kualitas strategi masuk pasar": (
            f"Segmen awal, proposisi nilai, harga, dan saluran dengan data kasus. {ONLY}",
            [
                "Tidak ada strategi.",
                "Segmen sangat luas (semua UMKM kuliner), atau tetap bertumpu pada penjualan langsung tanpa alasan.",
                "Tiga dari empat unsur (segmen, proposisi nilai, harga, saluran) ada dan memakai data kasus.",
                "Keempat unsur ada, harga dibandingkan dengan kompetitor Rp99.000-Rp199.000, dan alasan tidak memakai penjualan langsung memakai biaya atau kapasitas.",
                "Level 4 terpenuhi, kapasitas demo dihitung (acuan: sekitar 2.600 per tahun untuk target 2.000 pelanggan) atau segmen awal diberi ukuran pasar.",
            ],
        ),
        "Kualitas proposal kemitraan": (
            f"Pemilihan satu mitra dan proposal yang saling menguntungkan. {ONLY}",
            [
                "Tidak ada mitra atau proposal.",
                "Mitra dipilih tanpa perbandingan, atau manfaat hanya untuk satu pihak.",
                "Mitra dipilih dengan alasan, dan dua atau tiga dari empat unsur ada (manfaat mitra, peran, skema insentif, langkah awal).",
                "Mitra dibandingkan dengan dua calon lain, dan keempat unsur ada dengan skema insentif berangka.",
                "Level 4 terpenuhi, insentif dicek terhadap biaya akuisisi atau nilai pelanggan, dan langkah awal punya waktu serta ukuran keberhasilan.",
            ],
        ),
        "Target dan unit ekonomi": (
            f"Target 12 bulan, biaya akuisisi dibanding nilai pelanggan, dan risiko. {ONLY}",
            [
                "Tidak ada target atau hitungan.",
                "Target tanpa tahapan, atau hitungan unit ekonomi salah mendasar.",
                "Target 12 bulan dan unit ekonomi dihitung, tetapi satu asumsi penting (misalnya churn) tidak dipakai, atau risiko belum ada.",
                "Target bertahap, biaya akuisisi dan nilai pelanggan dihitung dengan churn (acuan: Rp150.000 dibagi 2,3% sekitar Rp6,5 juta sebelum margin), dan minimal dua risiko dengan mitigasi.",
                "Level 4 terpenuhi, masa balik modal dihitung atau churn dan harga segmen baru diuji dengan asumsi lebih buruk.",
            ],
        ),
        "Kejelasan komunikasi": comm("strategi, proposal, dan target", "calon mitra", "proposal bisa dibaca terpisah dan ditutup dengan ajakan atau langkah konkret"),
    },
    "strategi-pengujian-fitur-checkout": {
        "Analisis risiko dan cakupan": (
            f"Area berisiko dan cakupan menurut prioritas. {ONLY}",
            [
                "Tidak ada analisis risiko.",
                "Risiko umum (bug, error) tanpa menunjuk aturan fitur.",
                "Minimal tiga area berisiko dari aturan kasus, tetapi prioritas tanpa alasan atau cakupan tidak mengikuti prioritas.",
                "Minimal empat area (misalnya promo berulang, cicilan, stok 15 menit, OTP, pengembalian promo) diprioritaskan menurut dampak dan kemungkinan, dan cakupan mengikutinya.",
                "Level 4 terpenuhi, insiden Rp45 juta dipakai untuk prioritas, dan ada hal yang sengaja tidak diuji atau dikurangi beserta alasannya.",
            ],
        ),
        "Kualitas skenario uji": (
            f"Minimal 15 skenario beragam dengan hasil yang diharapkan. {ONLY}",
            [
                "Tidak ada skenario.",
                "Kurang dari delapan skenario, atau sebagian besar tanpa hasil yang diharapkan.",
                "Delapan sampai empat belas skenario dengan hasil yang diharapkan, atau 15 skenario yang hampir semuanya jalur positif.",
                "Minimal 15 skenario mencakup positif, negatif, nilai batas, dan integrasi, dengan langkah dan hasil yang benar menurut aturan (misalnya Rp500.000, Rp20.000.000, diskon Rp200.000, luar Jawa 12 bulan).",
                "Level 4 terpenuhi, ada skenario bersamaan atau urutan (misalnya promo dipakai dua kali, stok habis waktu, gagal setelah OTP), dan interaksi antar-aturan diuji.",
            ],
        ),
        "Strategi otomasi dan kriteria rilis": (
            f"Pembagian otomasi-manual, jadwal 7 hari, go/no-go, dan rilis bertahap. {ONLY}",
            [
                "Tidak ada strategi.",
                "Hanya satu atau dua dari empat unsur, atau jadwal tidak muat untuk 2 QA.",
                "Tiga unsur ada, atau empat unsur tetapi kriteria go/no-go tanpa angka.",
                "Keempat unsur ada, jadwal per hari untuk 2 QA, dan go/no-go terukur.",
                "Level 4 terpenuhi, sandbox yang tidak stabil ditangani, dan rilis bertahap punya persentase serta syarat berhenti.",
            ],
        ),
        "Kejelasan komunikasi": comm("risiko, skenario, dan strategi", "tim engineering", "skenario bernomor dan bisa dilacak ke area risikonya"),
    },
    "pipeline-cicd-untuk-deployment-manual": {
        "Ketepatan diagnosis": (
            f"Akar masalah kegagalan deployment dari data. {ONLY}",
            [
                "Tidak ada diagnosis.",
                "Penyebab umum (proses manual) tanpa memakai data kegagalan.",
                "Minimal tiga jenis kegagalan dari data dikaitkan dengan cara kerja, tetapi risiko lain (secret, rollback, ketergantungan senior) belum dibahas.",
                "Keempat jenis kegagalan (migrasi, konfigurasi, dependensi, tes) dikaitkan dengan akar masalah, dan minimal dua risiko lain dibahas.",
                "Level 4 terpenuhi, penyebab diprioritaskan dari jumlah kejadian atau waktu pulih 55 menit, dan bisa dilacak ke perbaikan tertentu.",
            ],
        ),
        "Kualitas rancangan pipeline dan rilis": (
            f"Tahapan pipeline, migrasi, secret, strategi deploy, dan rollback. {ONLY}",
            [
                "Tidak ada rancangan.",
                "Hanya menyebut alat CI/CD, atau dua dari lima unsur.",
                "Tiga atau empat unsur dijelaskan, atau lima unsur tetapi migrasi atau rollback masih umum.",
                "Kelima unsur dijelaskan dari commit sampai produksi, rollback punya langkah dan perkiraan waktu, dan secret keluar dari berkas .env di server.",
                "Level 4 terpenuhi, migrasi dibuat aman saat rollback (misalnya kompatibel dua versi), biaya alat dihitung di bawah Rp3 juta, dan alternatif strategi deploy dibandingkan.",
            ],
        ),
        "Rencana implementasi dan pemantauan": (
            f"Rencana 4 minggu, empat metrik pengiriman, serta pemantauan dan alert. {ONLY}",
            [
                "Tidak ada rencana.",
                "Hanya salah satu dari rencana, metrik, atau pemantauan.",
                "Rencana mingguan ada, tetapi metrik tanpa angka atau alert masih umum.",
                "Rencana 4 minggu untuk satu orang, keempat metrik punya kondisi awal atau target (misalnya change failure rate 32%, pemulihan 55 menit), dan alert minimum disebut ambangnya.",
                "Level 4 terpenuhi, urutan minggu mengurangi risiko terbesar lebih dulu, dan ada rencana transisi tanpa mematikan layanan.",
            ],
        ),
        "Kejelasan komunikasi": comm("diagnosis, rancangan, dan rencana", "tim kecil", "ada urutan tahap atau diagram teks yang bisa langsung dieksekusi"),
    },
    "respons-insiden-akun-admin-diambil-alih": {
        "Analisis kronologi dan penyebab": (
            f"Kronologi dari log, penyebab awal, dan hal yang belum diketahui. {ONLY}",
            [
                "Tidak ada kronologi atau penyebab.",
                "Kronologi hanya sebagian kecil atau penyebab bertentangan dengan log.",
                "Kronologi memuat minimal empat kejadian dengan waktu benar dan penyebab masuk akal, tetapi hal yang belum diketahui belum disebut.",
                "Keenam kejadian log (01.52 sampai 02.50) benar, penyebab dikaitkan dengan kata sandi bocor dan tanpa dua faktor, dan minimal dua hal yang belum diketahui disebut.",
                "Level 4 terpenuhi, fakta dibedakan dari dugaan, dan disebut bahwa log yang dihapus membuat dampak sebenarnya bisa lebih luas.",
            ],
        ),
        "Kualitas langkah respons": (
            f"Penahanan, pembersihan, pemulihan, dan bukti dalam 24 jam pertama. {ONLY}",
            [
                "Tidak ada langkah respons.",
                "Langkah umum (ganti kata sandi), atau mematikan seluruh layanan, atau akun sys-backup dan API key baru tidak ditangani.",
                "Penahanan menangani akun terkait, dan dua dari tiga hal lain (pembersihan, pemulihan, bukti) ada, tetapi urutan tanpa alasan.",
                "Keempat tahap ada berurutan dengan alasan; support-admin, sys-backup, sesi aktif, dan API key baru ditangani; bukti diamankan sebelum pembersihan; pihak terlibat disebut.",
                "Level 4 terpenuhi, ada batas waktu per langkah, layanan klinik tetap jalan terbatas, dan keterbatasan tim 2 orang ditangani (misalnya bantuan luar).",
            ],
        ),
        "Penilaian dampak dan komunikasi": (
            f"Dampak data, kewajiban notifikasi, dan komunikasi. {ONLY}",
            [
                "Tidak ada penilaian dampak atau komunikasi.",
                "Dampak umum (data bocor) tanpa cakupan, atau notifikasi tidak dibahas.",
                "Cakupan 12 klinik atau jenis data disebut, dan kewajiban 3x24 jam disebut, tetapi isi atau sasaran komunikasi belum jelas.",
                "Cakupan dan ketidakpastian dampak dinilai, tenggat 3x24 jam dihitung dari waktu insiden diketahui, dan komunikasi ke klinik, pasien, serta otoritas dibedakan.",
                "Level 4 terpenuhi, ada contoh isi pemberitahuan tanpa spekulasi dan rencana pembaruan informasi berikutnya.",
            ],
        ),
        "Pencegahan jangka panjang": (
            f"Perbaikan kontrol yang diprioritaskan dan menjawab akar masalah. {ONLY}",
            [
                "Tidak ada usulan pencegahan.",
                "Usulan umum (tingkatkan keamanan) atau hanya satu kontrol.",
                "Minimal tiga kontrol yang menjawab kasus (misalnya dua faktor, pembatasan akses per peran, log terpisah), tetapi tanpa prioritas.",
                "Minimal empat kontrol menjawab akar masalah dan diprioritaskan menurut risiko atau usaha.",
                "Level 4 terpenuhi, ada tenggat dan penanggung jawab, serta cara menguji kontrol (misalnya latihan respons atau pemeriksaan akses berkala).",
            ],
        ),
    },
}
