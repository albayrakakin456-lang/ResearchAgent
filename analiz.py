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


# Başka çalışmaları aktaran (yayının kendi sonucu olmayan) cümle kalıpları
LITERATUR_KALIPLARI = (
    "has been shown", "have been shown", "has been reported", "have been reported",
    "has been suggested", "have been suggested", "previous stud", "prior stud",
    "earlier stud", "previous research", "prior research", "past research",
    "studies have", "research has", "research suggests", "literature",
    "it is well known", "it is widely",
)


def literatur_kontrol(gecerli):
    """Dayanak cümlelerinden literatür alıntısına benzeyenlerin numaraları.

    Örn. "X has been shown to increase Y" makalenin kendi bulgusu değil,
    önceki çalışmalardan bir alıntıdır. Model bunu bulgu sanabiliyor.
    """
    return [g["numara"] for g in gecerli
            if any(kalip in g["cumle"].casefold() for kalip in LITERATUR_KALIPLARI)]


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
        "- Soru gerçek bir araştırma sorusu değilse (selamlaşma, anlamsız "
        "kelime vb.) ya da yayının konusu soruyla doğrudan aynı değilse "
        "\"ilgili\": false de. Benzer kelime geçmesi ilgili olmak için yetmez.\n"
        "- Dayanak olarak SADECE bulguyu doğrudan söyleyen sonuç ve "
        "çıkarım cümlelerini seç.\n"
        "- Yöntem, katılımcı, arka plan ve amaç cümlelerini SEÇME.\n"
        "- Başka çalışmaları aktaran cümleleri (\"has been shown\", "
        "\"previous studies\", \"studies have\" gibi) SEÇME; bunlar bu "
        "yayının bulgusu değildir.\n"
        "- Bulguya dayanak cümlelerde geçmeyen bir kavram ya da sonuç ekleme.\n"
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
    # Dayanak başka çalışmalardan alıntıysa uyar (web'de ve raporda görünür)
    alinti = literatur_kontrol(gecerli)
    not_ = ""
    if alinti:
        numaralar = ", ".join(f"{n}." for n in alinti)
        not_ = (f"Uyarı: {numaralar} dayanak cümlesi önceki çalışmalardan alıntı olabilir; "
                "bu yayının kendi bulgusu olmayabilir.")
    return _sonuc("doğrulandı", True, bulgu, gecerli, atilan, not_=not_, kanitsiz=kanitsiz)


def soru_kontrol_et(soru):
    """Aramadan önce tek model çağrısı: araştırma sorusu mu + İngilizce arama ifadesi.

    {"uygun": bool, "neden": str, "arama_ifadesi": str} döner. Model cevap
    veremezse güvenli tarafta kalır ve geçirmez.
    """
    prompt = (
        f"Girdi: {soru}\n\n"
        "Görev 1: Bu girdi, bilimsel makalelerde aranabilecek bir araştırma "
        "sorusu ya da araştırma konusu mu?\n"
        "EVET örnekleri: 'aralıklı tekrar öğrencilerin hatırlamasını nasıl "
        "etkiler', 'spaced repetition university students', 'kafeinin uyku "
        "kalitesine etkisi'.\n"
        "HAYIR örnekleri: selamlaşma ve sohbet ('naber', 'günün nasıl "
        "gidiyor'), kişisel duygu/durum ('günüm çok kötüydü'), fıkra, öneri, "
        "kişisel tavsiye, anlamsız kelimeler.\n"
        "Emin değilsen HAYIR de.\n"
        "Görev 2: Evet ise, makale veritabanlarında (OpenAlex, arXiv) "
        "aratmak için İngilizce bir \"arama_ifadesi\" yaz: 3-6 anahtar "
        "kelime, soru cümlesi değil. Girdi zaten İngilizceyse anlamını "
        "koruyarak aynen kullan. HAYIR ise boş bırak.\n"
        "Sadece şu JSON'u döndür:\n"
        '{"arastirma_sorusu": true, "neden": "Türkçe kısa açıklama", '
        '"arama_ifadesi": "artificial intelligence academic performance"}'
    )
    try:
        cevap = ask(prompt, system=SYSTEM, temperature=0)
    except LLMError as hata:
        return {"uygun": False, "neden": f"Soru kontrol edilemedi: {hata}",
                "arama_ifadesi": ""}
    data = _json_oku(cevap)
    if data is None:
        return {"uygun": False, "arama_ifadesi": "",
                "neden": "Soru kontrol edilemedi (model yanıtı okunamadı)."}
    neden = str(data.get("neden") or "").strip()
    if data.get("arastirma_sorusu") is True:
        # Boş/uzun ifadeyi kabul etme; çağıran orijinal soruya döner
        ifade = " ".join(str(data.get("arama_ifadesi") or "").split())
        return {"uygun": True, "neden": "", "arama_ifadesi": ifade[:120]}
    return {"uygun": False, "neden": neden, "arama_ifadesi": ""}


