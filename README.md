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

### 4. Sanal ortam ve paketler

Sanal ortam (`.venv`), projenin paketlerini bilgisayardaki diğer Python projelerinden ayrı tutar. Bir kez oluşturulur, her yeni terminalde açılır:

```powershell
py -m venv .venv
.venv\Scripts\activate
```

Açıldığında satırın başında `(.venv)` görünür. PowerShell "running scripts is disabled" hatası verirse bir kez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` çalıştırıp tekrar deneyin. macOS ve Linux'ta: `python3 -m venv .venv` ve `source .venv/bin/activate`.

Sonra paketleri kurun:

```powershell
py -m pip install -r requirements.txt
```

Bu komut `requests`, `python-dotenv` ve web arayüzü için `flask` paketlerini kurar. `requirements.txt` değiştiğinde (örneğin `git pull` sonrası yeni paket eklendiyse) tekrar çalıştırın.

### 5. API anahtarları (`.env`)

Her ekip üyesi kendi OpenAlex ve Groq anahtarını alır; anahtarlar kimseyle paylaşılmaz. `.env.example` dosyasını kopyalayıp adını `.env` yapın ve değerleri **`.env` içine** yazın:

```powershell
copy .env.example .env
```

`.env.example` GitHub'a gönderilen boş bir şablondur; içine asla gerçek anahtar yazmayın. `git status` çıktısında `.env.example` "modified" görünüyorsa `git restore .env.example` ile eski hâline döndürün (önce anahtarlarınızın `.env` içinde olduğundan emin olun).

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

**API anahtarları ve şifreler asla commit'lenmez.** `.env` dosyası `.gitignore` içinde olduğu için GitHub'a gönderilmez; yalnızca boş şablon olan `.env.example` gönderilir. `git add .` yerine değişen dosyaları tek tek ekleyin (`git add README.md tests/`). Bir anahtar yanlışlıkla GitHub'a giderse hemen iptal edilip yenisi alınmalıdır.

## Çalıştırma

Komutlar `ResearchAgent` klasöründe, sanal ortam açıkken çalıştırılır. macOS ve Linux'ta `py` yerine `python3` kullanın.

### Komut satırı

Rapor `--output` ile verilen dosyaya yazılır. `output/` klasörü GitHub'a gönderilmez.

| Ne yapmak istiyorsun | Gerekenler |
| --- | --- |
| `--source json` (varsayılan): demo kayıtlarıyla | İnternet ve anahtar gerekmez |
| `--source openalex`: OpenAlex'ten canlı arama | `OPENALEX_API_KEY` |
| `--source arxiv`: arXiv'den canlı arama | Anahtar gerekmez |
| `--analyze` ekleyerek bulgu, dayanak ve çelişki analizi | Groq anahtarı ya da Ollama |

```powershell
# Demo kayıtları: rapor "Benzersiz yayın kaydı 7" göstermeli
py researchagent.py --source json --input demo/kayitlar.json --output output/rapor.md

# OpenAlex + analiz
py researchagent.py --source openalex --query "spaced repetition university students" --analyze --output output/rapor_kanit.md

# arXiv
py researchagent.py --source arxiv --query "spaced repetition" --output output/rapor_arxiv.md
```

`--question "..."` ile rapora arama ifadesinden farklı bir soru başlığı yazılabilir. Demo kayıtlarında 14 kayıt 7 farklı yayına aittir; "Temsili" ile başlayanlar örnektir, diğerleri gerçek yayınlardır. `--analyze` özeti olan ilk 5 yayını analiz eder; demo kayıtlarında özet olmadığı için analiz OpenAlex ya da arXiv ile anlamlı sonuç verir.

Kaynakları tek başına denemek için: `py openalex.py "spaced repetition"` ve `py arxiv.py "spaced repetition"`.

### Web arayüzü

```powershell
py app.py
```

Ardından tarayıcıda [http://127.0.0.1:5000](http://127.0.0.1:5000) adresini açın. Arayüz soruyu önce modelle kontrol eder (araştırma sorusu değilse arama yapmaz), sonra arar ve analiz eder; bu yüzden Groq anahtarı gerekir.

- Durdurmak için terminalde `Ctrl+C`.
- Bir `.py` dosyası değiştiyse sunucuyu durdurup tekrar `py app.py` çalıştırın; `.js` ya da `.css` değiştiyse tarayıcıyı yenilemek yeterli.
- Aynı anda tek sunucu çalışsın: Windows aynı porta iki sunucunun bağlanmasına izin verebilir ve sayfa eski kodu gösterir. Kontrol: `Get-NetTCPConnection -LocalPort 5000 -State Listen`
- Groq'un ücretsiz limiti dolarsa (429, "model hatası") birkaç dakika bekleyin.

### Testler

```powershell
py -m unittest discover tests
```

Testler `tests/` klasöründedir ve Python'un hazır `unittest` modülünü kullanır. İnternet, API anahtarı ya da model gerektirmezler: modeli çağıran yerlerde `unittest.mock.patch` ile sahte cevap verilir. Sonuç `OK` olmalı; bir test bile başarısızsa commit atmayın.

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
