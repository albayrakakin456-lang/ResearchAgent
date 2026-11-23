"""analiz.py testleri: rakam kontrolü, numara doğrulama, bul_kanit, çelişkiler.

Model çağıran fonksiyonlarda gerçek model ÇAĞRILMAZ: analiz.ask
unittest.mock.patch ile sahte cevap veren bir fonksiyonla değiştirilir.
"""
import unittest
from unittest.mock import patch

from analiz import (_celiskileri_dogrula, _json_oku, _numaralari_dogrula,
                    bul_kanit, sayi_kontrol)
from llm import LLMError

# Üç cümlelik örnek özet (yapay örnek veri, gerçek yayın değil)
YAYIN = {
    "title": "ÖRNEK VERİ: Spacing study",
    "abstract": ("Students studied word lists. Spaced practice improved recall by 15%. "
                 "Massed practice did not."),
}


class SayiKontrolTest(unittest.TestCase):
    """c) Bulgudaki rakam dayanak cümlede yoksa listeye girmeli."""

    def test_eksik_rakam_listeye_girer(self):
        self.assertEqual(sayi_kontrol("Puan 30.8 ve 27.22 oldu.",
                                      ["The score rose to 30.8."]), ["27.22"])

    def test_alt_metin_eslesmez(self):
        # 30.8, 130.85'in içinde geçse de aynı sayı değil
        self.assertEqual(sayi_kontrol("Skor 30.8 oldu.", ["The score was 130.85."]), ["30.8"])

    def test_virgul_ve_nokta_eslesir(self):
        self.assertEqual(sayi_kontrol("Ortalama 27,22 çıktı.", ["The mean was 27.22."]), [])

    def test_hepsi_varsa_bos(self):
        self.assertEqual(sayi_kontrol("%45 düşüş, 0.8 etki.",
                                      ["A 45% drop; effect size 0.8."]), [])

    def test_dayanak_yoksa_hepsi_eksik(self):
        self.assertEqual(sayi_kontrol("15 ve 20", []), ["15", "20"])

    def test_tekrar_eden_rakam_bir_kez(self):
        self.assertEqual(sayi_kontrol("15, yine 15", []), ["15"])


class NumaralariDogrulaTest(unittest.TestCase):
    """d) Sadece 1..toplam aralığındaki tam sayılar geçerli."""

    def test_gecersizler_atilir_ve_sayilir(self):
        # 0 ve 9 aralık dışı, "2" metin, True bool, 1.5 ondalık
        gecerli, atilan = _numaralari_dogrula([1, 0, 9, "2", True, 1.5, 3], 3)
        self.assertEqual(gecerli, [1, 3])
        self.assertEqual(atilan, 5)

    def test_liste_degilse(self):
        self.assertEqual(_numaralari_dogrula("1,2", 3), ([], 0))
        self.assertEqual(_numaralari_dogrula(None, 3), ([], 0))

    def test_tekrar_eden_numara_bir_kez(self):
        gecerli, _ = _numaralari_dogrula([2, 2], 3)
        self.assertEqual(gecerli, [2])


class JsonOkuTest(unittest.TestCase):
    def test_kod_citi_ve_etrafinda_metin(self):
        self.assertEqual(_json_oku('Cevap:\n```json\n{"ilgili": true}\n```'), {"ilgili": True})

    def test_okunamayan(self):
        self.assertIsNone(_json_oku("bu bir JSON değil"))
        self.assertIsNone(_json_oku("[1, 2]"))  # sözlük değil


class BulKanitTest(unittest.TestCase):
    """e) bul_kanit: model cevabı ne olursa olsun çökmemeli."""

    @patch("analiz.ask", return_value='{"ilgili": true, "bulgu": "Aralıklı çalışma '
                                      'hatırlamayı %15 artırdı.", "cumle_numaralari": [2]}')
    def test_dogrulandi(self, sahte_ask):
        sonuc = bul_kanit("Aralıklı tekrar hatırlamayı etkiler mi?", YAYIN)
        self.assertEqual(sonuc["durum"], "doğrulandı")
        self.assertEqual(sonuc["gecerli"][0]["numara"], 2)
        self.assertIn("15%", sonuc["gecerli"][0]["cumle"])
        self.assertEqual(sonuc["kanitsiz_sayilar"], [])
        sahte_ask.assert_called_once()

    @patch("analiz.ask", return_value='{"ilgili": true, "bulgu": "Etki 40 puan.", '
                                      '"cumle_numaralari": [7, "2", true]}')
    def test_gecerli_numara_kalmazsa_dogrulanamadi(self, sahte_ask):
        sonuc = bul_kanit("soru", YAYIN)
        self.assertEqual(sonuc["durum"], "doğrulanamadı")
        self.assertEqual(sonuc["gecerli"], [])
        self.assertEqual(sonuc["atilan"], 3)
        # Dayanak yoksa bulgudaki rakam kanıtsız sayılır
        self.assertEqual(sonuc["kanitsiz_sayilar"], ["40"])

    @patch("analiz.ask", return_value="Üzgünüm, bunu yapamam.")
    def test_okunamayan_yanit(self, sahte_ask):
        sonuc = bul_kanit("soru", YAYIN)
        self.assertEqual(sonuc["durum"], "yanıt okunamadı")

    @patch("analiz.ask", return_value='{"ilgili": false}')
    def test_ilgisiz(self, sahte_ask):
        self.assertEqual(bul_kanit("soru", YAYIN)["durum"], "ilgisiz")

    @patch("analiz.ask", side_effect=LLMError("429 limit"))
    def test_model_hatasi(self, sahte_ask):
        sonuc = bul_kanit("soru", YAYIN)
        self.assertEqual(sonuc["durum"], "model hatası")
        self.assertIn("429", sonuc["not"])

    @patch("analiz.ask")
    def test_ozet_yoksa_model_cagrilmaz(self, sahte_ask):
        self.assertEqual(bul_kanit("soru", {"title": "T", "abstract": ""})["durum"], "özet yok")
        sahte_ask.assert_not_called()


class CeliskileriDogrulaTest(unittest.TestCase):
    """f) Var olmayan, kendisiyle eşleşen ve tekrar eden çiftler atılmalı."""

    def test_gecersiz_ciftler_atilir(self):
        ham = [
            {"yayin_a": 1, "yayin_b": 2, "aciklama": "zıt sonuç"},  # geçerli
            {"yayin_a": 2, "yayin_b": 1, "aciklama": "aynı çift ters"},  # tekrar
            {"yayin_a": 1, "yayin_b": 1, "aciklama": "kendisi"},  # a == b
            {"yayin_a": 1, "yayin_b": 5, "aciklama": "yok"},  # var olmayan
            {"yayin_a": True, "yayin_b": 2},  # bool
            "metin",  # sözlük değil
        ]
        gecerli, atilan = _celiskileri_dogrula(ham, 3)
        self.assertEqual(gecerli, [{"yayin_a": 1, "yayin_b": 2, "aciklama": "zıt sonuç"}])
        self.assertEqual(atilan, 5)


if __name__ == "__main__":
    unittest.main()
