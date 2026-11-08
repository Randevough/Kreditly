# Kreditly

Kreditly adalah aplikasi Flask berbahasa Indonesia untuk mengeksplorasi prediksi kelayakan pinjaman. Isi profil, tinjau gambaran pinjaman, lalu pelajari hasil model dalam satu alur sederhana.

## Fitur

- Antarmuka responsif dengan tema hijau, navigasi keyboard, dan label formulir yang jelas.
- Contoh pengisian, indikator kelengkapan, dan ringkasan pinjaman langsung.
- Validasi server yang mempertahankan data saat terjadi kesalahan.
- Halaman hasil dengan pilihan mengubah data atau memulai simulasi baru.
- Tidak menyimpan data formulir ke database atau penyimpanan browser.

## Menjalankan

Gunakan **Python 3.11**. Model bawaan membutuhkan **scikit-learn 1.2.1** dan **numpy < 2**; gunakan lingkungan virtual terpisah.

```sh
git clone https://github.com/Randevough/Kreditly.git
cd Kreditly
python -m venv .venv
```

Aktifkan lingkungan di Windows dengan `.venv\Scripts\activate`, atau di macOS/Linux dengan `source .venv/bin/activate`.

```sh
python -m pip install -r requirements.txt
python app.py
```

Buka <http://127.0.0.1:5000/>. Server lokal berjalan tanpa debug.

## Satuan dan batasan

Penghasilan menggunakan **USD per bulan**. Jumlah pinjaman menggunakan **ribuan USD**: angka `120` berarti **US$120.000**. Ringkasan pokok bulanan membagi jumlah pinjaman dengan tenor; bunga dan biaya belum termasuk.

Hasil merupakan simulasi pembelajaran, bukan persetujuan atau penawaran kredit. Model RandomForestClassifier bawaan belum dikalibrasi untuk Indonesia dan menggunakan atribut demografis dari dataset aslinya. Urutan 16 fitur serta satuan input model dipertahankan.

## Struktur

- `app.py`: route Flask, validasi, dan pemanggilan model.
- `templates/`: kerangka bersama, formulir, dan halaman hasil.
- `static/`: gaya responsif dan interaksi formulir.
- `Dataset/`, notebook, `model.pkl`: dataset, proses pelatihan, dan model bawaan.
- `tests/`: tes route dan validasi menggunakan model pengganti; tidak mengukur akurasi model.

## Pengujian

```sh
python -m unittest discover -s tests -v
```

Tes memakai model pengganti agar kontrak input dan alur formulir bisa diperiksa secara terpisah. Untuk menjalankan model asli, gunakan versi Python dan dependensi di atas. Muat hanya berkas pickle yang dipercaya.

## Lisensi dan atribusi

Dikembangkan dari [Loan Eligibility Prediction Web App](https://github.com/MohamedKhalidLx/Loan-Eligibility-Prediction-Web-App) oleh MohamedKhalidLx. Antarmuka dan alur Kreditly dikembangkan lebih lanjut. Copyright dan ketentuan MIT kode asal dipertahankan di [LICENSE](LICENSE).
