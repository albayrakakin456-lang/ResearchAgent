"""arXiv'den makale çeker, kayitlar.json biçiminde döndürür."""
import sys
import time
import xml.etree.ElementTree as ET

import requests

# Arama adresi (arXiv API kullanım kılavuzundan); anahtar gerekmez
API_URL = "https://export.arxiv.org/api/query"
# arXiv, istekler arasında en az 3 saniye bekleme istiyor
REQUEST_DELAY = 3
# Kendimizi tanıtalım; arXiv anonim toplu istekleri sevmiyor
HEADERS = {"User-Agent": "ResearchAgent/0.1 (ogrenci projesi)"}

# Yanıt Atom XML; etiketler bu ad alanlarıyla gelir
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

# Son isteğin zamanı; art arda çağrılarda bekleme için
_last_request = 0.0


def _text(element, path):
    """Etiketin metnini tek satıra indirger; yoksa boş metin."""
    found = element.find(path, NS)
    if found is None or not found.text:
        return ""
    # arXiv başlık ve özetleri satır sonlarıyla bölünmüş gelir
    return " ".join(found.text.split())


def build_query(query):
    """'spaced repetition' → 'all:spaced AND all:repetition'."""
    words = query.split()
    return " AND ".join(f"all:{word}" for word in words)


def to_record(entry):
    """arXiv kaydını (Atom <entry>) kayitlar.json biçimine çevirir."""
    title = _text(entry, "atom:title")
    record = {"title": title, "source": "arXiv"}

    # Dergide yayımlandıysa DOI'si olur; yoksa alan hiç konmaz
    doi = _text(entry, "arxiv:doi")
    if doi:
        record["doi"] = doi
    # Tarih "2017-06-12T17:57:34Z" biçiminde; ilk 4 karakter yıl
    published = _text(entry, "atom:published")
    if published[:4].isdigit():
        record["year"] = int(published[:4])
    # Çok yazar varsa sadece ilkini al (openalex.py ile aynı)
    author = _text(entry, "atom:author/atom:name")
    if author:
        record["author"] = author
    # Makalenin arXiv sayfası, örn. http://arxiv.org/abs/1706.03762v7
    url = _text(entry, "atom:id")
    if url:
        record["url"] = url
    abstract = _text(entry, "atom:summary")
    if abstract:
        record["abstract"] = abstract
    return record


def parse_feed(xml_text):
    """API yanıtını kayıt listesine çevirir; okunamazsa None döner."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    records = []
    for entry in root.findall("atom:entry", NS):
        # Hatalı sorguda arXiv sonuç yerine bir "Error" kaydı döndürür
        if "/api/errors" in _text(entry, "atom:id"):
            print(f"Hata: arXiv sorguyu kabul etmedi ({_text(entry, 'atom:summary')}).")
            return []
        records.append(to_record(entry))
    # Başlığı olmayan kayıt zorunlu alanı karşılamaz, atla
    return [record for record in records if record["title"]]


def search_arxiv(query, max_results=10):
    """Arama ifadesiyle arXiv'de arar, kayıt listesi döndürür."""
    global _last_request
    if not query.strip():
        print("Hata: arama ifadesi boş.")
        return []

    params = {
        "search_query": build_query(query),
        "start": 0,
        # Tek istekte çok sonuç istemek arXiv'i yorar; makul sınır
        "max_results": max(1, min(max_results, 100)),
        "sortBy": "relevance",
    }

    # Önceki istekten bu yana 3 sn geçmediyse bekle
    wait = REQUEST_DELAY - (time.time() - _last_request)
    if wait > 0:
        time.sleep(wait)

    try:
        response = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        _last_request = time.time()
        # 4xx/5xx durumunda HTTPError fırlat
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        code = response.status_code
        if code in (429, 503):
            print(f"Hata ({code}): arXiv şu an çok yoğun. Biraz bekleyip tekrar dene.")
        else:
            print(f"Hata: arXiv {code} döndürdü.")
        return []
    except requests.exceptions.ConnectionError:
        print("Hata: internete bağlanılamadı.")
        return []
    except requests.exceptions.Timeout:
        print("Hata: arXiv zamanında yanıt vermedi.")
        return []
    except requests.exceptions.RequestException:
        print("Hata: istek gönderilemedi.")
        return []

    records = parse_feed(response.text)
    if records is None:
        print("Hata: arXiv yanıtı okunamadı.")
        return []
    if not records:
        print("Sonuç bulunamadı.")
    return records


# Dosya doğrudan çalışınca bu blok çalışır, import'ta çalışmaz
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Kullanım: python arxiv.py "arama ifadesi"')
        sys.exit(1)
    for record in search_arxiv(sys.argv[1], max_results=5):
        print(f"- {record['title']} | yıl: {record.get('year', '-')} | DOI: {record.get('doi', '-')}")
