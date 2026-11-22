"""Yayın özetinden soruyla ilgili bulguyu ve dayanak cümleleri bulur."""
import json
import re

from llm import LLMError, ask
from researchagent import split_sentences

SYSTEM = (
    "Sen titiz bir araştırma asistanısın. Sadece verilen cümlelere dayan, "
    "bilgi uydurma. Yalnızca istenen JSON'u döndür, başka metin yazma."
)


def _sonuc(durum, ilgili=False, bulgu="", gecerli=None, atilan=0, not_=""):
    """Her durumda aynı anahtarları taşıyan sonuç sözlüğü."""
    return {
        "ilgili": ilgili,
        "bulgu": bulgu,
        "gecerli": gecerli or [],
        "atilan": atilan,
        "durum": durum,
        "not": not_,
    }


def _prompt(soru, yayin, cumleler):
    # Cümleleri "1. ...", "2. ..." diye alt alta diz
    numarali = "\n".join(f"{i}. {c}" for i, c in enumerate(cumleler, start=1))
    return (
        f"Araştırma sorusu: {soru}\n\n"
        f"Yayın: {yayin['title']}\n\n"
        f"Özetin numaralı cümleleri:\n{numarali}\n\n"
        "Görev: Soruyla ilgili bulguyu bu cümlelerden çıkar.\n"
        "Kurallar:\n"
        "- Sadece verilen cümlelere dayan, bilgi uydurma.\n"
        "- İlgili değilse \"ilgili\": false de.\n"
        "- Dayanak olarak SADECE bulguyu doğrudan söyleyen sonuç ve "
        "çıkarım cümlelerini seç.\n"
        "- Yöntem, katılımcı, arka plan ve amaç cümlelerini SEÇME.\n"
        "- En fazla 2 cümle seç.\n"
        "- Aynı bilgi iki dilde varsa sadece birini seç, İngilizce olanı "
        "tercih et.\n"
        "- \"cumle_numaralari\" yukarıdaki numaralardan oluşsun.\n"
        "- \"bulgu\" Türkçe ve tek cümle olsun.\n"
        "Sadece şu JSON'u döndür:\n"
        '{"ilgili": true, "bulgu": "...", "cumle_numaralari": [3, 5]}'
    )


def _json_oku(text):
    """Cevaptan JSON sözlüğü çıkarır; olmazsa None döner."""
    # ```json ... ``` çitlerini temizle
    text = re.sub(r"```(?:json)?", "", text).strip()
    try:
        data = json.loads(text)
    except ValueError:
        # Etrafında metin varsa ilk { ile son } arasını dene
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            data = json.loads(text[start:end + 1])
        except ValueError:
            return None
    return data if isinstance(data, dict) else None


def _numaralari_dogrula(numaralar, toplam):
    """1..toplam aralığındaki tam sayıları ayırır, atılanı sayar."""
    # Liste değilse hiç numara verilmemiş say
    if not isinstance(numaralar, list):
        return [], 0
    gecerli, atilan = [], 0
    for sayi in numaralar:
        # bool de int sayılır (True == 1); onu da reddet
        if isinstance(sayi, int) and not isinstance(sayi, bool) and 1 <= sayi <= toplam:
            if sayi not in gecerli:
                gecerli.append(sayi)
        else:
            atilan += 1
    return gecerli, atilan


def bul_kanit(soru, yayin):
    """Yayın özetinde soruya dayanak olan cümleleri bulur ve doğrular."""
    cumleler = split_sentences(yayin.get("abstract", ""))
    if not cumleler:
        return _sonuc("özet yok")

    try:
        cevap = ask(_prompt(soru, yayin, cumleler), system=SYSTEM)
    except LLMError as hata:
        return _sonuc("model hatası", not_=str(hata))

    data = _json_oku(cevap)
    if data is None:
        return _sonuc("yanıt okunamadı")

    ilgili = data.get("ilgili") is True
    bulgu = str(data.get("bulgu") or "").strip()
    numaralar, atilan = _numaralari_dogrula(data.get("cumle_numaralari"), len(cumleler))
    # Geçerli numaraları cümle metinleriyle eşleştir
    gecerli = [{"numara": n, "cumle": cumleler[n - 1]} for n in numaralar]

    if not ilgili:
        return _sonuc("ilgisiz", atilan=atilan)
    # İlgili denmiş ama hiç geçerli numara yoksa güvenme
    if not gecerli:
        return _sonuc("doğrulanamadı", True, bulgu, [], atilan)
    return _sonuc("doğrulandı", True, bulgu, gecerli, atilan)
