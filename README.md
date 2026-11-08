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

Semua nominal diisi langsung dalam rupiah penuh tanpa pemisah angka
Contoh `8000000` berarti Rp8 juta

- Penghasilan pemohon Rp2 juta sampai Rp40 juta per bulan
- Penghasilan pendamping Rp0 sampai Rp15 juta per bulan
- Cicilan berjalan Rp0 sampai Rp20 juta per bulan
- Biaya hidup Rp0 sampai Rp40 juta per bulan
- Jumlah pinjaman Rp1 juta sampai Rp500 juta
- Tenor 6, 12, 18, 24, 36, 48, atau 60 bulan
- Riwayat kredit lancar, pernah menunggak, atau belum punya riwayat

Hasil berupa prediksi layak atau belum layak, estimasi cicilan, rasio seluruh cicilan terhadap penghasilan, dan sisa penghasilan setelah kebutuhan serta cicilan
Estimasi cicilan menggunakan anuitas dengan asumsi bunga 1% per bulan atas saldo berjalan, tanpa biaya tambahan
Bunga tersebut merupakan asumsi tugas, bukan tarif produk lembaga keuangan

Nominal diproses langsung dalam rupiah, tanpa konversi dolar
Model tidak menggunakan gender, status pernikahan, pendidikan, atau lokasi tempat tinggal
Data formulir tidak disimpan ke database atau penyimpanan browser

## Untuk presentasi

Tiga contoh profil tersedia di formulir: pengeluaran terjaga, cicilan tinggi, dan riwayat kredit baru
Halaman hasil menampilkan alokasi penghasilan dan perbandingan nominal serta tenor
Setiap alternatif memakai classifier yang sama dan dapat dimuat kembali ke formulir
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

## Melatih ulang dan menguji

```sh
python train_model.py
python -m unittest discover -s tests -v
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
