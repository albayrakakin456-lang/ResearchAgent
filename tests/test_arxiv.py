"""arxiv.py testleri: LaTeX temizliği ve sorgu oluşturma. İnternet gerekmez."""
import contextlib
import io
import unittest
from unittest.mock import patch

from arxiv import build_query, clean_latex, search_arxiv


class CleanLatexTest(unittest.TestCase):
    """g) arXiv özetlerindeki LaTeX düz metne çevrilmeli."""

    def test_yazi_tipi_ve_kesir(self):
        self.assertEqual(clean_latex(r"$\mathrm{CRT}_{\mathrm{S}}(4)=\tfrac{3}{2}$"),
                         "CRT_S(4)=3/2")

    def test_semboller(self):
        self.assertEqual(clean_latex(r"$x \leq y$ and $\alpha \cdot \beta$"),
                         "x ≤ y and α · β")

    def test_us(self):
        self.assertEqual(clean_latex(r"$(1 - ε^{3/2})^{n}$"), "(1 - ε^(3/2))^n")

    def test_kacisli_karakterler(self):
        # Gerçek bir arXiv özetinde "90.2\%" olarak kalıyordu
        self.assertEqual(clean_latex(r"a 90.2\% success rate"), "a 90.2% success rate")
        self.assertEqual(clean_latex(r"R\&D"), "R&D")

    def test_latexsiz_metin_degismez(self):
        metin = "Spaced repetition improved recall by 15%."
        self.assertEqual(clean_latex(metin), metin)

    def test_kalinti_kalmaz(self):
        sonuc = clean_latex(r"We prove $\mathrm{val}^*(G^{\otimes n}) \geq \frac{1}{2}$.")
        for karakter in "$\\{}":
            self.assertNotIn(karakter, sonuc)


class BuildQueryTest(unittest.TestCase):
    def test_baglaclar_atilir(self):
        self.assertEqual(build_query("how does spacing affect the memory"),
                         "all:spacing AND all:affect AND all:memory")

    def test_tirnakli_ifade(self):
        self.assertEqual(build_query('"spaced repetition" students', "OR"),
                         'all:"spaced repetition" OR all:students')



class SearchArxivTest(unittest.TestCase):
    """Arama sırası: önce tam ifade. Gerçek istek atılmaz, _fetch sahte."""

    def ara(self, sorgu, cevaplar):
        """Her _fetch çağrısında sıradaki sahte cevabı verir, sorguları döndürür."""
        with patch("arxiv._fetch", side_effect=cevaplar) as sahte, \
                contextlib.redirect_stdout(io.StringIO()):
            sonuc = search_arxiv(sorgu)
        return sonuc, [cagri.args[0] for cagri in sahte.call_args_list]

    def test_once_tam_ifade(self):
        # "spaced" kelimesi tek başına aranınca "space" ile de eşleşiyordu
        sonuc, sorgular = self.ara("spaced repetition", [[{"title": "T"}]])
        self.assertEqual(sorgular, ['all:"spaced repetition"'])
        self.assertEqual(len(sonuc), 1)

    def test_tam_ifade_bos_donerse_kelimelerle(self):
        _, sorgular = self.ara("spaced repetition", [[], [{"title": "T"}]])
        self.assertEqual(sorgular, ['all:"spaced repetition"', "all:spaced AND all:repetition"])

    def test_dort_kelimede_iki_kelimelik_tam_ifadeye_iner(self):
        _, sorgular = self.ara("spaced repetition university students",
                               [[], [], [], [{"title": "T"}]])
        self.assertEqual(sorgular[-1], 'all:"spaced repetition"')

    def test_hata_olunca_yeni_istek_atilmaz(self):
        sonuc, sorgular = self.ara("spaced repetition", [None])
        self.assertEqual(sonuc, [])
        self.assertEqual(len(sorgular), 1)


if __name__ == "__main__":
    unittest.main()
