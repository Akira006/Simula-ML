## 1. Jawaban acak seragam

N = 20,000 responden per varian, seed 20261009. Pita toleransi masuk top-3: 15.0%-35.0% (nilai seimbang = 25%).

| Bidang | v1 top-3 | v1 top-1 | v1 (tie acak) top-3 | v2 final top-3 | v2 final top-1 | v2 top-3 (CI 95%) |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Back-End | 48.7% ⚠ | 18.1% | 38.7% | 24.0% | 8.5% | 23.4%-24.6% |
| Front-End | 24.9% | 2.9% | 18.7% | 24.7% | 8.4% | 24.1%-25.3% |
| Mobile | 9.4% ⚠ | 0.0% | 8.0% | 24.6% | 7.8% | 24.0%-25.2% |
| Data | 53.7% ⚠ | 26.6% | 50.5% | 25.1% | 8.5% | 24.5%-25.7% |
| UI/UX Design | 31.0% | 10.7% | 30.3% | 25.0% | 8.1% | 24.4%-25.6% |
| Product | 11.1% ⚠ | 1.1% | 11.3% | 24.8% | 8.3% | 24.2%-25.4% |
| Marketing | 45.4% ⚠ | 19.0% | 48.0% | 25.1% | 8.4% | 24.6%-25.8% |
| Keuangan | 16.4% | 3.1% | 19.9% | 25.5% | 8.5% | 24.9%-26.1% |
| Akuntansi | 43.0% ⚠ | 16.1% | 49.1% | 25.2% | 8.0% | 24.6%-25.8% |
| Human Resources | 3.6% ⚠ | 0.3% | 5.8% | 25.2% | 8.6% | 24.6%-25.8% |
| Supply Chain | 7.8% ⚠ | 1.6% | 11.5% | 24.9% | 8.3% | 24.3%-25.5% |
| Legal | 4.9% ⚠ | 0.5% | 8.3% | 25.7% | 8.7% | 25.1%-26.3% |

⚠ = di luar pita toleransi.

| Varian | Bidang di luar pita | Selisih maks. dari 25% | Top-3 berisi 3 bidang tech | Top-1 seri persis |
| --- | --- | ---: | ---: | ---: |
| v1 struktur draf + normalisasi poin maks. (tie acak) | Akuntansi | 11.6 poin persen | 6.8% | 14.6% |
| v1 draf (tie-break urutan bidang) | Back-End, Mobile, Data, Product, Marketing, Akuntansi, Human Resources, Supply Chain, Legal | 28.7 poin persen | 6.2% | 26.9% |
| v1 draf (tie-break acak) | Back-End, Mobile, Data, Product, Marketing, Akuntansi, Human Resources, Supply Chain, Legal | 25.5 poin persen | 4.3% | 26.9% |
| v2 (a) tanpa aturan klaster | tidak ada | 0.7 poin persen | 1.2% | 35.4% |
| v2 (a) dengan tie-break urutan bidang | tidak ada | 9.1 poin persen | 3.2% | 35.4% |
| v2 final: (b) maks. 2 bidang per klaster kecuali selisih >= 2 poin | tidak ada | 1.0 poin persen | 0.1% | 35.4% |

Pembanding: bila top-3 diambil acak dari 12 bidang, peluang ketiganya tech = 1/220 = 0.45%.

## 2. Persona sintetis

N = 2,000 per bidang. Persona memilih opsi berbobot tertinggi untuk bidangnya dengan peluang 80%, sisanya acak; tools tidak terkait dicentang dengan peluang 15%. Target: top-3 >= 90%, top-1 >= 60%.

| Persona | v1 top-1 | v1 top-3 | v2 final top-1 | v2 final top-3 | v2 (a) top-3 | v2 + jurusan top-1 | v2 seri persis | v2 selisih <= 1 poin |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Back-End | 98.8% | 100.0% | 95.9% | 99.3% | 99.4% | 96.5% | 3.2% | 11.9% |
| Front-End | 71.9% | 99.8% | 95.5% | 99.1% | 99.1% | 97.0% | 3.4% | 10.8% |
| Mobile | 0.0% ⚠ | 96.3% | 93.6% | 99.2% | 99.3% | 94.4% | 4.2% | 13.7% |
| Data | 99.6% | 100.0% | 96.0% | 99.2% | 99.2% | 97.2% | 2.6% | 9.4% |
| UI/UX Design | 98.4% | 99.9% | 95.8% | 99.5% | 99.5% | 97.6% | 2.4% | 10.1% |
| Product | 47.3% ⚠ | 94.2% | 95.5% | 99.2% | 99.2% | 97.8% | 3.4% | 10.2% |
| Marketing | 99.1% | 99.9% | 95.9% | 99.2% | 99.2% | 97.8% | 3.2% | 10.1% |
| Keuangan | 87.8% | 99.0% | 96.0% | 99.3% | 99.3% | 98.0% | 3.5% | 11.9% |
| Akuntansi | 90.3% | 99.9% | 95.6% | 99.6% | 99.6% | 97.5% | 3.6% | 11.1% |
| Human Resources | 63.8% | 89.3% ⚠ | 95.5% | 99.2% | 99.2% | 96.7% | 3.7% | 11.1% |
| Supply Chain | 81.5% | 96.2% | 96.0% | 99.7% | 99.7% | 97.5% | 2.9% | 10.2% |
| Legal | 40.8% ⚠ | 88.2% ⚠ | 95.7% | 99.6% | 99.6% | 98.2% | 3.5% | 10.2% |

