"""llm.py testleri: 429 (istek limiti) gelince bir kez tekrar deneme.

Gerçek istek atılmaz: requests.post ve time.sleep sahte (mock).
"""
import unittest
from unittest.mock import MagicMock, patch

import llm


def sahte_yanit(kod, govde=None, bekle=None):
    """requests.post'un döndürdüğü yanıtın sahtesi."""
    yanit = MagicMock()
    yanit.status_code = kod
    yanit.json.return_value = govde or {}
    yanit.headers = {} if bekle is None else {"retry-after": bekle}
    return yanit


class LimitTekrarTest(unittest.TestCase):

    @patch("llm.time.sleep")
    @patch("llm.requests.post")
    def test_429_sonra_basari(self, sahte_post, sahte_uyku):
        sahte_post.side_effect = [sahte_yanit(429, bekle="3"), sahte_yanit(200, {"ok": 1})]
        self.assertEqual(llm._post("http://x", {}), {"ok": 1})
        self.assertEqual(sahte_post.call_count, 2)
        sahte_uyku.assert_called_once_with(3.0)

    @patch("llm.time.sleep")
    @patch("llm.requests.post")
    def test_iki_kez_429_hata(self, sahte_post, sahte_uyku):
        sahte_post.side_effect = [sahte_yanit(429), sahte_yanit(429)]
        with self.assertRaises(llm.LLMError) as hata:
            llm._post("http://x", {})
        self.assertIn("429", str(hata.exception))
        # En fazla bir kez tekrar denenir
        self.assertEqual(sahte_post.call_count, 2)

    @patch("llm.time.sleep")
    @patch("llm.requests.post")
    def test_bekleme_ust_siniri(self, sahte_post, sahte_uyku):
        sahte_post.side_effect = [sahte_yanit(429, bekle="600"), sahte_yanit(200, {})]
        llm._post("http://x", {})
        sahte_uyku.assert_called_once_with(llm.LIMIT_BEKLEME_UST)

    @patch("llm.time.sleep")
    @patch("llm.requests.post")
    def test_bekleme_basligi_yoksa_5_sn(self, sahte_post, sahte_uyku):
        sahte_post.side_effect = [sahte_yanit(429), sahte_yanit(200, {})]
        llm._post("http://x", {})
        sahte_uyku.assert_called_once_with(5)

    @patch("llm.time.sleep")
    @patch("llm.requests.post")
    def test_diger_hatalar_tekrar_denenmez(self, sahte_post, sahte_uyku):
        sahte_post.return_value = sahte_yanit(401)
        with self.assertRaises(llm.LLMError):
            llm._post("http://x", {})
        self.assertEqual(sahte_post.call_count, 1)
        sahte_uyku.assert_not_called()


if __name__ == "__main__":
    unittest.main()
