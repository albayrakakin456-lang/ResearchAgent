"""arXiv'den makale çeker, kayitlar.json biçiminde döndürür."""
import re
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


# Aramada anlam taşımayan İngilizce kelimeler; sorgudan çıkarılır
STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "for", "to", "and", "or", "with",
    "by", "at", "from", "is", "are", "how", "what", "does", "do", "vs",
}


def query_terms(query):
    """Sorguyu terimlere ayırır. Tırnak içindeki ifade tek terim kalır.

    'spaced repetition in "university students"'
    → ['spaced', 'repetition', 'university students']
    """
    terms = []
    # "..." içindekini ya da boşluksuz kelimeyi yakala
    for phrase, word in re.findall(r'"([^"]+)"|(\S+)', query):
        # arXiv sorgu dilinde özel anlamı olan karakterleri temizle
        term = re.sub(r'[():"]', " ", phrase or word)
        term = " ".join(term.split())
        if term:
            terms.append(term)
    # Bağlaçları at; hepsi bağlaçsa (çok kısa sorgu) olduğu gibi bırak
    meaningful = [t for t in terms if t.casefold() not in STOPWORDS]
    return meaningful or terms


# Özetlerdeki LaTeX komutlarının düz metin karşılıkları
LATEX_SYMBOLS = {
    "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠", "approx": "≈",
    "cdot": "·", "times": "×", "otimes": "⊗", "pm": "±", "infty": "∞",
    "to": "→", "rightarrow": "→", "leftarrow": "←", "sim": "~", "bot": "⊥",
    "ldots": "…", "dots": "…", "in": "∈", "sum": "Σ", "prod": "Π",
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "theta": "θ", "lambda": "λ", "mu": "μ", "pi": "π",
    "sigma": "σ", "tau": "τ", "phi": "φ", "omega": "ω", "Omega": "Ω",
    "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Sigma": "Σ", "Phi": "Φ",
}


def clean_latex(text):
    r"""arXiv özetlerindeki LaTeX'i okunur düz metne çevirir.

    '$\mathrm{CRT}_{\mathrm{S}}(4)=\tfrac{3}{2}$' → 'CRT_S(4)=3/2'
    """
    if "$" not in text and "\\" not in text:
        return text
    # \mathrm{X}, \text{X} gibi yazı tipi komutları → X (iç içe olabilir)
    font = re.compile(r"\\(?:mathrm|mathbf|mathit|mathcal|mathbb|text|textrm|textbf|textit|operatorname)\{([^{}]*)\}")
    while font.search(text):
        text = font.sub(r"\1", text)
    # \frac{a}{b} → (a)/(b); tek parça ise parantezsiz
    def frac(match):
        top, bottom = match.group(1), match.group(2)
        top = top if len(top) == 1 else f"({top})"
        bottom = bottom if len(bottom) == 1 else f"({bottom})"
        return f"{top}/{bottom}"
    text = re.sub(r"\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}", frac, text)
    # Kaçışlı tek karakterler: \% → %, \& → &, \_ → _, \# → #
    text = re.sub(r"\\([%&_#])", r"\1", text)
    # Bilinen semboller; bilinmeyen komutun sadece \ işareti silinir
    text = re.sub(r"\\([A-Za-z]+)", lambda m: LATEX_SYMBOLS.get(m.group(1), m.group(1)), text)
    # Üs ve alt indis: x^{ab} → x^(ab), x_{ab} → x_ab
    text = re.sub(r"\^\{([^{}]*)\}", lambda m: "^" + (m.group(1) if len(m.group(1)) == 1 else f"({m.group(1)})"), text)
    text = re.sub(r"_\{([^{}]*)\}", r"_\1", text)
    # Kalan $, {, } işaretlerini sil
    text = text.replace("$", "").replace("{", "").replace("}", "")
    return " ".join(text.split())


