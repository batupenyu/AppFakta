"""
Sistem Tanda Tangan Online PDF
Link publik - siapa saja bisa menandatangani
"""

import os
import json
import base64
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, abort, redirect, url_for
from weasyprint import HTML

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ganti-dengan-secret-key-anda'
app.config['SIGNED_DIR'] = 'signed_pdfs'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

os.makedirs(app.config['SIGNED_DIR'], exist_ok=True)

SUBMISSIONS_FILE = "submissions.json"


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
    public_link = request.host_url.rstrip('/') + '/sign'
    return render_template("index.html", submissions=submissions, public_link=public_link)


@app.route("/sign")
def sign_page():
    """Halaman tanda tangan publik - bisa diakses siapa saja"""
    return render_template("sign.html")


@app.route("/api/submit", methods=["POST"])
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


@app.route("/api/delete/<sub_id>", methods=["DELETE"])
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


@app.route("/api/edit/<sub_id>", methods=["PUT"])
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


@app.route("/api/status")
def api_status():
    """API: ringkasan status"""
    return jsonify({
        "total": len(submissions),
        "sudah": len(submissions),
        "belum": 0,
    })


# ─────────────────────────────────────────
# PDF FILLING FUNCTION
# ─────────────────────────────────────────

def fill_pdf(output_path, nama, nik, jabatan, instansi, signature_bytes):
    """
    Generate PDF from HTML template with participant data and signature.
    Uses base64 embedded images for WeasyPrint compatibility.
    """
    from jinja2 import Environment, FileSystemLoader

    tanggal = datetime.now().strftime("Koba, %B %Y")
    nip = nik
    sig_b64 = base64.b64encode(signature_bytes).decode('ascii')

    logo_babel_b64 = ""
    ttd_b64 = ""

    try:
        with open('logo_babel.jpg', 'rb') as f:
            logo_babel_b64 = base64.b64encode(f.read()).decode('ascii')
    except Exception:
        pass

    try:
        with open('ttd.jpg', 'rb') as f:
            ttd_b64 = base64.b64encode(f.read()).decode('ascii')
    except Exception:
        pass

    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('document.html')

    html_out = template.render(
        nama=nama,
        nip=nip,
        jabatan=jabatan,
        instansi=instansi,
        tanggal=tanggal,
        signature_data=sig_b64,
        logo_babel=logo_babel_b64,
        ttd=ttd_b64
    )

    base_url = 'file://' + os.path.abspath('.')
    HTML(string=html_out, base_url=base_url).write_pdf(output_path)


if __name__ == "__main__":
    print("=" * 50)
    print("  Sistem Tanda Tangan Online PDF")
    print("  Link publik: http://localhost:5000/sign")
    print("  Admin panel: http://localhost:5000/")
    print("=" * 50)
    app.run(debug=True, port=5000)
