"""OpenAlex'ten makale çeker, kayitlar.json biçiminde döndürür."""
import os
import sys

import requests
from dotenv import load_dotenv

# Makale arama adresi (resmi dokümandan)
API_URL = "https://api.openalex.org/works"


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
    return record


def search_openalex(query, max_results=10):
    """Arama ifadesiyle OpenAlex'te arar, kayıt listesi döndürür."""
    # .env dosyasındaki değerleri ortama yükle
    load_dotenv()
    api_key = os.getenv("OPENALEX_API_KEY", "").strip()
    if not api_key:
        print("Hata: OPENALEX_API_KEY bulunamadı. .env dosyasını kontrol et.")
        return []

    params = {
        "search": query,
        # En çok 100 sonuç istenebilir (dokümana göre)
        "per_page": max(1, min(max_results, 100)),
        # Sadece ihtiyacımız olan alanlar gelsin
        "select": "title,doi,publication_year,authorships,primary_location",
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
