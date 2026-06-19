"""
Sistem Tanda Tangan Online PDF
Link publik - siapa saja bisa menandatangani
"""

import os
import json
import base64
import uuid
from datetime import datetime
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_file, abort, redirect, url_for
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ganti-dengan-secret-key-anda'
app.config['SIGNED_DIR'] = '/tmp/signed_pdfs' if os.path.exists('/tmp') else 'signed_pdfs'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
CORS(app)

SUBMISSIONS_FILE = "/tmp/submissions.json" if os.path.exists('/tmp') else "submissions.json"


def load_submissions():
    if os.path.exists(SUBMISSIONS_FILE):
        with open(SUBMISSIONS_FILE) as f:
            return json.load(f)
    return []


def save_submissions(data):
    with open(SUBMISSIONS_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


submissions = load_submissions()


def get_next_id():
    if not submissions:
        return "sub-001"
    last_id = submissions[-1]["id"]
    num = int(last_id.split("-")[-1]) + 1
    return f"sub-{num:03d}"


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.route("/")
def index():
    """Halaman admin - monitor semua penandatanganan"""
    public_link = request.url_root.rstrip('/') + '/sign'
    return render_template("index.html", submissions=submissions, public_link=public_link)


@app.route("/sign")
def sign_page():
    """Halaman tanda tangan publik - bisa diakses siapa saja"""
    return render_template("sign.html")


@app.route("/do/submit", methods=["POST"])
def submit_signature():
    """
    Terima data dari form:
    - nama, nik, jabatan, instansi (teks)
    - signature_data (base64 PNG dari canvas)
    """
    data = request.get_json()
    nama     = data.get("nama", "").strip()
    nik      = data.get("nik", "").strip()
    jabatan  = data.get("jabatan", "").strip()
    instansi = data.get("instansi", "").strip()
    sig_data = data.get("signature_data", "")

    if not all([nama, nik, sig_data]):
        return jsonify({"error": "Data tidak lengkap"}), 400

    try:
        sig_bytes = base64.b64decode(sig_data.split(",")[1])
    except Exception:
        return jsonify({"error": "Format tanda tangan tidak valid"}), 400

    sub_id = get_next_id()
    sig_b64 = sig_data.split(",")[1] if "," in sig_data else ""

    output_path = os.path.join(
        app.config['SIGNED_DIR'],
        f"{sub_id}_{nama.replace(' ', '_')}.pdf"
    )

    try:
        fill_pdf(
            output_path=output_path,
            nama=nama,
            nik=nik,
            jabatan=jabatan,
            instansi=instansi,
            signature_bytes=sig_bytes,
        )
    except Exception as e:
        return jsonify({"error": f"Gagal membuat PDF: {str(e)}"}), 500

    submission = {
        "id": sub_id,
        "nama": nama,
        "nik": nik,
        "jabatan": jabatan,
        "instansi": instansi,
        "status": "sudah",
        "file": output_path,
        "waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "signature_data": sig_b64,
    }
    submissions.append(submission)
    save_submissions(submissions)

    return jsonify({
        "success": True,
        "message": "Dokumen berhasil ditandatangani!",
        "id": sub_id,
    })


@app.route("/download/<sub_id>")
def download_pdf(sub_id):
    """Download PDF yang sudah ditandatangani"""
    sub = next((s for s in submissions if s["id"] == sub_id), None)
    if not sub or sub["status"] != "sudah" or not sub["file"]:
        abort(404)
    return send_file(
        sub["file"],
        as_attachment=True,
        download_name=f"pakta_integritas_{sub['nama'].replace(' ', '_')}.pdf"
    )


@app.route("/do/delete/<sub_id>", methods=["DELETE"])
def delete_submission(sub_id):
    global submissions
    sub = next((s for s in submissions if s["id"] == sub_id), None)
    if not sub:
        return jsonify({"error": "Data tidak ditemukan"}), 404

    if sub["status"] == "sudah" and sub.get("file"):
        try:
            os.remove(sub["file"])
        except OSError:
            pass

    submissions = [s for s in submissions if s["id"] != sub_id]
    save_submissions(submissions)

    return jsonify({"success": True})


@app.route("/do/edit/<sub_id>", methods=["PUT"])
def edit_submission(sub_id):
    global submissions
    sub = next((s for s in submissions if s["id"] == sub_id), None)
    if not sub:
        return jsonify({"error": "Data tidak ditemukan"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Data tidak valid"}), 400

    nama    = data.get("nama", "").strip()
    nik     = data.get("nik", "").strip()
    jabatan = data.get("jabatan", "").strip()
    instansi = data.get("instansi", "").strip()
    sig_data = data.get("signature_data", "")

    if not all([nama, nik]):
        return jsonify({"error": "Nama dan NIK/NIP wajib diisi"}), 400

    if sig_data:
        try:
            sig_bytes = base64.b64decode(sig_data.split(",")[1])
        except Exception:
            return jsonify({"error": "Format tanda tangan tidak valid"}), 400
    else:
        old_sig_b64 = sub.get("signature_data", "")
        if old_sig_b64:
            try:
                sig_bytes = base64.b64decode(old_sig_b64)
            except Exception:
                sig_bytes = b""
        else:
            sig_bytes = b""

    output_path = os.path.join(
        app.config['SIGNED_DIR'],
        f"{sub_id}_{nama.replace(' ', '_')}.pdf"
    )

    if sub.get("file") and sub["file"] != output_path:
        try:
            os.remove(sub["file"])
        except OSError:
            pass

    try:
        fill_pdf(
            output_path=output_path,
            nama=nama,
            nik=nik,
            jabatan=jabatan,
            instansi=instansi,
            signature_bytes=sig_bytes,
        )
    except Exception as e:
        return jsonify({"error": f"Gagal memperbarui PDF: {str(e)}"}), 500

    sub["nama"]     = nama
    sub["nik"]      = nik
    sub["jabatan"]  = jabatan
    sub["instansi"] = instansi
    sub["file"]     = output_path
    sub["waktu"]    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if sig_data:
        sub["signature_data"] = sig_data.split(",")[1] if "," in sig_data else sig_data

    save_submissions(submissions)

    return jsonify({
        "success": True,
        "message": "Data berhasil diperbarui!",
        "id": sub_id,
    })


@app.route("/do/status")
def api_status():
    """API: ringkasan status"""
    return jsonify({
        "total": len(submissions),
        "sudah": len(submissions),
        "belum": 0,
    })


# ─────────────────────────────────────────
# PDF FILLING FUNCTION (ReportLab)
# ─────────────────────────────────────────

def fill_pdf(output_path, nama, nik, jabatan, instansi, signature_bytes):
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib import colors

    tanggal = datetime.now().strftime("Koba, %B %Y")
    sig_stream = BytesIO(signature_bytes)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    page_width, page_height = landscape(A4)
    margin = 1 * cm
    usable_width = page_width - 2 * margin
    col_width = usable_width / 2

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    styles = {
        "center_header": ParagraphStyle("CenterHeader", fontName="Helvetica-Bold", fontSize=11, alignment=TA_CENTER, spaceAfter=3),
        "title": ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=13, alignment=TA_CENTER, spaceAfter=6),
        "section": ParagraphStyle("Section", fontName="Helvetica", fontSize=10, alignment=TA_LEFT, spaceAfter=6),
        "item_text": ParagraphStyle("ItemText", fontName="Helvetica", fontSize=10, alignment=TA_JUSTIFY, leading=14, spaceAfter=3),
        "date": ParagraphStyle("Date", fontName="Helvetica", fontSize=11, alignment=TA_CENTER, spaceAfter=6),
        "sig_label": ParagraphStyle("SigLabel", fontName="Helvetica", fontSize=9, alignment=TA_CENTER, leading=12),
        "sig_name": ParagraphStyle("SigName", fontName="Helvetica-Bold", fontSize=10, alignment=TA_CENTER, leading=12),
    }

    elements = []

    if os.path.exists("logo_babel.jpg"):
        elements.append(Image("logo_babel.jpg", width=60, height=33, hAlign="CENTER"))
        elements.append(Spacer(1, 0.2 * cm))

    elements.append(Paragraph("PEMERINTAH PROVINSI KEPULAUAN BANGKA BELITUNG", styles["center_header"]))
    elements.append(Paragraph("PAKTA INTEGRITAS", styles["title"]))
    elements.append(Spacer(1, 0.6 * cm))
    elements.append(Paragraph(f"Saya, {nama}, selaku {jabatan} pada SMK Negeri 1 Koba, menyatakan sebagai berikut:", styles["section"]))
    elements.append(Spacer(1, 0.5 * cm))

    items_l = [
        ("1.", "Berperan secara pro aktif dalam upaya pencegahan dan pemberantasan Korupsi. Kolusi dan Nepotisme serta tidak melibatkan diri dalam perbuatan tercela;"),
        ("2.", "Tidak meminta atau menerima pemberian secara langsung atau tidak langsung berupa suap, hadiah, bantuan, atau bentuk lainnya yang tidak sesuai dengan ketentuan yang berlaku;"),
        ("3.", "Bersikap transparan, jujur, obyektif, tanggung jawab, akuntabel dan profesional dalam melaksanakan tugas, serta patuh pada peraturan perundang-undangan, termasuk kewajiban penyampaian Laporan Hara Kekayaan Penyelenggara Negara (LHKPN) / SPT Tahunan secara tepat waktu;"),
        ("4.", "Menghindari pertentangan kepentingan (conflict of interest) dalam pelaksanaan tugas;"),
    ]
    items_r = [
        ("5.", "Menggunakan sepenuhnya fasilitas BMD untuk kelancaran tugas dan fungsi kedinasan, menjaga dan merawat aset BMD dengan baik dan mengembalikan aset BMD sesuai peraturan perundang-undangan;"),
        ("6.", "Memberi contoh dalam kepatuhan terhadap peraturan perundang-undangan yang berlaku dalam melaksanaakan tugas, terutama kepada karyawan yang berada di bawah pengawasan saya dan sesama pegawai di lingkungan kerja saya secara konsisten;"),
        ("7.", "Akan menyampaikan informasi penyimpangan integritas di SMK Negeri 1 Koba serta turut menjaga kerahasiaan saksi atas pelanggaran peraturan yang dilaporkannya;"),
        ("8.", "Bila saya melanggar hal-hal tersebut di atas, saya siap menghadapi konsekuensinya."),
    ]

    def make_item_row(n, t):
        num_para = Paragraph(f"<b>{n}</b>", styles["item_text"])
        txt_para = Paragraph(t, styles["item_text"])
        return [num_para, txt_para]

    num_col_w = 0.8 * cm
    txt_col_w = col_width - num_col_w - 0.2 * cm

    left_rows = [make_item_row(n, t) for n, t in items_l]
    right_rows = [make_item_row(n, t) for n, t in items_r]

    left_tbl = Table(left_rows, colWidths=[num_col_w, txt_col_w])
    left_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (1, 0), (1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    right_tbl = Table(right_rows, colWidths=[num_col_w, txt_col_w])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (1, 0), (1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    two_col = Table([[left_tbl, right_tbl]], colWidths=[col_width, col_width])
    two_col.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(two_col)

    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(tanggal, styles["date"]))
    elements.append(Spacer(1, 0.8 * cm))

    sig_img = Image(sig_stream, width=120, height=50, hAlign="CENTER")

    witness_rows = [
        [Paragraph("Disaksikan/Diketahui:", styles["sig_label"])],
        [Paragraph("Atasan Langsung", styles["sig_label"])],
        [Paragraph("Kepala SMK Negeri 1 Koba", styles["sig_label"])],
    ]
    if os.path.exists("ttd.jpg"):
        witness_rows.append([Image("ttd.jpg", width=100, height=45, hAlign="CENTER")])
    witness_rows.append([Paragraph("SYAHRYANTO, S.T., M.Pd.", styles["sig_name"])])
    witness_rows.append([Paragraph("NIP. 197708262006041005", styles["sig_label"])])

    witness_tbl = Table(witness_rows, colWidths=[5 * cm])
    witness_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    signer_rows = [
        [Paragraph("Pembuat Pernyataan", styles["sig_label"])],
        [sig_img],
        [Paragraph(nama, styles["sig_name"])],
        [Paragraph(f"NIP. {nik}", styles["sig_label"])],
    ]

    signer_tbl = Table(signer_rows, colWidths=[5 * cm])
    signer_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    sig_section = Table([[witness_tbl, signer_tbl]], colWidths=[col_width, col_width])
    sig_section.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 50),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(sig_section)

    doc.build(elements)


if __name__ == "__main__":
    print("=" * 50)
    print("  Sistem Tanda Tangan Online PDF")
    print("  Link publik: http://localhost:5000/sign")
    print("  Admin panel: http://localhost:5000/")
    print("=" * 50)
    app.run(debug=True, port=5000)
