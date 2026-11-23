# Notlar – Yusuf

`demo/kayitlar.json` dosyasına gerçek yayınlarla yeni test kayıtları ekledim ve programı çalıştırdım. Testleri `git pull` sonrası güncel `researchagent.py` ile (OpenAlex ve `--analyze` eklenmiş sürüm) yaptım. Bu notta rapordaki hataları ve bulduğum diğer sorunları listeliyorum.

## Eklenen test kayıtları

Kayıtlar gerçek yayınlara ait. DOI'leri yayıncı sayfalarından ve PubMed'den kontrol ettim. Her yayın, farklı kaynaklardan gelmiş gibi birkaç kez ve farklı yazımlarla eklendi:

| Yayın | Kayıt sayısı | Neyi test ediyor |
| --- | --- | --- |
| Cepeda vd. (2006), Psychological Bulletin | 3 | `https://doi.org/` öneki, büyük/küçük harf, `doi:` öneki |
| Dunlosky vd. (2013), Psychological Science in the Public Interest | 2 | `http://dx.doi.org/` öneki, düz ve kıvrık kesme işareti (' ve ’) |
| Kang (2016), Policy Insights from the Behavioral and Brain Sciences | 2 | Aynı yayının bir kaydında DOI var, diğerinde yok |
| Carpenter vd. (2012), Educational Psychology Review | 2 | DOI yok; yıl bir kayıtta sayı (`2012`), diğerinde metin (`"2012"`) |
| Mawson ve Kang (2025), Behavioral Sciences | 2 | DOI'nin başında ve sonunda boşluk |

Eski üç temsili kaydı silmedim.

## Sonuç

Doğru sonuç **7** benzersiz yayın olmalıydı (2 temsili + 5 gerçek). Program **11** buldu, yani 4 yayın tekrar olarak listeleniyordu. (Düzeltildi, en alttaki "Düzeltme" bölümüne bakın.)

Doğru çalışanlar:
- `https://doi.org/` öneki ve büyük/küçük harf farkı (Cepeda, ilk iki kayıt).
- DOI'deki baştaki ve sondaki boşluklar (Mawson).

## Hatalar (researchagent.py – `unique_publications`)

1. **`doi:` öneki temizlenmiyor.** Cepeda'nın PubMed kaydı ayrı bir yayın sayılıyor. Rapordaki link de bozuk: `https://doi.org/doi:10.1037/...`; yeni eklenen `DOI:` metni de `DOI: doi:10.1037/...` olarak çıkıyor.
2. **`http://dx.doi.org/` öneki temizlenmiyor.** Sadece `https://doi.org/` siliniyor. Dunlosky'nin Crossref kaydı ayrı sayılıyor ve link bozuk: `https://doi.org/http://dx.doi.org/...` (`http://doi.org/` ve `dx.doi.org` biçimleri de aynı sorunu yaşar.) OpenAlex DOI'yi `https://doi.org/...` biçiminde verdiği için OpenAlex kayıtlarında sorun yok; sorun başka kaynaklar eklenince çıkacak.
3. **DOI'li ve DOI'siz kayıtlar hiç eşleşmiyor.** Anahtar DOI varsa `("doi", ...)`, yoksa `("metadata", ...)` olduğu için Kang (2016) iki ayrı yayın olarak görünüyor. Google Scholar gibi kaynaklar çoğu zaman DOI vermediği için bu durum gerçek veride sık çıkar.
4. **Yıl türü farklı olunca eşleşmiyor.** `2012` ile `"2012"` farklı anahtar oluyor (Carpenter).
5. **DOI'siz eşleştirmede başlık normalleştirmesi zayıf.** Sondaki nokta, kıvrık kesme işareti (’) veya `:` gibi noktalama farkları başlıkları farklı gösterir. Şu an sadece büyük/küçük harf ve fazla boşluk düzeltiliyor.

## Programı çökerten durumlar

Bunları `kayitlar.json`'a eklemedim, demo bozulmasın diye. Kısa Python testleriyle denedim:

| Kayıt | Hata |
| --- | --- |
| `"doi": null` | `AttributeError: 'NoneType' object has no attribute 'strip'` |
| `title` alanı yok | `KeyError: 'title'` |
| `"title": null` | `AttributeError: 'NoneType' object has no attribute 'casefold'` |
| `source` alanı yok | `KeyError: 'source'` |

`openalex.py` içindeki `to_record` bu `null` alanları zaten temizliyor ve başlıksız kayıtları atlıyor; OpenAlex yolu güvenli. Ama JSON yolunda (ve ileride eklenecek başka kaynaklarda) aynı koruma yok. Korumayı `unique_publications` içine de koymak (`record.get("doi") or ""`, başlık/kaynak yoksa kaydı atlamak) her kaynağı güvenli yapar.

## Diğer notlar

- **Türkçe "İ" harfi:** `"İngilizce".casefold()` sonucu `"i̇ngilizce"` (i + birleşik nokta) oluyor, `"ingilizce"` ile eşit değil. Türkçe başlıklı yayınlarda eşleştirme kaçabilir.
- **`--analyze` demo verisinde bir şey üretmiyor.** Demo kayıtlarında `abstract` alanı yok, bu yüzden 11 yayının hepsi "Özet yok" çıkıyor. Analizi denemek için `--source openalex` kullanmak gerekiyor (özetler oradan geliyor).
- **`split_sentences` küçük harfle başlayan cümleyi ayırmıyor.** Örneğin `"Results were robust (p < .05). however, effects varied."` tek cümle kalıyor. Fonksiyonun açıklamasında da yazıyor; özetlerde nadir, şimdilik sorun değil.
- **Olmayan dosya verilince** düz bir Python hatası (`FileNotFoundError` traceback) çıkıyor. Kullanıcıya anlaşılır bir mesaj vermek daha iyi olur.
- **`output/` klasörü `.gitignore`'da.** Bu yüzden `rapor.md` GitHub'a gönderilmiyor. Rapor çıktısını paylaşmak istersek ya bu notlara ekleyeceğiz ya da örnek bir raporu başka bir klasörde tutacağız.

## Düzeltme (22 Kasım) – `unique_publications`

Yukarıdaki 5 eşleştirme hatasını ve 4 çökme durumunu düzelttim. Demo artık doğru sonucu, **7** benzersiz yayını veriyor.

- **`normalize_doi`:** Küçük harfe çeviriyor, boşlukları siliyor ve `doi:`, `https://doi.org/`, `http://doi.org/`, `https://dx.doi.org/`, `http://dx.doi.org/`, `doi.org/`, `dx.doi.org/` öneklerini kaldırıyor. `None` gelirse boş metin döndürüyor.
- **`normalize_title`:** Büyük/küçük harf, noktalama, tırnak (’ ve ') ve fazla boşluk farklarını siliyor. Türkçe `İ` sorunu da çözüldü.
- **`normalize_year`:** `2012` ile `"2012"` aynı sayılıyor.
- **Eşleştirme sırası:** Önce DOI'ye bakılıyor. DOI yoksa ya da bulunamazsa başlık + yıla bakılıyor. DOI'siz kayıt, aynı başlık ve yıldaki DOI'li yayınla birleşiyor; kayıtların hangi sırayla geldiği önemli değil. İki kayıt aynı başlıkta ama farklı DOI'lerdeyse ayrı yayın sayılıyor (örneğin preprint ve dergi sürümü).
- **Eksik alanlar:** Başlığı olmayan kayıt bir uyarıyla atlanıyor, kaynağı olmayan kayıt "Bilinmeyen kaynak" oluyor; `null` alanlar artık çökertmiyor.
- **Yazar artık eşleştirme anahtarında değil.** Kaynaklar yazarı farklı yazıyor ("Cepeda" ve "Nicholas J. Cepeda" gibi); başlık + yıl yeterli.

Test ettiğim ek durumlar: DOI'siz kaydın DOI'li kayıttan önce gelmesi (birleşiyor), aynı başlık farklı DOI (ayrı kalıyor), aynı başlık farklı yıl (ayrı kalıyor).

Hâlâ açık olanlar: `split_sentences`'in küçük harfle başlayan cümleleri ayırmaması ve olmayan dosya verilince çıkan düz Python hatası (yukarıdaki "Diğer notlar").

## arXiv kaynağı (`arxiv.py`)

`openalex.py` örnek alınarak yazıldı; aynı kayıt biçimini döndürüyor (`title`, `source: "arXiv"`, varsa `doi`, `year`, `author`, `url`, `abstract`).

- **Anahtar gerekmiyor.** arXiv API'si ücretsiz ve kayıtsız. `.env`'ye bir şey eklemeye gerek yok.
- **Hız sınırı:** arXiv istekler arasında en az 3 saniye beklenmesini istiyor; kod art arda çağrılarda bunu kendisi bekliyor.
- **Arama (23 Kasım'da güncellendi):** Önce bütün kelimelerin geçtiği makaleler aranıyor (`all:spaced AND all:repetition`). Hiç sonuç çıkmazsa sondaki kelimeler birer birer bırakılarak tekrar aranıyor (`spaced repetition university students` → `spaced repetition university` → `spaced repetition`), çünkü ilk kelimeler genelde konunun kendisi. En son çare olarak kelimelerden herhangi birini içerenler aranıyor (`OR`). Denemede sadece OR kullanmak alakasız sonuçlar getirdi (fizik, kuantum makaleleri), bu yüzden OR en sona kondu. `in`, `the`, `how` gibi bağlaçlar sorgudan çıkarılıyor. Tırnak içindeki ifade tam ifade olarak aranıyor: `"spaced repetition" students` → `all:"spaced repetition" AND all:students`. Önceki sürümde 4 kelimelik sorgular 0 sonuç veriyordu (Akın buldu).
- **DOI:** Sadece dergide yayımlanmış makalelerde geliyor. DOI'si olan arXiv kaydı, aynı DOI'li OpenAlex kaydıyla `unique_publications` içinde birleşiyor (test ettim).
- **Bilinen sınır:** Preprint ile dergi sürümünün yılı farklıysa (örn. arXiv 2016, dergi 2017) ve arXiv kaydında DOI yoksa, ikisi ayrı yayın sayılır.
- **LaTeX temizliği:** arXiv özetleri matematik ifadelerini LaTeX ile yazıyor (`$\mathrm{CRT}_{\mathrm{S}}(4)=\tfrac{3}{2}$`). Raporda anlamsız karakterler çıkmasın diye `clean_latex` bunları düz metne çeviriyor (`CRT_S(4)=3/2`); `\leq`, `\alpha` gibi semboller ≤, α olarak yazılıyor.
- **Kapsam:** arXiv'de bilgisayar bilimi, yapay zekâ, fizik, matematik çok; psikoloji ve eğitim az. Demo sorumuz (aralıklı tekrar) için sonuç az gelebilir.

Tek başına denemek için:

```powershell
py arxiv.py "spaced repetition"
```

Akın `researchagent.py`'ye bağladı:

```powershell
py researchagent.py --source arxiv --query "spaced repetition" --output output/rapor.md
```

## İSTÜN kütüphane erişimi (salı görüşmesi öncesi)

Kaynak: İSTÜN kütüphane sitesi, [Abone Veritabanları](https://library.istun.edu.tr/en/subscribed-databases-1186) ve [Sıkça Sorulan Sorular](https://library.istun.edu.tr/en/sikca-sorulan-sorular-1154) sayfaları.

**Projeyle ilgili abonelikler:** ScienceDirect, Scopus, Web of Science, Springer Nature / SpringerLink, Wiley Online Library, Taylor & Francis, IEEE Xplore, JSTOR, Academic Search Ultimate, ERIC (eğitim – demo sorumuz için önemli), Medline.

**Kampüs dışı erişim:** Sadece VETİS. İSTÜN e-posta kullanıcı adı ve şifresiyle giriliyor; öğrenci, akademisyen ve personel kullanabiliyor.

**Kurallar (önemli):** Sitede otomatik indirme ve sistematik veri aktarımı "kesinlikle yasak" olarak yazıyor. İhlal hâlinde veritabanı erişimi kesilebiliyor, hukuki ve disiplin süreci başlayabiliyor. Ayrıca İSTÜN mensubu olmayanlarla içerik ya da giriş bilgisi paylaşmak yasak.

**Sonuç:** Ajanın VETİS üzerinden bu veritabanlarına otomatik girmesi yasak; denemiyoruz.

**Görüşmede sorulacaklar:**
1. Abonelik sözleşmeleri, araştırma projesi için metin ve veri madenciliğine (TDM) izin veriyor mu? Elsevier (Scopus, ScienceDirect), Springer Nature, Wiley ve IEEE gibi yayıncıların resmi API/TDM programları var; kütüphane bunlar için kurumsal erişim sağlayabilir mi?
2. Ajan makaleleri açık kaynaklardan (OpenAlex, arXiv) bulup sadece DOI linki gösterse, kullanıcı tam metne kendi VETİS girişiyle ulaşsa bu kabul edilebilir mi?
3. Proje için sınırlı, yazılı izin alınabilecek bir süreç veya muhatap kişi var mı?

**Görüşme sonucu:** (salıdan sonra buraya yazılacak)

## 24 Kasım: testler, düzeltmeler, elle test

### Otomatik testler (`tests/`)

`py -m unittest discover tests` → 50 test, hepsi geçiyor. İnternet, API anahtarı ya da model gerektirmiyor; modeli çağıran yerlerde (`analiz.ask`, `analiz.soru_kontrol_et`, `arxiv._fetch`) `unittest.mock.patch` ile sahte cevap veriliyor.

- `test_researchagent.py`: `unique_publications` (DOI yazımları, DOI'siz eşleşme, `None` değerler), `split_sentences` (et al., ondalık sayı, tırnakla biten cümle), `calistir` (kısa girdi ve "araştırma sorusu değil" durumunda model/arama çağrılmıyor).
- `test_analiz.py`: `sayi_kontrol`, `_numaralari_dogrula`, `_json_oku`, `bul_kanit` (doğrulandı / doğrulanamadı / yanıt okunamadı / ilgisiz / model hatası / özet yok), `_celiskileri_dogrula`, `celiski_bul`.
- `test_arxiv.py`: `clean_latex`, `build_query`, `search_arxiv` arama sırası.

Testlerin hata yakaladığını kontrol etmek için koda bilerek hata ekledim (DOI öneki, rakam eşleşmesi); ilgili testler kırmızı yandı.

### Düzeltilen hatalar (her biri ayrı commit, kendi testiyle)

1. **`split_sentences` "Asymp. Sig." ifadesini bölüyordu** (`researchagent.py`, kısaltma listesi). Endonezce bir özette "Asymp." / "Sig." / "(2-tailed)…" üç ayrı cümle oluyordu; model öznesi olmayan parçayı dayanak seçmişti. `Asymp` ve `Sig` kısaltma listesine eklendi. Düzeltmeden sonra model düzgün İngilizce cümleleri seçti.
2. **`clean_latex` kaçışlı karakterleri temizlemiyordu** (`arxiv.py`). LECTOR özetinde `90.2\%` kalıyordu. `\%`, `\&`, `\_`, `\#` artık düz karaktere çevriliyor.
3. **Çelişki analizi başarısız olunca sebebi görünmüyordu** (`researchagent.py` `render_celiskiler` ve `calistir`, `analiz.py` `celiski_bul`). Rapor sadece "Çelişki analizi yapılamadı" diyordu. Artık "Neden: İstek limiti doldu (429)…" ya da "Neden: Model yanıtı okunamadı." satırı raporda ve web'de görünüyor. Fonksiyon adları ve parametreleri değişmedi.
4. **arXiv'de "spaced" kelimesi "space" ile eşleşiyordu** (`arxiv.py` `search_arxiv`). arXiv kelimeleri köküne indirdiği için "spaced repetition" aramasında sonsuz evren, string algoritması gibi alakasız makaleler geliyordu. Artık önce tam ifade aranıyor (`all:"spaced repetition"`), sonuç yoksa eski kademeli arama devam ediyor. Düzeltmeden sonra 10 sonucun hepsi konuyla ilgili.

### Elle test sonuçları

- Demo JSON: "Benzersiz yayın kaydı 7", doğru.
- OpenAlex + `--analyze`: 10 yayın, ilk 5'i analiz edildi; Pakistan çalışmasında bulgudaki 27.93, 30.8, 0.8 dayanak cümlede birebir var. Çelişki adımı 429'a takıldı ve sebep raporda göründü.
- arXiv: 10 sonucun hepsi aralıklı tekrarla ilgili, LaTeX kalıntısı yok.
- Web arayüzü (`py app.py`): "naber" → kırmızı "en az 3 kelime"; "günüm çok kötüydü" → sadece sarı "araştırma sorusu değil" mesajı, kaynak yok; gerçek soru → kartlar, "dayanak doğrulandı" rozeti, "Dayanak cümleleri" düğmesinde sarı vurgu, model hatası kartında 429 mesajı, PDF olarak kaydet ve Markdown indir çalışıyor.

### Akın için öneriler (düzeltmedim)

- **Groq 429:** 5 analiz + çelişki (web'de + soru kontrolü) art arda yapılınca ücretsiz dakikalık limit doluyor. Web'de 4. yayın, komut satırında çelişki adımı "model hatası" oldu. Öneri: `llm.ask` içinde 429 gelince birkaç saniye bekleyip bir kez tekrar denemek.
- **"resp." kısaltması** da cümleyi bölüyor ("(resp. 90%)"). Aynı türden; `ABBREVIATION` listesine eklenebilir.
- **Boşluksuz cümleler:** Bazı OpenAlex özetlerinde nokta sonrası boşluk yok ("acquisition.HLR combines"), bütün özet tek cümle oluyor. Veriden kaynaklı; düzeltmek "e.g." gibi yazımları bozabileceği için dokunmadım.
- **`.env.example` uyarısı:** Kurulumda anahtarlar yanlışlıkla `.env.example`'a yazılabiliyor (bende oldu, commit'lenmeden fark edildi). README'ye uyarı ekledim.
