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
Estimasi cicilan menggunakan anuitas dengan asumsi bunga efektif tahunan nominal 12% yang dibagi 12 untuk suku bunga bulanan, tanpa biaya tambahan
Angka 12% adalah asumsi tugas, bukan tarif produk lembaga keuangan
Istilah efektif di UI mengacu pada perhitungan bunga atas saldo berjalan, bukan bunga flat atau effective annual rate setelah pemajemukan

Nominal diproses langsung dalam rupiah, tanpa konversi dolar
Model tidak menggunakan gender, status pernikahan, pendidikan, atau lokasi tempat tinggal
Data formulir tidak disimpan ke database atau penyimpanan browser

## Model dan data

Model aktif dilatih dari awal menggunakan 20.000 profil sintetis dengan satuan rupiah
Tidak ada data pelanggan, histori persetujuan, atau pembayaran peminjam Indonesia dalam dataset ini
Label merupakan hasil mekanisme hipotetis pada `train_model.py`, bukan keputusan lembaga keuangan

Random Forest dilatih dengan 12.000 baris, lalu dikalibrasi dengan metode sigmoid memakai 4.000 baris terpisah
Evaluasi dilakukan pada 4.000 baris uji yang tidak dipakai untuk pelatihan atau kalibrasi
Split dan generator memakai seed 42 agar hasil dapat direproduksi

Lihat [MODEL_CARD.md](MODEL_CARD.md) untuk asumsi, hasil evaluasi, dan batas pemakaian
Metrik dataset sintetis tidak membuktikan akurasi atau kalibrasi pada peminjam Indonesia nyata
Kalibrasi di sini hanya berlaku terhadap mekanisme pembentukan label sintetis

## Melatih ulang dan menguji

```sh
python train_model.py
python -m unittest discover -s tests -v
```

Pelatihan menulis ulang `model.pkl`, `model_metadata.json`, dan `Dataset/kreditly_synthetic_idr.csv`
Kolom `Split` mencatat pembagian train, calibration, dan test
Tes route memakai model terlatih yang sebenarnya, termasuk kasus layak dan belum layak, validasi, kontrak fitur, perhitungan keuangan, serta pemisahan data

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
