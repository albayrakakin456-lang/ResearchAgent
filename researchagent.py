"""Build a small report from locally collected academic records."""
import argparse
import json
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
            }
        publication = publications[key]
        if record["source"] not in publication["sources"]:
            publication["sources"].append(record["source"])
    return list(publications.values())


def render_report(question, publications):
    lines = ["# ResearchAgent", "", f"**Araştırma sorusu**  {question}", "",
             f"**Benzersiz yayın kaydı**  {len(publications)}", "",
             "## Taranacak yayınlar", ""]
    for publication in publications:
        title = publication["title"]
        url = publication["url"]
        label = f"[{title}]({url})" if url else title
        # DOI varsa metni hazırla, yoksa boş bırak
        doi_text = f" DOI: {publication['doi']}" if publication["doi"] else ""
        # Satırı oluştur; DOI yoksa sonuna hiçbir şey eklenmez
        lines.append(f"- {label} ({', '.join(publication['sources'])}){doi_text}")
    lines.extend(["", "Kanıt ve pasaj doğrulama henüz uygulanmadı.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    # Varsayılan json: eski komut --source olmadan çalışsın
    parser.add_argument("--source", choices=["json", "openalex"], default="json")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--query")
    parser.add_argument("--question")
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
    report = render_report(question, unique_publications(records))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Rapor hazır: {args.output}")


if __name__ == "__main__":
    main()
