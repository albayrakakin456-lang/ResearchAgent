"""Yayın özetinden soruyla ilgili bulguyu ve dayanak cümleleri bulur."""
import json
import re

from llm import LLMError, ask
from researchagent import split_sentences

SYSTEM = (
    "Sen titiz bir araştırma asistanısın. Sadece verilen cümlelere dayan, "
    "bilgi uydurma. Yalnızca istenen JSON'u döndür, başka metin yazma."
)


def _sonuc(durum, ilgili=False, bulgu="", gecerli=None, atilan=0, not_="",
           kanitsiz=None):
    """Her durumda aynı anahtarları taşıyan sonuç sözlüğü."""
    return {
        "ilgili": ilgili,
        "bulgu": bulgu,
        "gecerli": gecerli or [],
        "atilan": atilan,
        "durum": durum,
        "not": not_,
        "kanitsiz_sayilar": kanitsiz or [],
    }


def _sayilar(text):
    """Metindeki sayıları bulur; virgüllüyü noktalıya çevirir."""
    # 27.22, 27,22, 45, 0.8 gibi yazımları yakalar
    found = re.findall(r"\d+(?:[.,]\d+)*", text)
    return [sayi.replace(",", ".") for sayi in found]


def sayi_kontrol(bulgu, cumleler):
    """Bulgudaki sayılardan dayanak cümlelerde olmayanları döndürür."""
    # Dayanak cümlelerdeki sayılar bir küme (tekrarsız liste) olur
    dayanak = set()
    for cumle in cumleler:
        dayanak.update(_sayilar(cumle))
    eksik = []
    for sayi in _sayilar(bulgu):
        # Küme kontrolü tam eşleşme arar: 130.85 içinde 30.8 aranmaz
        if sayi not in dayanak and sayi not in eksik:
            eksik.append(sayi)
    return eksik


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
        # temperature=0: aynı soruya mümkün olduğunca aynı cevap
        cevap = ask(_prompt(soru, yayin, cumleler), system=SYSTEM, temperature=0)
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
        # Dayanak yok: bulgudaki her sayı kanıtsız sayılır
        return _sonuc("doğrulanamadı", True, bulgu, [], atilan,
                      kanitsiz=sayi_kontrol(bulgu, []))
    # Bulgudaki sayılar seçilen dayanak cümlelerde var mı?
    kanitsiz = sayi_kontrol(bulgu, [g["cumle"] for g in gecerli])
    return _sonuc("doğrulandı", True, bulgu, gecerli, atilan, kanitsiz=kanitsiz)


# Dosya doğrudan çalışınca küçük deneme çalışır, import'ta çalışmaz
if __name__ == "__main__":
    # (bulgu, dayanak cümleleri, beklenen kanıtsız sayılar)
    DENEMELER = [
        ("Puan 30.8 ve 27.22 oldu.", ["The score rose to 30.8."], ["27.22"]),
        ("Ortalama 27,22 çıktı.", ["The mean was 27.22."], []),
        ("Skor 30.8 oldu.", ["Skor 130.85 idi."], ["30.8"]),
        ("%45 düşüş, 0.8 etki.", ["A 45% drop; effect size 0.8."], []),
    ]
    for bulgu, cumleler, beklenen in DENEMELER:
        sonuc = sayi_kontrol(bulgu, cumleler)
        durum = "OK  " if sonuc == beklenen else "HATA"
        print(f"{durum} {bulgu!r} -> {sonuc} (beklenen {beklenen})")
