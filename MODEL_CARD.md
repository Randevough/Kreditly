# Model Card: Kreditly IDR v2

## Tujuan dan asal data

Model penilaian pinjaman pribadi untuk tugas, seluruh nominal menggunakan rupiah
Versi `kreditly-idr-synthetic-v2` memakai `logistic_regression_sigmoid`
Semua 20.000 profil dan label berasal dari generator sintetis seed 42
Tidak ada data peminjam Indonesia nyata atau kebijakan pemberi pinjaman dalam dataset

Label diambil dari distribusi Bernoulli dengan probabilitas logistik hipotetis
Rasio cicilan, sisa penghasilan relatif, dan riwayat kredit membentuk probabilitas generator
Batas acuan 40%, penyangga sisa 15%, dan koefisien pada generator adalah asumsi tugas
Pemilihan fitur mengikuti mekanisme label sintetis yang diketahui, sehingga model linear logistik cocok untuk data ini
Hasil ini tidak membuktikan bahwa hubungan yang sama berlaku di dunia nyata

## Fitur dan konsistensi

| Fitur model | Definisi |
| --- | --- |
| DebtToIncomeRatio | Seluruh cicilan dibagi penghasilan gabungan |
| DisposableIncomeShare | Sisa setelah biaya hidup dan cicilan dibagi penghasilan gabungan |
| CreditArrears | 1 jika pernah menunggak, selain itu 0 |
| CreditHistoryClear | 1 jika riwayat lancar, selain itu 0 |

Riwayat baru diwakili oleh kedua indikator kredit bernilai 0
Penghasilan dan nominal mentah tetap diperlukan untuk menghitung cicilan dan rasio
Gender, pernikahan, pendidikan, dan lokasi tidak digunakan
Bunga 1% per bulan atas saldo berjalan merupakan asumsi tugas, tanpa biaya lain

Arah model diperiksa agar peningkatan pinjaman, cicilan lain, atau biaya hidup tidak meningkatkan skor kelayakan
Peningkatan penghasilan atau tenor tidak menurunkan skor dalam kondisi input lainnya tetap
Tenor lebih panjang menambah total pembayaran walaupun cicilan bulanan turun
Pemeriksaan ini adalah kontrak perilaku untuk mekanisme tugas, bukan rekomendasi kebijakan kredit

## Pembagian dan pemilihan model

Train 12.000, calibration 2.000, validation 2.000, test 4.000
Model dasar dilatih pada train saja, calibrator sigmoid memakai calibration saja
Empat kandidat dibandingkan dengan log loss pada validation
Test tidak dipakai untuk memilih kandidat atau ambang klasifikasi
Split test yang sama pernah dipakai mengevaluasi v1 sehingga perbandingan antaversi bersifat berulang
Sesudah pemilihan, audit tambahan memakai 5.000 profil baru dari seed 2026
Audit tidak digunakan untuk memilih atau menyesuaikan model

| Kandidat pada validation | Akurasi | Brier score | Log loss | Pilihan |
| --- | ---: | ---: | ---: | --- |
| logistic_regression | 0.93800 | 0.04370 | 0.14020 |  |
| logistic_regression_sigmoid | 0.93750 | 0.04368 | 0.13972 | Dipilih |
| random_forest_monotonic | 0.91750 | 0.06832 | 0.22989 |  |
| random_forest_monotonic_sigmoid | 0.91800 | 0.06257 | 0.20494 |  |

## Evaluasi model terpilih

| Metrik | Test 4.000 | Audit 5.000 |
| --- | ---: | ---: |
| Akurasi | 0.94525 | 0.94020 |
| Precision layak | 0.90196 | 0.88533 |
| Recall layak | 0.88547 | 0.89130 |
| ROC AUC | 0.98641 | 0.98361 |
| Brier score | 0.03996 | 0.04419 |
| Log loss | 0.13113 | 0.14481 |

Baseline yang selalu memilih kelas mayoritas mendapat akurasi 74.025% pada test
Matriks kebingungan test dalam urutan TN, FP, FN, TP: 2861, 100, 119, 920
Kurva kalibrasi disimpan dalam metadata, Brier score sendiri bukan ukuran kalibrasi murni
Ambang keputusan tetap 0,5 dan probabilitas tidak ditampilkan sebagai peluang persetujuan nyata

## Batasan dan reproduksi

Semua metrik hanya mengukur kesesuaian pada label hipotetis sintetis
Kalibrasi terhadap label sintetis bukan kalibrasi pada peminjam Indonesia
Indikator keuangan di UI adalah ringkasan input, bukan atribusi sebab akibat dari classifier
Rencana alternatif dihitung ulang memakai model yang sama, perubahan nominal atau tenor tidak menjamin persetujuan
Data observasi berizin dan evaluasi terpisah menurut waktu serta peminjam tetap diperlukan untuk pemakaian nyata

Gunakan Python 3.12 dan versi dependensi pada requirements.txt
Jalankan `python train_model.py` untuk membuat model, dataset, metadata, dan laporan ini
Jalankan `python -m unittest discover -s tests -v` untuk memeriksa aplikasi dan kontrak perilaku

Referensi API: [Logistic Regression](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LogisticRegression.html), [Random Forest](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.RandomForestClassifier.html), [Probability calibration](https://scikit-learn.org/stable/modules/calibration.html)