def arastirma_sorusu_mu(soru):
    """Aramadan önce: bu girdi bilimsel bir araştırma sorusu mu?

    (True, "") ya da (False, neden) döner. (Eski arayüz; soru_kontrol_et'e dayanır.)
    """
    kontrol = soru_kontrol_et(soru)
    return kontrol["uygun"], kontrol["neden"]


def _celiski_sonuc(durum, mesaj, uygun=None, celiskiler=None, atilan=0, not_=""):
    """Çelişki aramasının her durumda aynı anahtarlı sonucu."""
    return {
        "durum": durum,
        "mesaj": mesaj,
        "uygun": uygun or [],
        "celiskiler": celiskiler or [],
        "atilan": atilan,
        "not": not_,
    }


def _uygun_mu(yayin):
    """İlgili, doğrulanmış ve geçerli dayanağı olan yayın mı?"""
    kanit = yayin.get("kanit") or {}
    return (bool(kanit.get("ilgili"))
            and kanit.get("durum") == "doğrulandı"
            and bool(kanit.get("gecerli")))


def _celiski_prompt(soru, uygun):
    # Her yayın: numara, başlık, bulgu (cümleler gönderilmez)
    satirlar = "\n".join(
        f"{i}. Başlık: {y['title']}\n   Bulgu: {y['kanit']['bulgu']}"
        for i, y in enumerate(uygun, start=1)
    )
    return (
        f"Araştırma sorusu: {soru}\n\n"
        f"Yayınlar ve bulguları:\n{satirlar}\n\n"
        "Görev: Bulguları birbiriyle çelişen yayın çiftlerini bul.\n"
        "Kurallar:\n"
        "- Sadece AYNI sonuç ölçütü hakkında ZIT sonuç varsa çelişki say.\n"
        "- Yön farkı çelişkidir: biri artırır, diğeri azaltır derse; ya da "
        "biri etki bulmuş, diğeri etki bulamamışsa (anlamlı fark yok, "
        "etkilemedi). Örnek: \"hafızayı olumsuz etkiler\" ile \"hafızayı "
        "etkilemedi\" çelişir.\n"
        "- Yönü kelimeye göre değil ANLAMA göre değerlendir: \"yanlış "
        "hatırlamayı artırır\" ile \"hafızayı olumsuz etkiler\" ikisi de "
        "kötüleşmedir, AYNI yöndedir; çelişki değildir.\n"
        "- Ölçütler farklıysa (örn. genel bilişsel yetenek ile yanlış hatıra) "
        "çelişki sayma.\n"
        "- Gruplar farklıysa (örn. üniversite öğrencileri ve genel nüfus) "
        "yine çelişki say, ama \"aciklama\" içinde iki grubu da belirt.\n"
        "- Farklı konu ya da aynı yönde sadece farklı etki büyüklüğü "
        "çelişki değildir.\n"
        "- Emin değilsen boş liste dön.\n"
        "- Uydurma yapma; sadece yukarıdaki bulgulara dayan.\n"
        "- \"yayin_a\" ve \"yayin_b\" yukarıdaki numaralar olsun.\n"
        "- \"aciklama\" Türkçe ve tek cümle olsun.\n"
        "Sadece şu JSON'u döndür:\n"
        '{"celiskiler": [{"yayin_a": 1, "yayin_b": 3, "aciklama": "..."}]}'
    )


