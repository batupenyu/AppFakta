"""
Import daftar peserta dari file CSV
Format CSV: nama,email (opsional)

Contoh isi file peserta.csv:
  Ahmad Fauzi,ahmad@email.com
  Siti Rahayu,siti@email.com
  ...
"""
import csv
import json
import os

STATUS_FILE = "status_peserta.json"

def import_from_csv(csv_file: str):
    """Import nama peserta dari file CSV ke sistem"""
    
    if not os.path.exists(csv_file):
        print(f"❌ File {csv_file} tidak ditemukan!")
        return

    peserta_db = {}
    
    with open(csv_file, encoding="utf-8") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader, start=1):
            if not row:
                continue
            nama  = row[0].strip()
            email = row[1].strip() if len(row) > 1 else ""
            pid   = f"peserta-{i:03d}"
            
            peserta_db[pid] = {
                "id":     pid,
                "nama":   nama,
                "email":  email,
                "status": "belum",
                "file":   None,
                "waktu":  None,
            }

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(peserta_db, f, indent=2, ensure_ascii=False)

    print(f"✅ {len(peserta_db)} peserta berhasil diimport dari {csv_file}")
    print(f"   Data tersimpan di {STATUS_FILE}")


def show_sample_csv():
    """Buat file CSV contoh"""
    sample = """Ahmad Fauzi,ahmad.fauzi@email.com
Siti Rahayu,siti.rahayu@email.com
Budi Santoso,budi@email.com
Dewi Lestari,dewi@email.com
Eko Prasetyo,eko@email.com
"""
    with open("peserta_contoh.csv", "w") as f:
        f.write(sample)
    print("✅ File contoh dibuat: peserta_contoh.csv")
    print("   Edit file tersebut, lalu jalankan:")
    print("   python import_peserta.py peserta_contoh.csv")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        import_from_csv(sys.argv[1])
    else:
        print("Penggunaan: python import_peserta.py <file.csv>")
        print()
        show_sample_csv()
