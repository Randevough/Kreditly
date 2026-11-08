# Panduan presentasi Kreditly

## Pembukaan

Kreditly memprediksi kelayakan pinjaman dari profil keuangan dalam rupiah
Proyek ini memakai data sintetis untuk mempelajari klasifikasi dan kemampuan membayar
Dataset bukan data peminjam nyata dan hasil bukan persetujuan lembaga keuangan

## Urutan demo

1) Pilih contoh Pengeluaran terjaga lalu kirim penilaian
2) Jelaskan cicilan bulanan, rasio seluruh cicilan, dan sisa penghasilan
3) Buka perbandingan tenor lalu tunjukkan cicilan turun tetapi total pembayaran naik
4) Klik Coba rencana untuk memuat alternatif ke formulir dan nilai ulang
5) Pilih Cicilan tinggi untuk menunjukkan hasil belum layak walaupun riwayat kredit lancar
6) Pilih Riwayat kredit baru untuk menunjukkan belum punya riwayat tidak otomatis ditolak

## Hasil contoh yang dihitung oleh model aktif

| Profil | Penghasilan gabungan | Cicilan baru / bulan | Rasio seluruh cicilan | Sisa setelah biaya | Prediksi |
| --- | ---: | ---: | ---: | ---: | --- |
| Pengeluaran terjaga | Rp10.000.000 | Rp1.660.715 | 21,6% | Rp4.339.285 | Layak |
| Cicilan tinggi | Rp5.000.000 | Rp3.321.431 | 96,4% | -Rp2.821.431 | Belum layak |
| Riwayat kredit baru | Rp6.000.000 | Rp1.882.939 | 36,4% | Rp1.317.061 | Layak |

Nominal pada tabel dibulatkan ke rupiah, rasio ditulis satu desimal
Bunga 1% per bulan merupakan asumsi proyek
Rasio dan sisa penghasilan adalah indikator perhitungan, bukan bukti sebab akibat dari model

## Cara menjelaskan metode

Empat fitur akhir terdiri dari rasio cicilan, rasio sisa penghasilan, indikator pernah menunggak, dan indikator pembayaran lancar
Fitur relatif menghindari ketergantungan langsung pada besar nominal rupiah
Riwayat baru memakai kedua indikator kredit bernilai 0
Gender dan status pernikahan tidak digunakan

Label sintetis dibuat dengan mekanisme logistik yang mempertimbangkan kemampuan membayar dan riwayat kredit
Karena mekanismenya diketahui, Logistic Regression cocok untuk mempelajari hubungan tersebut
Kami membandingkannya dengan Random Forest dan varian kalibrasi sebelum memilih model

Train 12.000, calibration 2.000, validation 2.000, test 4.000
Pemilihan memakai log loss validation agar bukan sekadar mencari akurasi test tertinggi
Setelah terpilih, model diaudit pada 5.000 profil baru dari seed berbeda

## Angka evaluasi yang dapat disebut

- Model terpilih `logistic_regression_sigmoid`
- Akurasi test sintetis 94.525%
- Akurasi audit sintetis baru 94.020%
- Baseline kelas mayoritas pada test 74.025%
- Brier score test 0.03996
- Log loss test 0.13113

Pada split test yang sama, v1 memiliki akurasi 94,025% dan Brier score 0,04575
Peningkatan v2 terbatas pada eksperimen data sintetis, bukan klaim akurasi kredit Indonesia
Jangan menyebut skor ini sebagai peluang persetujuan bank atau akurasi pada nasabah nyata

## Jika ditanya kenapa memakai data sintetis

Belum tersedia data pinjaman lokal berizin untuk proyek ini
Data sintetis membuat alur pelatihan, pemisahan data, pengujian arah hasil, serta antarmuka dapat didemonstrasikan
Langkah berikutnya adalah validasi pada data observasi dengan definisi label dan periode pengamatan yang jelas

## Berkas yang bisa diperlihatkan

`train_model.py` untuk pembentukan data dan pemilihan kandidat
`model_metadata.json` untuk angka validasi, test, audit, dan kurva kalibrasi
`MODEL_CARD.md` untuk asumsi dan batasan
`tests/test_app.py` untuk pengujian aplikasi serta arah perubahan hasil

## Demo fitur untuk pengguna awam

Ketik `8000000` di penghasilan lalu tunjukkan format otomatis `8.000.000`
Salin-tempel `Rp 8.000.000` untuk menunjukkan parser tidak mengubah satuan
Buka rincian biaya untuk memisahkan pokok, bunga, dan biaya lain yang belum diketahui
Tunjukkan bagian Apa artinya buatmu untuk menjelaskan sisa anggaran dan rasio cicilan
Pada contoh Pengeluaran terjaga tenor 36 bulan, perkiraan nominal anggaran adalah Rp105.300.000 dengan ruang cicilan baru Rp3.500.000 per bulan
Gunakan tombol Coba nominal ini untuk memuat nilainya ke formulir sebelum menilai ulang
Jelaskan bahwa perhitungan memakai asumsi 40% batas seluruh cicilan dan 15% sisa penghasilan, bukan limit persetujuan bank
Pada contoh Cicilan tinggi, aplikasi tidak menawarkan nominal baru karena ruang anggaran tidak mencukupi
