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