def _celiskileri_dogrula(ham, toplam):
    """Var olmayan/aynı/tekrar eden çiftleri atar, atılanı sayar."""
    gecerli, atilan, gorulen = [], 0, set()
    for kayit in ham:
        if not isinstance(kayit, dict):
            atilan += 1
            continue
        a, b = kayit.get("yayin_a"), kayit.get("yayin_b")
        # Her ikisi de 1..toplam aralığında tam sayı mı? (bool olamaz)
        numara_ok = all(
            isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= toplam
            for n in (a, b)
        )
        # frozenset: (1,3) ile (3,1) aynı çift sayılır
        if not numara_ok or a == b or frozenset((a, b)) in gorulen:
            atilan += 1
            continue
        gorulen.add(frozenset((a, b)))
        aciklama = str(kayit.get("aciklama") or "").strip()
        gecerli.append({"yayin_a": a, "yayin_b": b, "aciklama": aciklama})
    return gecerli, atilan


def celiski_bul(soru, sonuclar):
    """--analyze sonuçları arasında birbiriyle çelişen bulguları arar."""
    # Sadece doğrulanmış, ilgili ve dayanaklı olanlar karşılaştırılır
    uygun = [yayin for yayin in sonuclar if _uygun_mu(yayin)]
    if len(uygun) < 2:
        # Tek yayınla çelişki aranamaz; modele hiç sorma
        return _celiski_sonuc("aranamadı",
                              "Çelişki aranamadı (yeterli bulgu yok).", uygun)
    try:
        cevap = ask(_celiski_prompt(soru, uygun), system=SYSTEM, temperature=0)
    except LLMError as hata:
        return _celiski_sonuc("yapılamadı", "Çelişki analizi yapılamadı.",
                              uygun, not_=str(hata))
    data = _json_oku(cevap)
    ham = data.get("celiskiler") if data else None
    if not isinstance(ham, list):
        return _celiski_sonuc("yapılamadı", "Çelişki analizi yapılamadı.", uygun,
                              not_="Model yanıtı okunamadı.")
    gecerli, atilan = _celiskileri_dogrula(ham, len(uygun))
    return _celiski_sonuc("tamam", "", uygun, gecerli, atilan)


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

    # --- Çelişki denemesi: YAPAY ÖRNEK VERİ, gerçek yayın DEĞİL ---
    def ornek(baslik, bulgu):
        return {"title": f"ÖRNEK VERİ: {baslik}", "url": "",
                "kanit": _sonuc("doğrulandı", True, bulgu,
                                [{"numara": 1, "cumle": "(örnek cümle)"}])}

    CELISKI_DENEMELERI = [
        # (ad, yapay yayınlar, beklenen çelişki sayısı)
        ("zıt iki bulgu", [
            ornek("A", "Aralıklı tekrar sınav başarısını artırır."),
            ornek("B", "Aralıklı tekrar sınav başarısı üzerinde etkisizdir.")], 1),
        ("ilgisiz iki bulgu", [
            ornek("C", "Kahve tüketimi uyku süresini kısaltır."),
            ornek("D", "Dağ bisikleti bacak kası gücünü artırır.")], 0),
    ]
    for ad, yayinlar, beklenen in CELISKI_DENEMELERI:
        sonuc = celiski_bul("Aralıklı tekrar sınav başarısını artırır mı?", yayinlar)
        bulunan = len(sonuc["celiskiler"])
        durum = "OK  " if bulunan == beklenen else "HATA"
        print(f"{durum} {ad}: durum={sonuc['durum']} "
              f"bulunan={bulunan} beklenen={beklenen} {sonuc['not']}")
        for kayit in sonuc["celiskiler"]:
            print("    ", kayit)
