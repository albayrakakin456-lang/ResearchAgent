# ResearchAgent

ResearchAgent, bir araştırma sorusu için akademik kaynakları taramayı ve rapordaki ana bulguları ilgili makale pasajlarına bağlamayı hedefler.

## İlk çalıştırma

Python 3.10 veya üzeri gerekir. VS Code'da bu klasörü açıp terminalde çalıştırın.

```powershell
py researchagent.py --input demo/kayitlar.json --output output/rapor.md
```

macOS ve Linux'ta `py` yerine `python3` kullanın. Beklenen sonuç iki benzersiz yayın kaydıdır. Örnek DOI ve yayınlar temsilidir. Bu sürüm yerel JSON okur ve Markdown raporu yazar. Canlı kaynak bağlantıları ve pasaj doğrulama sonraki geliştirme işleridir.

## Ekip çalışması

1. GitHub davetini kabul edin ve VS Code'da Git: Clone ile depoyu açın.
2. Trello kartınızı seçin. Araştırma notlarının bağlantısını kartta paylaşın.
3. Kod değişikliği yapacaksanız güncel main üzerinden işinize özel bir dal açın. Örnek dal adı `h2/kaynak-taramasi`.
4. Değişiklikleri çalıştırıp kontrol edin, commit yapın ve dalınızı GitHub'a gönderin.
5. Main'e doğru bir Pull Request açın. Açıklamaya Trello kartı bağlantısını ve nasıl test ettiğinizi ekleyin. Bir ekip üyesinden inceleme isteyin.
6. İnceleme ve birleştirme tamamlanınca Trello kartını kapatın.

## İlk geliştirme işleri

| İş | İlk çıktı |
| --- | --- |
| Literatür | Aynı demo sorusuna ait doğrulanabilir yayın kayıtları ve sorgular |
| Kaynak erişimi | İki kaynağın yanıtlarını ortak kayıt biçimine dönüştürme |
| Yayın kayıtları | Yinelenen ve DOI'siz kayıtlar için eşleştirme örnekleri |
| Kanıt | İddia, yayın, bölüm veya sayfa ve pasajı içeren örnek kayıt |
| Arayüz | Soru girişi, rapor ve kanıt ayrıntısı taslağı |
| Test | Tekrar, yalnız özet, kaynak hatası ve desteksiz bulgu senaryoları |


Akın buradaydı