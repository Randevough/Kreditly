# Kreditly

Loan Eligibility Prediction App berbahasa Indonesia untuk tugas pengembangan model dan aplikasi web
Kreditly menilai profil pinjaman pribadi untuk karyawan dan pekerja mandiri menggunakan nominal rupiah penuh

## Menjalankan

Gunakan Python 3.12 dan lingkungan virtual terpisah

```sh
git clone https://github.com/Randevough/Kreditly.git
cd Kreditly
python -m venv .venv
```

Windows: `.venv\Scripts\activate`
macOS/Linux: `source .venv/bin/activate`

```sh
python -m pip install -r requirements.txt
python app.py
```

Buka <http://127.0.0.1:5000/>
Model baru sudah disertakan sehingga pelatihan ulang tidak diperlukan untuk menjalankan aplikasi

## Input dan hasil

Semua nominal diisi dalam rupiah penuh dan diformat otomatis saat diketik
Contoh `8000000` tampil sebagai `8.000.000`
Input salin-tempel seperti `Rp 8.000.000` juga didukung
Angka desimal, nilai negatif, dan susunan pemisah yang tidak valid ditolak di browser serta server

- Penghasilan pemohon Rp2 juta sampai Rp40 juta per bulan
- Penghasilan pendamping Rp0 sampai Rp15 juta per bulan
- Cicilan berjalan Rp0 sampai Rp20 juta per bulan
- Biaya hidup Rp0 sampai Rp40 juta per bulan
- Jumlah pinjaman Rp1 juta sampai Rp500 juta
- Tenor 6, 12, 18, 24, 36, 48, atau 60 bulan
- Riwayat kredit lancar, pernah menunggak, atau belum punya riwayat

Hasil berupa prediksi layak atau belum layak, estimasi cicilan, rasio seluruh cicilan terhadap penghasilan, dan sisa penghasilan setelah kebutuhan serta cicilan
Estimasi cicilan menggunakan anuitas atas sisa pokok dengan cicilan tetap, tanpa biaya tambahan
Bunga dapat diubah dari 0 sampai 3% per bulan dengan nilai awal 1%, maksimal dua angka desimal
Input `0,75` atau `0.75` berarti bunga 0,75% per bulan, bukan 75%
Bunga 0% dihitung sebagai pokok dibagi tenor, dengan total bunga nol
Rentang 0–3% adalah batas input aplikasi, bukan batas regulasi atau rekomendasi tarif
Bunga tersebut merupakan asumsi tugas, bukan tarif produk lembaga keuangan

Nominal diproses langsung dalam rupiah, tanpa konversi dolar
Model tidak menggunakan gender, status pernikahan, pendidikan, atau lokasi tempat tinggal
Data formulir tidak disimpan ke database atau penyimpanan browser

## Perkiraan nominal dan rincian biaya

Perkiraan nominal adalah perhitungan anggaran yang terpisah dari prediksi classifier
Asumsi tugas: seluruh cicilan maksimal 40% penghasilan gabungan dan sisa setelah biaya hidup serta cicilan minimal 15% penghasilan
Ruang cicilan baru adalah nilai terkecil dari dua batas berikut, dengan minimum nol

- `40% × penghasilan − cicilan berjalan`
- `penghasilan − biaya hidup − cicilan berjalan − 15% × penghasilan`

Ruang cicilan dikonversi menjadi pokok pinjaman melalui invers rumus anuitas pada tenor yang dipilih
Nominal dibulatkan turun ke kelipatan Rp100.000 dan dibatasi pada rentang Rp1 juta sampai Rp500 juta
Jika tidak ada nominal dalam rentang tersebut, aplikasi tidak menawarkan tombol penggunaan nominal
Perkiraan ini bukan limit atau jaminan persetujuan lembaga keuangan

Rincian biaya memisahkan pokok pinjaman, total bunga, dan total pokok + bunga
Administrasi, provisi, asuransi, dan biaya lain ditulis belum diperhitungkan karena tidak ada tarif pemberi pinjaman yang terhubung
Penjelasan hasil merangkum sisa anggaran, rasio cicilan, dan riwayat yang dimasukkan tanpa mengklaim sebagai penjelasan sebab akibat classifier

## Untuk presentasi

Tiga contoh profil tersedia di formulir: pengeluaran terjaga, cicilan tinggi, dan riwayat kredit baru
Halaman hasil menampilkan alokasi penghasilan dan perbandingan nominal serta tenor
Setiap alternatif memakai classifier dan bunga pilihan yang sama dan dapat dimuat kembali ke formulir
Lihat [PRESENTATION.md](PRESENTATION.md) untuk urutan demo dan penjelasan metode

