"""arxiv.py testleri: LaTeX temizliği ve sorgu oluşturma. İnternet gerekmez."""
import unittest

from arxiv import build_query, clean_latex


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


if __name__ == "__main__":
    unittest.main()
