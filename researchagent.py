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
        lines.append(f"- {label} ({', '.join(publication['sources'])})")
    lines.extend(["", "Kanıt ve pasaj doğrulama henüz uygulanmadı.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    report = render_report(data["question"], unique_publications(data["records"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Rapor hazır: {args.output}")


if __name__ == "__main__":
    main()
