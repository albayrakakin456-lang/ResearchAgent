"""researchagent.py testleri: yayın birleştirme ve cümle bölme.

Çalıştırma (proje klasöründe): py -m unittest discover tests
İnternet, API anahtarı ya da model GEREKMEZ.
"""
import contextlib
import io
import unittest
from unittest.mock import patch

from researchagent import calistir, split_sentences, unique_publications


def birlestir(kayitlar):
    """unique_publications'ı çağırır; ekrana yazdığı uyarıları gizler."""
    with contextlib.redirect_stdout(io.StringIO()):
        return unique_publications(kayitlar)


class UniquePublicationsTest(unittest.TestCase):
    """a) Aynı yayının farklı kayıtları tek yayında birleşmeli."""

    def test_doi_yazimlari_tek_yayin(self):
        # Aynı DOI'nin bütün yazım biçimleri
        kayitlar = [
            {"title": "A", "doi": "10.1037/0033-2909.132.3.354", "source": "OpenAlex"},
            {"title": "A", "doi": "doi:10.1037/0033-2909.132.3.354", "source": "PubMed"},
            {"title": "A", "doi": "https://doi.org/10.1037/0033-2909.132.3.354", "source": "S2"},
            {"title": "A", "doi": "http://dx.doi.org/10.1037/0033-2909.132.3.354", "source": "Crossref"},
            {"title": "A", "doi": "  10.1037/0033-2909.132.3.354  ", "source": "Bosluk"},
            {"title": "A", "doi": "10.1037/0033-2909.132.3.354".upper(), "source": "Buyuk"},
        ]
        yayinlar = birlestir(kayitlar)
        self.assertEqual(len(yayinlar), 1)
        self.assertEqual(yayinlar[0]["doi"], "10.1037/0033-2909.132.3.354")
        self.assertEqual(yayinlar[0]["url"], "https://doi.org/10.1037/0033-2909.132.3.354")
        self.assertEqual(len(yayinlar[0]["sources"]), 6)

    def test_doisiz_kayit_baslik_ve_yila_gore_birlesir(self):
        kayitlar = [
            {"title": "Using Spacing to Enhance Learning", "year": 2012, "source": "S2"},
            # Büyük/küçük harf, noktalama ve yıl türü farklı
            {"title": "using spacing to enhance learning.", "year": "2012", "source": "Scholar"},
        ]
        yayinlar = birlestir(kayitlar)
        self.assertEqual(len(yayinlar), 1)
        self.assertEqual(yayinlar[0]["sources"], ["S2", "Scholar"])

    def test_doisiz_kayit_doili_kayitla_birlesir(self):
        # Sıra fark etmemeli: önce DOI'siz, sonra DOI'li kayıt
        kayitlar = [
            {"title": "Spaced Repetition Promotes Learning", "year": 2016, "source": "Scholar"},
            {"title": "Spaced repetition promotes learning", "year": 2016,
             "doi": "10.1177/2372732215624708", "source": "OpenAlex"},
        ]
        yayinlar = birlestir(kayitlar)
        self.assertEqual(len(yayinlar), 1)
        self.assertEqual(yayinlar[0]["doi"], "10.1177/2372732215624708")

    def test_farkli_yil_ayri_yayin(self):
        kayitlar = [
            {"title": "Same Title", "year": 2020, "source": "A"},
            {"title": "Same Title", "year": 2021, "source": "B"},
        ]
        self.assertEqual(len(birlestir(kayitlar)), 2)

    def test_farkli_doi_ayri_yayin(self):
        # Aynı başlık ama farklı DOI (örn. preprint ve dergi sürümü)
        kayitlar = [
            {"title": "Same Title", "year": 2020, "doi": "10.1/a", "source": "A"},
            {"title": "Same Title", "year": 2020, "doi": "10.1/b", "source": "B"},
        ]
        self.assertEqual(len(birlestir(kayitlar)), 2)

    def test_none_degerlerde_cokmez(self):
        kayitlar = [
            {"title": "X", "doi": None, "year": None, "source": None,
             "url": None, "abstract": None},
            {"title": None, "doi": "10.1/x", "source": "A"},  # başlıksız: atlanır
            {"doi": "10.1/y"},                                 # title anahtarı yok
        ]
        yayinlar = birlestir(kayitlar)
        self.assertEqual(len(yayinlar), 1)
        self.assertEqual(yayinlar[0]["doi"], "")
        self.assertEqual(yayinlar[0]["sources"], ["Bilinmeyen kaynak"])


class SplitSentencesTest(unittest.TestCase):
    """b) Özet cümlelere doğru bölünmeli."""

    def test_normal_cumleler_bolunur(self):
        metin = "Spacing helps memory. It works for students! Does it last? Yes."
        self.assertEqual(split_sentences(metin), [
            "Spacing helps memory.", "It works for students!", "Does it last?", "Yes.",
        ])

    def test_et_al_bolmez(self):
        metin = "Cepeda et al. (2006) reviewed 317 experiments. Spacing helped."
        self.assertEqual(split_sentences(metin), [
            "Cepeda et al. (2006) reviewed 317 experiments.", "Spacing helped.",
        ])

    def test_et_al_buyuk_harfle_devam_bolmez(self):
        metin = "As Smith et al. Showed earlier, spacing works. Second sentence."
        self.assertEqual(len(split_sentences(metin)), 2)

    def test_ondalik_sayi_bolmez(self):
        metin = "The correlation was 0.867 in the spaced group. Effects were large."
        self.assertEqual(split_sentences(metin), [
            "The correlation was 0.867 in the spaced group.", "Effects were large.",
        ])

    def test_tirnakla_biten_cumle(self):
        metin = 'Data came from the "National Institute." The sample was large.'
        self.assertEqual(split_sentences(metin), [
            'Data came from the "National Institute."', "The sample was large.",
        ])

    def test_bos_metin(self):
        self.assertEqual(split_sentences(""), [])
        self.assertEqual(split_sentences("   "), [])


class CalistirGirisKontrolTest(unittest.TestCase):
    """Web arayüzü: kısa ya da boş girdi modele hiç gitmemeli."""

    @patch("analiz.soru_kontrol_et")
    def test_kisa_girdi_modele_gitmez(self, sahte_kontrol):
        sonuc = calistir("naber")
        self.assertIn("en az 3 kelime", sonuc["hata"])
        self.assertEqual(sonuc["yayinlar"], [])
        sahte_kontrol.assert_not_called()

    @patch("analiz.soru_kontrol_et")
    def test_bos_girdi(self, sahte_kontrol):
        sonuc = calistir("   ")
        self.assertTrue(sonuc["hata"])
        sahte_kontrol.assert_not_called()

    @patch("analiz.soru_kontrol_et",
           return_value={"uygun": False, "neden": "Kişisel durum.", "arama_ifadesi": ""})
    def test_arastirma_sorusu_degilse_arama_yapilmaz(self, sahte_kontrol):
        # Kaynak aramasını da sahte yapıyoruz: çağrılırsa test kırılsın
        with patch("openalex.search_openalex") as sahte_arama:
            sonuc = calistir("günüm çok kötüydü bugün")
        self.assertIn("araştırma sorusu değil", sonuc["uyari"])
        self.assertEqual(sonuc["yayinlar"], [])
        sahte_arama.assert_not_called()


if __name__ == "__main__":
    unittest.main()