## Model dan data

Model aktif dilatih dari awal menggunakan 20.000 profil sintetis dengan satuan rupiah
Tidak ada data pelanggan, histori persetujuan, atau pembayaran peminjam Indonesia dalam dataset ini
Label merupakan hasil mekanisme hipotetis pada `train_model.py`, bukan keputusan lembaga keuangan

Empat kandidat dibandingkan: Logistic Regression dan Random Forest dengan batas arah monoton, masing-masing dengan dan tanpa kalibrasi sigmoid
Pembagian data: 12.000 train, 2.000 calibration, 2.000 validation, dan 4.000 test
Model dipilih berdasarkan log loss pada validation, bukan angka test
Model terpilih adalah Logistic Regression dengan kalibrasi sigmoid
Audit tambahan dilakukan pada 5.000 profil baru dari seed 2026 setelah pemilihan model
Generator dan pembagian utama memakai seed 42

Lihat [MODEL_CARD.md](MODEL_CARD.md) untuk asumsi, hasil evaluasi, dan batas pemakaian
Metrik dataset sintetis tidak membuktikan akurasi atau kalibrasi pada peminjam Indonesia nyata
Kalibrasi di sini hanya berlaku terhadap mekanisme pembentukan label sintetis

## Bunga custom dan model

Bunga pilihan digunakan bersama oleh ringkasan browser, server, rincian biaya, perkiraan kemampuan bayar, dan semua alternatif rencana
Model tetap memakai empat fitur yang sama, bunga memengaruhi prediksi melalui rasio cicilan dan sisa penghasilan
Artifact model tidak dilatih ulang untuk fitur ini, data pelatihan dan metrik evaluasi tetap memakai asumsi awal 1% per bulan
Pengujian memeriksa 168 kombinasi bunga, tenor, dan riwayat kredit agar kenaikan bunga tidak meningkatkan skor kelayakan atau kemampuan pinjam
Kesamaan fitur pada beban cicilan yang sama diperiksa terhadap perhitungan bunga awal
Pemeriksaan tersebut membuktikan konsistensi perhitungan dan arah model, bukan akurasi atau kalibrasi pada bunga lain maupun peminjam nyata

## Melatih ulang dan menguji

```sh
python train_model.py
python -m unittest discover -s tests -v
```

Tes format rupiah dan kalkulator browser memakai Node.js tanpa paket tambahan

```sh
node --test tests/money.test.mjs
```

Pelatihan menulis ulang `model.pkl`, `model_metadata.json`, `Dataset/kreditly_synthetic_idr.csv`, dan `MODEL_CARD.md`
Kolom `Split` mencatat pembagian train, calibration, validation, dan test
Tes route memakai model terlatih yang sebenarnya, termasuk kasus layak dan belum layak, validasi, kontrak fitur, perhitungan keuangan, pemisahan data, arah hasil keuangan, dan perbandingan rencana

Gunakan versi scikit-learn yang sama dengan `requirements.txt` karena format pickle sensitif terhadap versi
Muat hanya artifact pickle yang dipercaya

## Struktur

- `app.py`: route, validasi input, dan hasil penilaian
- `loan_model.py`: kontrak fitur, batas input, dan perhitungan keuangan bersama
- `train_model.py`: pembentukan data, pelatihan, kalibrasi, dan evaluasi
- `model.pkl`: model rupiah aktif dan metadata kontraknya
- `model_metadata.json`: hasil evaluasi serta identitas model yang dapat dibaca
- `Dataset/kreditly_synthetic_idr.csv`: dataset tugas dengan sumber sintetis
- `legacy/`: dataset dan notebook upstream yang disimpan sebagai arsip, tidak dipakai model aktif
- `templates/`, `static/`: antarmuka dan interaksi
- `tests/`: pemeriksaan model dan aplikasi

## Lisensi dan atribusi

Aplikasi dikembangkan dari [Loan Eligibility Prediction Web App](https://github.com/MohamedKhalidLx/Loan-Eligibility-Prediction-Web-App) oleh MohamedKhalidLx
Antarmuka, alur, dan model IDR dikembangkan lebih lanjut untuk Kreditly
Copyright dan lisensi MIT kode asal dipertahankan di [LICENSE](LICENSE)
