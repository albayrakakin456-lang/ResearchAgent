"""OpenAlex'ten makale çeker, kayitlar.json biçiminde döndürür."""
import os
import sys

import requests
from dotenv import load_dotenv

# Makale arama adresi (resmi dokümandan)
API_URL = "https://api.openalex.org/works"


def rebuild_abstract(inverted_index):
    """Kelime -> konumlar sözlüğünü normal metne çevirir."""
    # Özet yoksa None gelir; boş metin döndür
    if not inverted_index:
        return ""
    # Her kelimeyi geçtiği her konumla eşleştir
    positions = []
    for word, indexes in inverted_index.items():
        for index in indexes:
            positions.append((index, word))
    # Konuma göre sırala, kelimeleri boşlukla birleştir
    positions.sort()
    return " ".join(word for _, word in positions)


def to_record(work):
    """OpenAlex makalesini kayitlar.json biçimine çevirir."""
    # Başlık yoksa None gelir; boş metne çevir
    title = (work.get("title") or "").strip()
    # DOI yoksa None gelir; "" yapmazsak researchagent.py çöker
    doi = (work.get("doi") or "").strip()
    # Sayfa adresi iç içe sözlükte; her adımda None'a karşı koru
    location = work.get("primary_location") or {}
    url = (location.get("landing_page_url") or "").strip()

    # Çok yazar varsa sadece ilkini al
    authorships = work.get("authorships") or []
    author = ""
    if authorships:
        first = authorships[0].get("author") or {}
        author = (first.get("display_name") or "").strip()

    record = {"title": title, "source": "OpenAlex"}
    # Boş olmayan isteğe bağlı alanları ekle
    if doi:
        record["doi"] = doi
    if work.get("publication_year"):
        record["year"] = work["publication_year"]
    if author:
        record["author"] = author
    if url:
        record["url"] = url
    # Özet varsa ekle, yoksa alan hiç konmaz
    abstract = rebuild_abstract(work.get("abstract_inverted_index"))
    if abstract:
        record["abstract"] = abstract
    return record


def search_openalex(query, max_results=10):
    """Arama ifadesiyle OpenAlex'te arar, özeti olan kayıtları döndürür."""
    # .env dosyasındaki değerleri ortama yükle
    load_dotenv()
    api_key = os.getenv("OPENALEX_API_KEY", "").strip()
    if not api_key:
        print("Hata: OPENALEX_API_KEY bulunamadı. .env dosyasını kontrol et.")
        return []

    params = {
        "search": query,
        # Sadece özeti olanlar (dokümanda adı var, kullanımı denendi)
        "filter": "has_abstract:true",
        # En çok 100 sonuç istenebilir (dokümana göre)
        "per_page": max(1, min(max_results, 100)),
        # Sadece ihtiyacımız olan alanlar gelsin
        "select": "title,doi,publication_year,authorships,"
                  "primary_location,abstract_inverted_index",
    }
    # Anahtar adrese değil başlığa yazılır, hata mesajında sızmaz
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=15)
        # 4xx/5xx durumunda HTTPError fırlat
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError:
        code = response.status_code
        if code in (401, 403):
            print(f"Hata ({code}): anahtar geçersiz ya da etkinleştirilmemiş.")
        elif code == 429:
            print("Hata (429): çok fazla istek. Biraz bekleyip tekrar dene.")
        else:
            print(f"Hata: OpenAlex {code} döndürdü.")
        return []
    except requests.exceptions.ConnectionError:
        print("Hata: internete bağlanılamadı.")
        return []
    except requests.exceptions.Timeout:
        print("Hata: OpenAlex zamanında yanıt vermedi.")
        return []
    except (requests.exceptions.RequestException, ValueError):
        print("Hata: istek ya da yanıt işlenemedi.")
        return []

    # Başlığı olmayan kayıt zorunlu alanı karşılamaz, atla
    records = [to_record(work) for work in data.get("results", [])]
    records = [record for record in records if record["title"]]
    if not records:
        print("Sonuç bulunamadı.")
    return records


# Dosya doğrudan çalışınca bu blok çalışır, import'ta çalışmaz
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Kullanım: py openalex.py "arama ifadesi"')
        sys.exit(1)
    for record in search_openalex(sys.argv[1], max_results=5):
        print(f"- {record['title']} | yıl: {record.get('year', '-')} | DOI: {record.get('doi', '-')}")