def build_query(query, operator="AND"):
    """Terimleri arXiv sorgusuna çevirir.

    'spaced repetition' → 'all:spaced AND all:repetition'
    operator="OR" → 'all:spaced OR all:repetition'
    Çok kelimeli terim tam ifade olarak aranır: all:"university students"
    """
    return _join(query_terms(query), operator)


def _join(terms, operator):
    """Terim listesini 'all:a AND all:"b c"' biçimine çevirir."""
    parts = [f'all:"{term}"' if " " in term else f"all:{term}" for term in terms]
    return f" {operator} ".join(parts)


def to_record(entry):
    """arXiv kaydını (Atom <entry>) kayitlar.json biçimine çevirir."""
    # Başlık ve özette LaTeX matematik ifadeleri olabilir; düz metne çevir
    title = clean_latex(_text(entry, "atom:title"))
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
    abstract = clean_latex(_text(entry, "atom:summary"))
    if abstract:
        record["abstract"] = abstract
    return record


def parse_feed(xml_text):
    """API yanıtını kayıt listesine çevirir; okunamaz ya da hatalıysa None."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        print("Hata: arXiv yanıtı okunamadı.")
        return None
    records = []
    for entry in root.findall("atom:entry", NS):
        # Hatalı sorguda arXiv sonuç yerine bir "Error" kaydı döndürür
        if "/api/errors" in _text(entry, "atom:id"):
            print(f"Hata: arXiv sorguyu kabul etmedi ({_text(entry, 'atom:summary')}).")
            return None
        records.append(to_record(entry))
    # Başlığı olmayan kayıt zorunlu alanı karşılamaz, atla
    return [record for record in records if record["title"]]


def search_arxiv(query, max_results=10):
    """Arama ifadesiyle arXiv'de arar, kayıt listesi döndürür.

    Önce bütün terimlerin geçtiği makaleleri arar (AND). Sonuç çıkmazsa
    sondaki terimleri birer birer bırakarak tekrar dener; ilk terimler
    genelde konunun kendisidir ("spaced repetition university students"
    → "spaced repetition university" → "spaced repetition"). En son çare
    olarak terimlerden herhangi birini içerenleri arar (OR).
    """
    terms = query_terms(query)
    if not terms:
        print("Hata: arama ifadesi boş.")
        return []

    records = _fetch(_join(terms, "AND"), max_results)
    # Hata olduysa (None) yeni istek atma; sonuç yoksa terim azalt
    count = len(terms) - 1
    while records == [] and count >= 2:
        print(f"Sonuç yok; ilk {count} kelimeyle aranıyor: {' '.join(terms[:count])}")
        records = _fetch(_join(terms[:count], "AND"), max_results)
        count -= 1
    if records == [] and len(terms) > 1:
        print("Sonuç yok; kelimelerden herhangi biriyle aranıyor (sonuçlar alakasız olabilir)...")
        records = _fetch(_join(terms, "OR"), max_results)
    if records is None:
        return []
    if not records:
        print("Sonuç bulunamadı.")
    return records


def _fetch(search_query, max_results):
    """Tek bir API isteği atar. Hata olursa None, sonuç yoksa [] döner."""
    global _last_request
    params = {
        "search_query": search_query,
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
        return None
    except requests.exceptions.ConnectionError:
        print("Hata: internete bağlanılamadı.")
        return None
    except requests.exceptions.Timeout:
        print("Hata: arXiv zamanında yanıt vermedi.")
        return None
    except requests.exceptions.RequestException:
        print("Hata: istek gönderilemedi.")
        return None

    # Okunamayan ya da hata içeren yanıtta parse_feed mesajı kendisi yazar
    return parse_feed(response.text)


# Dosya doğrudan çalışınca bu blok çalışır, import'ta çalışmaz
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Kullanım: python arxiv.py "arama ifadesi"')
        sys.exit(1)
    for record in search_arxiv(sys.argv[1], max_results=5):
        print(f"- {record['title']} | yıl: {record.get('year', '-')} | DOI: {record.get('doi', '-')}")
