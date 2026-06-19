"""
Generate link tanda tangan publik
Link ini bisa dibagikan ke siapa saja untuk mengisi dan menandatangani dokumen
Tidak ada batas jumlah peserta
"""
import webbrowser
import os

BASE_URL = os.environ.get("APP_URL", "http://localhost:5000")
PUBLIC_LINK = f"{BASE_URL}/sign"

def generate_public_link(output_file="link_publik.txt"):
    content = f"""========================================
   LINK TANDA TANGAN PUBLIK
========================================

Link: {PUBLIC_LINK}

Cara pakai:
1. Bagikan link di atas ke peserta via email, WhatsApp, dll
2. Peserta buka link, isi data diri dan tanda tangan
3. PDF otomatis ter-generate dan bisa didownload
4. Tidak ada batas jumlah peserta!

========================================
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(content)
    print(f"✅ Link disimpan di: {output_file}")

if __name__ == "__main__":
    generate_public_link()
    webbrowser.open(PUBLIC_LINK)
