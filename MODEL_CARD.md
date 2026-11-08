# Model Card: Kreditly IDR

## Tujuan

Model klasifikasi kelayakan pinjaman pribadi berformat rupiah untuk tugas
Versi `kreditly-idr-synthetic-v1` menggunakan Random Forest dan kalibrasi sigmoid
Keputusan aplikasi memakai ambang probabilitas 0,5 tanpa menampilkan probabilitas sebagai peluang persetujuan nyata

## Asal data

Seluruh 20,000 baris berasal dari generator sintetis seed 42
Distribusi penghasilan, nominal, biaya, dan riwayat kredit dipilih untuk membentuk contoh pembelajaran, bukan diestimasi dari populasi Indonesia
Tidak ada data observasi peminjam atau hubungan dengan pemberi pinjaman

Label `Eligible` diambil dari distribusi Bernoulli dengan probabilitas logistik hipotetis
Logit menggabungkan rasio cicilan terhadap penghasilan, sisa penghasilan relatif, dan kategori riwayat kredit
Koefisien, batas rasio 40%, penyangga sisa 15%, dan efek kategori kredit merupakan asumsi penulis untuk tugas, bukan kebijakan regulator atau lembaga keuangan
Kode lengkap mekanisme label tersedia di `generate_data` dalam `train_model.py`

## Kontrak fitur

Sembilan fitur dipakai dalam urutan yang sama saat training dan inference

| Fitur | Satuan |
| --- | --- |
| Penghasilan gabungan | Rupiah per bulan |
| Cicilan berjalan | Rupiah per bulan |
| Biaya hidup | Rupiah per bulan |
| Jumlah pinjaman | Rupiah |
| Tenor | Bulan |
| Riwayat kredit | 0 menunggak, 1 lancar, 2 belum punya riwayat |
| Estimasi cicilan baru | Rupiah per bulan |
| Rasio seluruh cicilan terhadap penghasilan | Pecahan |
| Sisa penghasilan setelah biaya dan cicilan | Rupiah per bulan |

Cicilan anuitas memakai suku bunga bulanan 0,01 sebagai asumsi tugas
Data yang digunakan tidak mencakup biaya administrasi, asuransi, agunan, atau histori pembayaran rinci

## Pembagian dan evaluasi

Training 12.000 baris, kalibrasi 4.000 baris, test 4.000 baris
Model dasar dibekukan sebelum kalibrasi sehingga tidak dilatih ulang dengan data kalibrasi
Data test hanya dipakai untuk menghitung hasil evaluasi setelah pipeline ditetapkan

| Metrik pada test sintetis | Model dasar | Setelah kalibrasi sigmoid |
| --- | ---: | ---: |
| Akurasi | 0.94050 | 0.94025 |
| Precision kelas layak | 0.89693 | 0.90161 |
| Recall kelas layak | 0.87103 | 0.86429 |
| ROC AUC | 0.98208 | 0.98208 |
| Brier score | 0.04555 | 0.04575 |
| Log loss | 0.15554 | 0.15931 |

Pada split ini kalibrasi sigmoid tidak memperbaiki Brier score atau log loss dibanding model dasar
Tahap kalibrasi tetap didokumentasikan sebagai eksperimen, tanpa klaim bahwa hasilnya membaik
Matriks kebingungan model terkalibrasi adalah TN=2863, FP=98, FN=141, TP=898
Kurva kalibrasi per kelompok probabilitas tersedia di `model_metadata.json`

## Batas interpretasi

Akurasi 94.025% hanya mengukur kesesuaian model dengan label hipotetis generator
Nilai ini bukan estimasi performa pada aplikasi kredit nyata di Indonesia
Konversi ke rupiah dan pemilihan kisaran nominal tidak menjadikan model terkalibrasi pada populasi Indonesia
Input di luar rentang aplikasi ditolak, tetapi rentang tersebut pun tidak menjamin representativitas

Validasi nyata memerlukan data berizin dengan definisi label, periode pengamatan, dan hasil pinjaman yang jelas
Sesudah tersedia, evaluasi harus mencakup pemisahan waktu dan peminjam, kalibrasi di data terpisah, pemeriksaan kesalahan antarkelompok, dan pemantauan perubahan distribusi

## Reproduksi

Gunakan Python 3.12 dan versi dependensi pada `requirements.txt`
Jalankan `python train_model.py` kemudian `python -m unittest discover -s tests -v`
Arsip upstream pada `legacy/` tidak digunakan untuk melatih model aktif

Metode kalibrasi mengikuti API resmi scikit-learn
[Probability calibration](https://scikit-learn.org/stable/modules/calibration.html)
