"""Build a small report from locally collected academic records."""
import argparse
import contextlib
import io
import json
import re
import unicodedata
from pathlib import Path


# DOI'nin önüne eklenebilen bilinen biçimler (en uzundan kısaya)
DOI_PREFIXES = (
    "https://dx.doi.org/", "http://dx.doi.org/",
    "https://doi.org/", "http://doi.org/",
    "dx.doi.org/", "doi.org/", "doi:",
)


def normalize_doi(value):
    """DOI'yi karşılaştırılabilir hâle getirir: '10.xxxx/...' biçimi, küçük harf."""
    # None ya da sayı gelebilir; önce metne çevir
    doi = str(value or "").strip().lower()
    for prefix in DOI_PREFIXES:
        if doi.startswith(prefix):
            doi = doi[len(prefix):].strip()
            break
    return doi


def normalize_title(value):
    """Başlığı eşleştirme için sadeleştirir: harf/rakam dışı her şey boşluk olur."""
    # NFKD + birleşik işaretleri silmek "İ" → "i", "’" gibi farkları giderir
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    # Noktalama ve tırnakları boşluğa çevir, fazla boşlukları sil
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def normalize_year(value):
    """2012 ve "2012" aynı sayılsın; çevrilemezse None."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def unique_publications(records):
    """Farklı kaynaklardan gelen aynı yayının kayıtlarını tek yayında birleştirir.

    Önce DOI'ye göre eşleştirir. DOI'si olmayan kayıt, aynı başlık ve yıla
    sahip yayınla birleşir (o yayının DOI'si olsa bile).
    """
    publications = []
    by_doi = {}
    by_title = {}
    for record in records:
        title = str(record.get("title") or "").strip()
        # Başlık yoksa kaydı tanıyamayız; çökmek yerine atla
        if not title:
            print("Uyarı: başlığı olmayan bir kayıt atlandı.")
            continue
        source = str(record.get("source") or "").strip() or "Bilinmeyen kaynak"
        doi = normalize_doi(record.get("doi"))
        title_key = (normalize_title(title), normalize_year(record.get("year")))

        # 1) Aynı DOI daha önce görüldüyse o yayın
        publication = by_doi.get(doi) if doi else None
        # 2) Değilse başlık + yıl. İki farklı DOI ise farklı yayın sayılır.
        if publication is None:
            candidate = by_title.get(title_key)
            if candidate is not None and (not doi or not candidate["doi"]):
                publication = candidate
        # 3) Hiçbiri değilse yeni yayın
        if publication is None:
            publication = {
                "title": title,
                "doi": "",
                "url": "",
                "sources": [],
                # Özet alanı da taşınsın, yoksa burada kaybolur
                "abstract": "",
            }
            publications.append(publication)
            by_title.setdefault(title_key, publication)

        # DOI'siz yayına sonradan DOI'li kayıt geldiyse DOI'yi ekle
        if doi and not publication["doi"]:
            publication["doi"] = doi
            publication["url"] = f"https://doi.org/{doi}"
        if doi:
            by_doi.setdefault(doi, publication)
        # DOI yoksa kaydın kendi adresini kullan
        if not publication["url"] and record.get("url"):
            publication["url"] = str(record["url"]).strip()
        # Henüz özet yoksa ve bu kayıtta varsa, onu al
        if not publication["abstract"] and record.get("abstract"):
            publication["abstract"] = str(record["abstract"]).strip()
        if source not in publication["sources"]:
            publication["sources"].append(source)
    return publications


# --analyze en fazla kaç yayını modele sorsun (maliyet ve süre için)
ANALYZE_LIMIT = 5

# Cümleyi bitirmeyen, bilinen kısaltmalar (büyük/küçük harf duyarlı)
ABBREVIATION = re.compile(
    r"(?:\bet al|\be\.g|\bi\.e|\bvs|\bcf|\bDr|\bProf|\bMr|\bMrs|\bMs"
    r"|\bFigs?|\bEq|\bNo|\bapprox|\bU\.S)\.$"
)
# . ! ? sonrası (varsa kapanış tırnağı/parantez) + boşluk + büyük harf
SENTENCE_END = re.compile(
    r"""(?:(?<=[.!?])|(?<=[.!?]["'”’)\]]))\s+(?=["'“‘(\[]?[A-ZÇĞİÖŞÜ0-9])"""
)


def split_sentences(text):
    """Metni basitçe cümlelere böler (küçük harfle başlayan cümlede yanılır)."""
    result = []
    for part in SENTENCE_END.split(text.strip()):
        part = part.strip()
        if not part:
            continue
        # Önceki parça kısaltmayla bittiyse cümle bitmemiştir, birleştir
        if result and ABBREVIATION.search(result[-1]):
            result[-1] += " " + part
        else:
            result.append(part)
    return result


def render_kanit(kanit):
    """bul_kanit sonucunu rapor satırlarına çevirir."""
    if not kanit:
        return []
    durum = kanit["durum"]
    # Bulgudaki dayanaksız rakamlar varsa bulgunun altına uyarı
    sayi_uyari = []
    if kanit.get("kanitsiz_sayilar"):
        sayilar = ", ".join(kanit["kanitsiz_sayilar"])
        sayi_uyari = [f"  - Uyarı: Bulgudaki şu rakamlar dayanak cümlelerde yok: {sayilar}"]
    if durum == "doğrulandı":
        lines = [f"  - **Bulgu:** {kanit['bulgu']}"] + sayi_uyari
        for item in kanit["gecerli"]:
            lines.append(f"  - **Dayanak ({item['numara']}. cümle):** {item['cumle']}")
    elif durum == "doğrulanamadı":
        # Model bulgu verdi ama geçerli cümle numarası gösteremedi
        lines = [f"  - **Bulgu (DOĞRULANAMADI):** {kanit['bulgu']}"] + sayi_uyari
        lines.append("  - **Dayanak:** yok, modelin verdiği cümle numaraları geçersiz")
    elif durum == "özet yok":
        lines = ["  - **Analiz:** Özet yok, analiz yapılamadı."]
    elif durum == "analiz edilmedi":
        # Yayın altına yazılmaz, raporun sonunda tek satırda özetlenir
        return []
    else:
        # ilgisiz, yanıt okunamadı, model hatası
        extra = f" ({kanit['not']})" if kanit["not"] else ""
        lines = [f"  - **Analiz:** {durum}{extra}"]
    if kanit["atilan"]:
        lines.append(f"  - Geçersiz atılan cümle numarası: {kanit['atilan']}")
    return lines


def yayin_etiketi(publication):
    """Linki varsa Markdown link, yoksa düz başlık."""
    title = publication["title"]
    url = publication.get("url", "")
    return f"[{title}]({url})" if url else title


def render_celiskiler(celiski):
    """celiski_bul sonucunu 'Çelişen sonuçlar' bölümüne çevirir."""
    lines = ["", "## Çelişen sonuçlar", ""]
    # Arama yapılamadıysa/yapılmadıysa nedenini yaz, bölümü bitir
    if celiski["durum"] != "tamam":
        lines.append(celiski["mesaj"])
        return lines
    if not celiski["celiskiler"]:
        lines.append("Çelişen çalışma bulunamadı.")
    for sira, kayit in enumerate(celiski["celiskiler"], start=1):
        lines.append(f"### Çelişki {sira}")
        for harf, anahtar in (("A", "yayin_a"), ("B", "yayin_b")):
            # Model numarası, doğrulanmış 'uygun' listesinin sırasıdır
            yayin = celiski["uygun"][kayit[anahtar] - 1]
            lines.append(f"- **{harf}:** {yayin_etiketi(yayin)}")
            lines.append(f"  - **Bulgu:** {yayin['kanit']['bulgu']}")
            for item in yayin["kanit"]["gecerli"]:
                lines.append(f"  - **Dayanak ({item['numara']}. cümle):** {item['cumle']}")
        if kayit["aciklama"]:
            lines.append(f"- **Açıklama:** {kayit['aciklama']}")
        lines.append("")
    if celiski["atilan"]:
        lines.append(f"Geçersiz olduğu için atılan çelişki kaydı: {celiski['atilan']}")
    return lines


def render_report(question, publications, analyzed=False, celiski=None):
    lines = ["# ResearchAgent", "", f"**Araştırma sorusu**  {question}", "",
             f"**Benzersiz yayın kaydı**  {len(publications)}", "",
             "## Taranacak yayınlar", ""]
    for publication in publications:
        label = yayin_etiketi(publication)
        # DOI varsa metni hazırla, yoksa boş bırak
        doi_text = f" DOI: {publication['doi']}" if publication["doi"] else ""
        # Satırı oluştur; DOI yoksa sonuna hiçbir şey eklenmez
        lines.append(f"- {label} ({', '.join(publication['sources'])}){doi_text}")
        # Özet varsa cümleleri 1'den başlayarak numarala
        sentences = split_sentences(publication.get("abstract", ""))
        for number, sentence in enumerate(sentences, start=1):
            # İki boşluk girinti: yayının alt maddesi olur
            lines.append(f"  {number}. {sentence}")
        # Analiz yapıldıysa bulguyu ve dayanağı yaz
        lines.extend(render_kanit(publication.get("kanit")))
    # Analiz yapıldıysa alt not da buna göre değişir
    if analyzed:
        footer = ("Dayanak cümle numaraları özetle doğrulandı; "
                  "anlamsal doğruluk elle kontrol edilmelidir.")
    else:
        footer = "Kanıt ve pasaj doğrulama henüz uygulanmadı."
    # Limit yüzünden atlanan yayınları tek satırda say
    skipped = sum(1 for p in publications
                  if p.get("kanit", {}).get("durum") == "analiz edilmedi")
    if skipped:
        lines.extend(["", f"{skipped} yayın analiz edilmedi "
                          f"(ilk {ANALYZE_LIMIT} yayınla sınırlı)."])
    # Çelişki araması yapıldıysa ayrı bir bölüm olarak ekle
    if celiski:
        lines.extend(render_celiskiler(celiski))
    lines.extend(["", footer, ""])
    return "\n".join(lines)


def analiz_et(question, publications, ilerleme=print):
    """Yayınlara bulgu ekler (publication["kanit"]), çelişki sonucunu döndürür."""
    # analiz sadece burada import edilir (döngüsel import olmasın)
    from analiz import bul_kanit, celiski_bul
    # Maliyet ve süre için sadece ilk 5 yayın analiz edilir
    # Sadece özeti olanlar sayılır; ilk ANALYZE_LIMIT tanesi seçilir
    selected = [p for p in publications if p["abstract"]][:ANALYZE_LIMIT]
    for number, publication in enumerate(selected, start=1):
        ilerleme(f"Analiz {number}/{len(selected)}: {publication['title'][:60]}")
        publication["kanit"] = bul_kanit(question, publication)
    # Kalanlara model çağrılmaz, sadece nedenini yazan not düşülür
    for publication in publications:
        if "kanit" in publication:
            continue
        if not publication["abstract"]:
            # Özet yoksa bul_kanit model çağırmadan "özet yok" döner
            publication["kanit"] = bul_kanit(question, publication)
        else:
            publication["kanit"] = {"durum": "analiz edilmedi", "atilan": 0}
    # Analiz sonuçları arasında çelişen bulguları ara
    ilerleme("Çelişki aranıyor...")
    return celiski_bul(question, publications)


# Web arayüzünde seçilebilen kaynaklar (anahtar -> görünen ad)
KAYNAKLAR = {"openalex": "OpenAlex", "arxiv": "arXiv"}
# "naber" gibi tek kelimelik girdiler araştırma sorusu sayılmaz
MIN_KELIME = 3


def calistir(sorgu, kaynak="openalex", analiz=True):
    """Web arayüzü için: arar, (istenirse) analiz eder, sonucu sözlük döndürür."""
    sonuc = {"soru": (sorgu or "").strip(), "kaynak": kaynak, "analiz": analiz,
             "hata": "", "uyari": "", "arama_ifadesi": "",
             "yayinlar": [], "celiskiler": None, "rapor_md": ""}
    if not sonuc["soru"]:
        sonuc["hata"] = "Lütfen bir araştırma sorusu yaz."
        return sonuc
    # Çok kısa girdide arama yapma: arama motoru alakasız şeyler getirir
    if len(sonuc["soru"].split()) < MIN_KELIME:
        sonuc["hata"] = (f"Lütfen bir araştırma sorusu yaz (en az {MIN_KELIME} kelime). "
                         "Örnek: spaced repetition university students")
        return sonuc
    if kaynak not in KAYNAKLAR:
        sonuc["hata"] = "Bilinmeyen kaynak seçildi."
        return sonuc
    # Kapı kontrolü: araştırma sorusu değilse hiç arama yapma
    from analiz import soru_kontrol_et
    kontrol = soru_kontrol_et(sonuc["soru"])
    if not kontrol["uygun"]:
        sonuc["uyari"] = ("Bu bir araştırma sorusu değil. ResearchAgent sadece "
                          "bilimsel makale ve araştırma sorularına cevap verir. "
                          "Örnek: spaced repetition university students")
        if kontrol["neden"]:
            sonuc["uyari"] += f" ({kontrol['neden']})"
        return sonuc
    # Makale veritabanları İngilizce: Türkçe soruyu İngilizce ifadeyle ara
    arama = kontrol["arama_ifadesi"] or sonuc["soru"]
    sonuc["arama_ifadesi"] = arama

    # Paketler sadece burada gerekli, json modu etkilenmesin
    if kaynak == "openalex":
        from openalex import search_openalex as search
    else:
        from arxiv import search_arxiv as search
    # Arama fonksiyonları hataları print eder; mesajı yakalayıp ekrana taşırız
    yazilan = io.StringIO()
    with contextlib.redirect_stdout(yazilan):
        kayitlar = search(arama)
    if not kayitlar:
        mesaj = " ".join(yazilan.getvalue().split())
        sonuc["hata"] = mesaj or f"{KAYNAKLAR[kaynak]} kaynağından kayıt gelmedi."
        return sonuc

    yayinlar = unique_publications(kayitlar)
    celiski = None
    if analiz:
        # Web'de terminal yok: ilerleme mesajlarını yutarız
        celiski = analiz_et(sonuc["soru"], yayinlar, ilerleme=lambda mesaj: None)

    # Çelişkideki yayınlar listede kaçıncı sırada? (nesne kimliğiyle bul)
    sira_of = {id(p): no for no, p in enumerate(yayinlar, start=1)}
    for no, p in enumerate(yayinlar, start=1):
        kanit = p.get("kanit") or {}
        durum = kanit.get("durum", "analiz edilmedi")
        sonuc["yayinlar"].append({
            "no": no,
            "baslik": p["title"],
            "link": p["url"],
            "doi": p["doi"],
            "kaynaklar": p["sources"],
            "cumleler": split_sentences(p.get("abstract", "")),
            "durum": "DOĞRULANAMADI" if durum == "doğrulanamadı" else durum,
            "bulgu": kanit.get("bulgu", ""),
            "dayanak": kanit.get("gecerli", []),
            "rakam_uyarisi": kanit.get("kanitsiz_sayilar", []),
            "not": kanit.get("not", ""),
        })
    if celiski:
        liste = []
        for kayit in celiski["celiskiler"]:
            a = celiski["uygun"][kayit["yayin_a"] - 1]
            b = celiski["uygun"][kayit["yayin_b"] - 1]
            liste.append({"a": sira_of[id(a)], "b": sira_of[id(b)],
                          "aciklama": kayit["aciklama"]})
        mesaj = celiski["mesaj"]
        if celiski["durum"] == "tamam" and not liste:
            mesaj = "Çelişen çalışma bulunamadı."
        sonuc["celiskiler"] = {"durum": celiski["durum"], "mesaj": mesaj,
                               "liste": liste, "atilan": celiski["atilan"]}
    # İndirilebilir Markdown raporu da aynı veriden üretilir
    sonuc["rapor_md"] = render_report(sonuc["soru"], yayinlar, analyzed=analiz, celiski=celiski)
    return sonuc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    # Varsayılan json: eski komut --source olmadan çalışsın
    parser.add_argument("--source", choices=["json", "openalex", "arxiv"], default="json")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--query")
    parser.add_argument("--question")
    # Varsayılan kapalı: eski komutlar aynen çalışır
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.source == "json":
        # json kaynağında dosya yolu şart
        if not args.input:
            parser.error("--source json için --input gerekli")
        data = json.loads(args.input.read_text(encoding="utf-8"))
        records = data["records"]
        # --question verildiyse dosyadaki sorunun yerine geçer
        question = args.question or data["question"]
    else:
        # openalex ve arxiv kaynaklarında arama ifadesi şart
        if not args.query:
            parser.error(f"--source {args.source} için --query gerekli")
        # Paketler sadece burada gerekli, json modu etkilenmesin
        if args.source == "openalex":
            from openalex import search_openalex as search
            source_name = "OpenAlex"
        else:
            from arxiv import search_arxiv as search
            source_name = "arXiv"
        records = search(args.query)
        # Sonuç yoksa boş rapor yazmadan çık
        if not records:
            raise SystemExit(f"{source_name} kaynağından kayıt gelmedi, rapor yazılmadı.")
        # Soru verilmezse arama ifadesi kullanılır
        question = args.question or args.query

    # Hangi kaynaktan gelirse gelsin aynı fonksiyonlardan geçer
    publications = unique_publications(records)
    # --analyze kapalıyken çelişki bölümü hiç yazılmaz
    celiski = None
    if args.analyze:
        celiski = analiz_et(question, publications)
    report = render_report(question, publications, analyzed=args.analyze, celiski=celiski)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Rapor hazır: {args.output}")


if __name__ == "__main__":
    main()
