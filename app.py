"""ResearchAgent'ın yerel web arayüzü. Çalıştır: py app.py"""
import threading
import traceback

from flask import Flask, jsonify, render_template, request

from researchagent import KAYNAKLAR, calistir

app = Flask(__name__)

# Aramalar stdout'u geçici olarak yakaladığı için aynı anda tek arama
ARAMA_KILIDI = threading.Lock()


@app.get("/")
def anasayfa():
    # Laravel: view('index', ['kaynaklar' => ...])
    return render_template("index.html", kaynaklar=KAYNAKLAR)


@app.post("/ara")
def ara():
    # Laravel: $request->input('sorgu')
    veri = request.get_json(silent=True) or {}
    sorgu = str(veri.get("sorgu", "")).strip()
    kaynak = str(veri.get("kaynak", "openalex"))
    if not ARAMA_KILIDI.acquire(blocking=False):
        return jsonify({"hata": "Başka bir arama sürüyor, bitmesini bekle."})
    try:
        return jsonify(calistir(sorgu, kaynak))
    except Exception:
        # Ayrıntı terminale yazılır; sayfada sade mesaj gösterilir
        traceback.print_exc()
        return jsonify({"hata": "Beklenmeyen bir hata oluştu. Ayrıntı terminalde."})
    finally:
        ARAMA_KILIDI.release()


if __name__ == "__main__":
    # Sadece bu bilgisayardan erişilir (127.0.0.1), debug kapalı
    app.run(host="127.0.0.1", port=5000)
