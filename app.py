from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io, os, re
from datetime import datetime

app = Flask(__name__)
CORS(app)

FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "ipag.ttf")
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("IPAGothic", FONT_PATH))
    FONT_NAME = "IPAGothic"
else:
    FONT_NAME = "Helvetica"

PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")

# ============================================================
# 市町村ごとの設定
# ============================================================
MUNI_CONFIG = {
    "aomori": {
        "name": "青森市",
        "pdf": "aomori.pdf",
        "pdf_w": 595.2,
        "pdf_h": 841.68,
        "fields": {
            "address":  (215, 207, 9),
            "furigana": (115, 298, 9),
            "tel":      (365, 303, 9),
            "name":     (115, 338, 10),
        },
        "dob_fields": {
            "year":  (380, 362, 9),
            "month": (414, 362, 9),
            "day":   (446, 362, 9),
        },
        "circles": {
            "pref": {
                "都": (206.85, 188.05),
                "道": (206.85, 198.6),
                "府": (206.85, 209.15),
                "県": (206.85, 219.7),
            },
            "era": {
                "明": (366.55, 338.55),
                "大": (390.75, 338.55),
                "昭": (414.85, 338.55),
                "平": (438.95, 338.55),
            },
            "radius_x": 7.5,
            "radius_y": 6.5,
        },
        "has_prefecture_field": True,   # 住所欄が「都道府県＋市区町村」形式
        "tel_split": False,             # 電話番号は1フィールドにそのまま入れる
    },

    "hachinohe": {
        "name": "八戸市",
        "pdf": "hachinohe.pdf",
        "pdf_w": 595.32,
        "pdf_h": 841.92,
        "fields": {
            "address":  (72, 143, 10),
            "furigana": (112, 160, 8),
            "name":     (95, 190, 13),
        },
        "dob_fields": {
            "year":  (378, 176, 9),
            "month": (420, 176, 9),
            "day":   (463, 176, 9),
        },
        "circles": {
            "pref": {},  # 八戸市のPDFには都道府県欄がない
            "era": {
                "大": (340, 158),
                "昭": (359, 158),
                "平": (378, 158),
            },
            "radius_x": 7,
            "radius_y": 6,
        },
        "has_prefecture_field": False,  # 「八戸市」から始まる住所のみ（都道府県欄なし）
        "tel_split": True,              # 電話番号は3分割フィールド
        "tel_fields": {
            "part1": (338, 195, 9),
            "part2": (400, 195, 9),
            "part3": (449, 195, 9),
        },
    },
}


def get_wareki(year):
    """西暦→和暦（元号ラベル, 和暦年, 丸をつける文字）"""
    if year >= 2019:
        return ("令和", year - 2018, "平")  # フォームに「令和」欄が無い場合のフォールバック
    if year >= 1989:
        return ("平成", year - 1988, "平")
    if year >= 1926:
        return ("昭和", year - 1925, "昭")
    return ("大正", year - 1911, "大")


def split_prefecture(address):
    m = re.match(r'^(.{2,3}?[都道府県])([\s\S]*)$', address)
    if m:
        return m.group(1), m.group(2)
    return None, address


def generate_pdf(muni_id, name, furigana, address, tel, dob_str):
    cfg = MUNI_CONFIG.get(muni_id)
    if not cfg:
        raise ValueError(f"未対応の市町村です: {muni_id}")

    pdf_path = os.path.join(PDF_DIR, cfg["pdf"])
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDFが見つかりません: {pdf_path}")

    PDF_H = cfg["pdf_h"]
    PDF_W = cfg["pdf_w"]

    dob = datetime.strptime(dob_str, "%Y-%m-%d")
    wareki_label, wareki_year, era_char = get_wareki(dob.year)

    # 住所処理：都道府県欄があるフォームは分離、無いフォームはそのまま
    if cfg.get("has_prefecture_field"):
        pref, address_rest = split_prefecture(address)
        pref_char = pref[-1] if pref else None
        address_to_write = address_rest or address
    else:
        pref_char = None
        address_to_write = address

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(PDF_W, PDF_H))

    # 通常テキスト項目
    texts = {"address": address_to_write, "furigana": furigana, "name": name}
    for key, text in texts.items():
        if not text or key not in cfg["fields"]:
            continue
        x, y_top, fs = cfg["fields"][key]
        c.setFont(FONT_NAME, fs)
        c.drawString(x, PDF_H - y_top, text)

    # 電話番号：分割フォームか単一フィールドか
    if cfg.get("tel_split") and tel:
        parts = tel.split("-")
        tel_field_keys = ["part1", "part2", "part3"]
        for i, key in enumerate(tel_field_keys):
            if i < len(parts) and key in cfg.get("tel_fields", {}):
                x, y_top, fs = cfg["tel_fields"][key]
                c.setFont(FONT_NAME, fs)
                c.drawString(x, PDF_H - y_top, parts[i])
    elif not cfg.get("tel_split") and tel and "tel" in cfg["fields"]:
        x, y_top, fs = cfg["fields"]["tel"]
        c.setFont(FONT_NAME, fs)
        c.drawString(x, PDF_H - y_top, tel)

    # 生年月日（年・月・日）
    for key, value in [("year", str(wareki_year)), ("month", str(dob.month)), ("day", str(dob.day))]:
        x, y_top, fs = cfg["dob_fields"][key]
        c.setFont(FONT_NAME, fs)
        c.drawString(x, PDF_H - y_top, value)

    # 丸囲み
    circles_cfg = cfg["circles"]
    rx = circles_cfg["radius_x"]
    ry = circles_cfg["radius_y"]
    c.setLineWidth(1.2)

    if pref_char and pref_char in circles_cfg.get("pref", {}):
        cx, cy_top = circles_cfg["pref"][pref_char]
        cy = PDF_H - cy_top
        c.ellipse(cx - rx, cy - ry, cx + rx, cy + ry, stroke=1, fill=0)

    if era_char in circles_cfg.get("era", {}):
        cx, cy_top = circles_cfg["era"][era_char]
        cy = PDF_H - cy_top
        c.ellipse(cx - rx, cy - ry, cx + rx, cy + ry, stroke=1, fill=0)

    c.save()
    packet.seek(0)

    base = PdfReader(pdf_path)
    overlay = PdfReader(packet)
    writer = PdfWriter()
    page = base.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output


@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "message": "住民票請求書API",
        "supported_municipalities": list(MUNI_CONFIG.keys()),
    })


@app.route("/api/generate", methods=["POST"])
def api_generate():
    try:
        data = request.get_json()
        muni_id   = data.get("muni", "aomori")
        name      = data.get("name", "")
        furigana  = data.get("furigana", "")
        address   = data.get("address", "")
        tel       = data.get("tel", "")
        dob       = data.get("dob", "")

        if not all([name, address, dob]):
            return jsonify({"error": "氏名・住所・生年月日は必須です"}), 400

        if muni_id not in MUNI_CONFIG:
            return jsonify({"error": f"「{muni_id}」は現在準備中です"}), 400

        pdf_bytes = generate_pdf(muni_id, name, furigana, address, tel, dob)

        cfg = MUNI_CONFIG.get(muni_id, {})
        filename = f"住民票請求書_{cfg.get('name', muni_id)}.pdf"

        return send_file(
            pdf_bytes,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename.encode("utf-8").decode("latin-1"),
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