⚠ = di bawah target (top-1 < 60% atau top-3 < 90%).

v1 struktur draf + normalisasi poin maks. (tanpa merombak soal), persona: top-1 terendah 56.6%, top-3 terendah 97.6%.

Persona tech yang top-3-nya berisi 3 bidang tech:

| Persona | v1 | v2 (a) tanpa aturan | v2 final (b) |
| --- | ---: | ---: | ---: |
| Back-End | 84.2% | 59.1% | 9.0% |
| Front-End | 57.8% | 2.4% | 0.1% |
| Mobile | 92.1% | 60.6% | 36.5% |

Ketahanan terhadap noise (nilai terendah di antara 12 persona):

| eps | v1 min top-1 | v1 min top-3 | v2 min top-1 | v2 min top-3 |
| ---: | ---: | ---: | ---: | ---: |
| 0.1 | 0.0% | 94.8% | 98.8% | 99.9% |
| 0.2 | 0.0% | 87.9% | 94.5% | 99.2% |
| 0.3 | 0.0% | 80.2% | 87.4% | 96.9% |
| 0.4 | 0.0% | 68.7% | 78.0% | 92.7% |

## 3. Sensitivitas bobot (+/-1)

### v2: 144 perubahan diuji

Baseline: selisih maks. top-3 dari 25% = 1.0 poin persen; top-1 persona terendah = 94.2%.

| Perubahan | Pergeseran top-3 terbesar | Bidang | Selisih maks. dari 25% | Top-1 persona terendah |
| --- | ---: | --- | ---: | --- |
| `q6_a:backend-1 (1->0)` | 6.6 pp | Back-End | 5.6 pp | 94.2% (UI/UX Design) |
| `q2_b:backend-1 (1->0)` | 6.3 pp | Back-End | 5.4 pp | 94.2% (UI/UX Design) |
| `q5_a:backend-1 (1->0)` | 6.3 pp | Back-End | 5.3 pp | 94.2% (UI/UX Design) |
| `q2_c:frontend-1 (1->0)` | 6.2 pp | Front-End | 6.2 pp | 94.2% (UI/UX Design) |
| `q6_c:frontend-1 (1->0)` | 6.1 pp | Front-End | 6.1 pp | 94.4% (UI/UX Design) |
| `q5_c:data-1 (1->0)` | 6.0 pp | Data | 6.1 pp | 94.4% (UI/UX Design) |
| `q6_a:accounting-1 (1->0)` | 6.0 pp | Akuntansi | 5.8 pp | 94.2% (UI/UX Design) |
| `q3_b:frontend-1 (1->0)` | 6.0 pp | Front-End | 6.0 pp | 94.2% (UI/UX Design) |
| `q2_e:product-1 (1->0)` | 6.0 pp | Product | 5.6 pp | 94.2% (UI/UX Design) |
| `q1_a:data-1 (1->0)` | 6.0 pp | Data | 6.1 pp | 94.2% (UI/UX Design) |

Perubahan yang paling menurunkan top-1 persona: `q6_a:backend-1 (1->0)` -> 94.2% (UI/UX Design).

### v1: 136 perubahan diuji

Baseline: selisih maks. top-3 dari 25% = 28.9 poin persen; top-1 persona terendah = 0.0%.

| Perubahan | Pergeseran top-3 terbesar | Bidang | Selisih maks. dari 25% | Top-1 persona terendah |
| --- | ---: | --- | ---: | --- |
| `q4_code:frontend+1 (1->2)` | 15.1 pp | Front-End | 26.6 pp | 0.0% (Mobile) |
| `q4_code:mobile+1 (1->2)` | 14.2 pp | Mobile | 26.5 pp | 0.4% (Mobile) |
| `q4_acc:accounting-1 (2->1)` | 11.9 pp | Akuntansi | 30.3 pp | 0.0% (Mobile) |
| `q4_code:backend+1 (1->2)` | 11.3 pp | Back-End | 35.3 pp | 0.0% (Mobile) |
| `q4_ads:marketing+1 (2->3)` | 11.1 pp | Marketing | 30.6 pp | 0.0% (Mobile) |
| `q4_code:backend-1 (1->0)` | 10.8 pp | Back-End | 30.2 pp | 0.0% (Mobile) |
| `q4_code:frontend-1 (1->0)` | 10.8 pp | Front-End | 30.6 pp | 0.0% (Mobile) |
| `q4_ads:marketing-1 (2->1)` | 10.7 pp | Marketing | 30.1 pp | 0.0% (Mobile) |
| `q4_acc:accounting+1 (2->3)` | 10.7 pp | Akuntansi | 28.5 pp | 0.0% (Mobile) |
| `q4_excel:data-1 (1->0)` | 10.7 pp | Data | 25.1 pp | 0.0% (Mobile) |

Perubahan yang paling menurunkan top-1 persona: `q4_code:frontend+1 (1->2)` -> 0.0% (Mobile).

