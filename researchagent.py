"""Build a small report from locally collected academic records."""
import argparse
import json
import re
from pathlib import Path


def unique_publications(records):
    publications = {}
    for record in records:
        doi = record.get("doi", "").strip().lower().removeprefix("https://doi.org/")
        title = " ".join(record["title"].casefold().split())
        key = ("doi", doi) if doi else ("metadata", title, record.get("year"), record.get("author", "").casefold())
        if key not in publications:
            publications[key] = {
                "title": record["title"],
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else record.get("url", ""),
                "sources": [],
                # Özet alanı da taşınsın, yoksa burada kaybolur
                "abstract": "",
            }
        publication = publications[key]
        # Henüz özet yoksa ve bu kayıtta varsa, onu al
        if not publication["abstract"] and record.get("abstract"):
            publication["abstract"] = record["abstract"].strip()
        if record["source"] not in publication["sources"]:
            publication["sources"].append(record["source"])
    return list(publications.values())


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    # Varsayılan json: eski komut --source olmadan çalışsın
    parser.add_argument("--source", choices=["json", "openalex"], default="json")
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
        # openalex kaynağında arama ifadesi şart
        if not args.query:
            parser.error("--source openalex için --query gerekli")
        # Paketler sadece burada gerekli, json modu etkilenmesin
        from openalex import search_openalex
        records = search_openalex(args.query)
        # Sonuç yoksa boş rapor yazmadan çık
        if not records:
            raise SystemExit("OpenAlex'ten kayıt gelmedi, rapor yazılmadı.")
        # Soru verilmezse arama ifadesi kullanılır
        question = args.question or args.query

    # Hangi kaynaktan gelirse gelsin aynı fonksiyonlardan geçer
    publications = unique_publications(records)
    # --analyze kapalıyken çelişki bölümü hiç yazılmaz
    celiski = None
    if args.analyze:
        # analiz sadece burada import edilir (döngüsel import olmasın)
        from analiz import bul_kanit, celiski_bul
        # Maliyet ve süre için sadece ilk 5 yayın analiz edilir
        # Sadece özeti olanlar sayılır; ilk ANALYZE_LIMIT tanesi seçilir
        selected = [p for p in publications if p["abstract"]][:ANALYZE_LIMIT]
        for number, publication in enumerate(selected, start=1):
            print(f"Analiz {number}/{len(selected)}: {publication['title'][:60]}")
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
        print("Çelişki aranıyor...")
        celiski = celiski_bul(question, publications)
    report = render_report(question, publications, analyzed=args.analyze, celiski=celiski)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Rapor hazır: {args.output}")


if __name__ == "__main__":
    main()
