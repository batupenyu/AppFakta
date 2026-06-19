# 📋 Sistem Tanda Tangan Online PDF

Sistem web berbasis Flask untuk mengumpulkan tanda tangan digital dari 50 peserta ke dalam PDF template.

---

## ⚙️ Instalasi

```bash
pip install flask pypdf reportlab pillow
```

---

## 🚀 Cara Menjalankan

### 1. Siapkan PDF Template Anda
Ganti file `template.pdf` dengan template PDF Anda sendiri.

### 2. (Opsional) Import Daftar Peserta dari CSV
```bash
python import_peserta.py daftar_peserta.csv
```
Format CSV: `Nama Lengkap,email@domain.com`

### 3. Jalankan Server
```bash
python app.py
```
Server berjalan di `http://localhost:5000`

### 4. Bagikan Link ke Peserta
Setiap peserta mendapat link unik:
```
http://localhost-atau-IP-server:5000/sign/peserta-001
http://localhost-atau-IP-server:5000/sign/peserta-002
...
```
Generate semua link sekaligus:
```bash
python generate_links.py
```

---

## 🖥️ Halaman-Halaman

| URL | Keterangan |
|-----|-----------|
| `/` | Panel admin — lihat status semua peserta |
| `/sign/<id>` | Form tanda tangan untuk peserta |
| `/download/<id>` | Download PDF yang sudah ditandatangani |
| `/api/status` | API JSON status ringkasan |

---

## 📁 Struktur File

```
pdf_signing/
├── app.py                  ← Aplikasi Flask utama
├── template.pdf            ← ⬅ Ganti dengan template PDF Anda
├── import_peserta.py       ← Import nama peserta dari CSV
├── generate_links.py       ← Generate daftar link peserta
├── status_peserta.json     ← Database status (auto-dibuat)
├── signed_pdfs/            ← PDF yang sudah ditandatangani tersimpan di sini
└── templates/
    ├── index.html          ← Halaman admin
    └── sign.html           ← Halaman tanda tangan peserta
```

---

## 🔧 Kustomisasi Posisi Tanda Tangan

Edit fungsi `fill_pdf()` di `app.py`:

```python
# Sesuaikan koordinat Y dengan template PDF Anda
field_y_positions = {
    "nama":     height - 180,   # ← ubah angka ini
    "nik":      height - 220,
    "jabatan":  height - 260,
    "instansi": height - 300,
}

# Posisi kotak tanda tangan
sig_x = width - 218
sig_y = height - 555
sig_w = 146
sig_h = 76
```

---

## 🌐 Deploy ke Server Publik

Agar peserta bisa akses dari mana saja, deploy ke:
- **VPS/Cloud**: Jalankan dengan `gunicorn` + nginx
- **Ngrok** (testing): `ngrok http 5000` → dapat URL publik sementara

```bash
# Install gunicorn
pip install gunicorn

# Jalankan production
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## 📊 Monitoring

Buka `http://localhost:5000` untuk melihat:
- Total peserta, sudah/belum tanda tangan
- Waktu masing-masing peserta menandatangani
- Tombol download PDF per peserta
- Panel auto-refresh setiap 30 detik
