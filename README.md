# ResearchAgent

ResearchAgent, bir araştırma sorusu için akademik kaynakları taramayı ve rapordaki ana bulguları ilgili makale pasajlarına bağlamayı hedefler.

## Kurulum

### 1. Gerekli programlar

| Program | Nereden | Not |
| --- | --- | --- |
| Python 3.10 veya üzeri | [python.org/downloads](https://www.python.org/downloads/) | Windows'ta kurulumun ilk ekranında **Add python.exe to PATH** kutusunu işaretleyin. |
| Git | [git-scm.com](https://git-scm.com/) | Varsayılan ayarlarla kurulabilir. |
| VS Code | [code.visualstudio.com](https://code.visualstudio.com/) | Python eklentisi önerilir. |

Kurulumu kontrol etmek için VS Code'da **Terminal → New Terminal** açıp şunları yazın. İkisi de sürüm numarası göstermeli:

```powershell
py --version
git --version
```

### 2. Git'i bir kez tanıtın

```powershell
git config --global user.name "Adınız"
git config --global user.email "github-hesabinizdaki@eposta.com"
```

E-posta GitHub hesabınızdakiyle aynı olmalı, yoksa commit'ler profilinizde görünmez.

### 3. Depoyu indirin

GitHub davetini kabul edin. Ardından ya VS Code'da `Ctrl+Shift+P` → **Git: Clone** ile depoyu seçin ya da terminalde:

```powershell
git clone https://github.com/MuhammetOmerd/ResearchAgent.git
cd ResearchAgent
```

GitHub girişi istenirse tarayıcıdan onaylayın. Bundan sonraki bütün komutlar bu `ResearchAgent` klasörünün içinde çalıştırılır. Terminal başka bir klasördeyse `git` komutları `fatal: not a git repository` hatası verir.

### 4. Paketleri kurun

```powershell
py -m pip install -r requirements.txt
```

Bu komut `requests` ve `python-dotenv` paketlerini kurar. Yalnızca demo JSON ile çalışmak için gerekmez; OpenAlex ve `--analyze` için gerekir.

### 5. API anahtarları (`.env`)

`.env.example` dosyasını kopyalayıp adını `.env` yapın ve içindeki değerleri doldurun:

```powershell
copy .env.example .env
```

| Değişken | Ne için | Nereden |
| --- | --- | --- |
| `OPENALEX_API_KEY` | OpenAlex araması (`--source openalex`) | [openalex.org](https://openalex.org) hesabı → [openalex.org/settings/api](https://openalex.org/settings/api) (ücretsiz) |
| `LLM_PROVIDER` | Analiz modeli: `groq` ya da `ollama` | — |
| `GROQ_API_KEY`, `GROQ_MODEL` | `groq` seçiliyse | [console.groq.com](https://console.groq.com) (ücretsiz katman) |
| `OLLAMA_MODEL` | `ollama` seçiliyse, model kendi bilgisayarınızda çalışır | [ollama.com](https://ollama.com) kurulup model indirilmeli, örn. `ollama pull qwen3:8b` |

Anahtarları kontrol etmek için:

```powershell
py check_key.py
py llm.py "Merhaba, tek cümleyle kendini tanıt."
```

İlki OpenAlex anahtarının bulunup bulunmadığını söyler (anahtarı ekrana yazmaz); ikincisi seçili modelden bir cevap almalıdır.

**API anahtarları ve şifreler asla commit'lenmez.** `.env` dosyası `.gitignore` içinde olduğu için GitHub'a gönderilmez; yalnızca boş şablon olan `.env.example` gönderilir. Bir anahtar yanlışlıkla GitHub'a giderse hemen iptal edilip yenisi alınmalıdır.

## Çalıştırma

Rapor `--output` ile verilen dosyaya yazılır. `output/` klasörü GitHub'a gönderilmez. macOS ve Linux'ta `py` yerine `python3` kullanın.

**Demo JSON ile (internet ve anahtar gerekmez):**

```powershell
py researchagent.py --input demo/kayitlar.json --output output/rapor.md
```

Demo kayıtlarında 14 kayıt var ve bunlar 7 farklı yayına ait; rapor 7 benzersiz yayın göstermelidir. Eşleştirmenin nasıl çalıştığı ve test edilen durumlar `notlar-yusuf.md` dosyasında. "Temsili" ile başlayan yayınlar ve DOI'leri örnektir; diğer kayıtlar gerçek yayınlardır.

**OpenAlex'ten canlı arama:**

```powershell
py researchagent.py --source openalex --query "spaced repetition university students" --question "Üniversite öğrencilerinde aralıklı tekrar hatırlamayı nasıl etkiler?" --output output/rapor.md
```

**Özet analizi ile (dil modeli gerekir):** Komutun sonuna `--analyze` ekleyin. Model, özeti olan ilk 5 yayında soruyla ilgili bulguyu ve dayanak cümle numaralarını çıkarır. Demo JSON kayıtlarında özet olmadığı için analiz yalnızca OpenAlex ile anlamlı sonuç verir.

OpenAlex aramasını tek başına denemek için: `py openalex.py "spaced repetition"`

## Ekip çalışması

1. GitHub davetini kabul edin ve VS Code'da Git: Clone ile depoyu açın.
2. Trello kartınızı seçin. Araştırma notlarının bağlantısını kartta paylaşın.
3. Çalışmaya başlamadan önce `git pull` (VS Code'da **Sync**) ile güncel hâli alın.
4. Kod değişikliği yapacaksanız güncel main üzerinden işinize özel bir dal açın. Örnek dal adı `h2/kaynak-taramasi`.
5. Değişiklikleri çalıştırıp kontrol edin, commit yapın ve dalınızı GitHub'a gönderin.
6. Main'e doğru bir Pull Request açın. Açıklamaya Trello kartı bağlantısını ve nasıl test ettiğinizi ekleyin. Bir ekip üyesinden inceleme isteyin.
7. İnceleme ve birleştirme tamamlanınca Trello kartını kapatın.

## İlk geliştirme işleri

| İş | İlk çıktı |
| --- | --- |
| Literatür | Aynı demo sorusuna ait doğrulanabilir yayın kayıtları ve sorgular |
| Kaynak erişimi | İki kaynağın yanıtlarını ortak kayıt biçimine dönüştürme |
| Yayın kayıtları | Yinelenen ve DOI'siz kayıtlar için eşleştirme örnekleri |
| Kanıt | İddia, yayın, bölüm veya sayfa ve pasajı içeren örnek kayıt |
| Arayüz | Soru girişi, rapor ve kanıt ayrıntısı taslağı |
| Test | Tekrar, yalnız özet, kaynak hatası ve desteksiz bulgu senaryoları |
