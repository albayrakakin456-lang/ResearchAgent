"""Tek bir ask() fonksiyonuyla Groq ya da Ollama'ya soru sorar."""
import os
import re
import sys
import time

import requests
from dotenv import load_dotenv

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/chat"
# Her istek için en çok 120 sn bekle
TIMEOUT = 120


class LLMError(Exception):
    """Model çağrısında oluşan, Türkçe mesajlı hata."""


def _messages(prompt, system):
    # Sistem mesajı varsa sohbetin başına ekle
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def _post(url, payload, headers=None):
    """İstek atar; ağ ve HTTP hatalarını Türkçe mesaja çevirir."""
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
    except requests.exceptions.ConnectionError:
        raise LLMError("Bağlantı kurulamadı. İnterneti ya da Ollama'nın açık olduğunu kontrol et.")
    except requests.exceptions.Timeout:
        raise LLMError(f"Model {TIMEOUT} saniyede yanıt vermedi.")
    except requests.exceptions.RequestException:
        raise LLMError("İstek gönderilirken beklenmeyen bir hata oluştu.")

    code = response.status_code
    if code == 404:
        raise LLMError("Model bulunamadı (404). Model adını .env'de kontrol et.")
    if code == 429:
        raise LLMError("İstek limiti doldu (429). Biraz bekleyip tekrar dene.")
    if code in (401, 403):
        raise LLMError(f"Anahtar reddedildi ({code}). GROQ_API_KEY'i kontrol et.")
    if code >= 400:
        raise LLMError(f"Model servisi hata döndürdü ({code}).")
    try:
        return response.json()
    except ValueError:
        raise LLMError("Servisten okunamayan bir yanıt geldi.")


def _ask_groq(prompt, system, temperature=None):
    # Anahtar yoksa istek atmadan anlaşılır hata ver
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise LLMError("GROQ_API_KEY bulunamadı. .env dosyasına anahtarını yaz.")
    payload = {
        "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        "messages": _messages(prompt, system),
        # Verilmediyse eski varsayılan (0.2) kalır
        "temperature": 0.2 if temperature is None else temperature,
    }
    # Anahtar adrese değil başlığa yazılır, hiçbir yere basılmaz
    headers = {"Authorization": f"Bearer {api_key}"}
    data = _post(GROQ_URL, payload, headers)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("Groq yanıtı beklenen biçimde değil.")


def _ask_ollama(prompt, system, temperature=None):
    payload = {
        "model": os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        "messages": _messages(prompt, system),
        # Cevap parça parça değil, tek seferde gelsin
        "stream": False,
    }
    # Ollama'da eski davranış "ayar yok"; sadece verilirse ekle
    if temperature is not None:
        payload["options"] = {"temperature": temperature}
    data = _post(OLLAMA_URL, payload)
    try:
        text = data["message"]["content"]
    except (KeyError, TypeError):
        raise LLMError("Ollama yanıtı beklenen biçimde değil.")
    # <think>...</think> düşünme kısmını sil (satır atlasa da)
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def ask(prompt, system=None, temperature=None):
    """Seçili sağlayıcıya soruyu sorar, cevap metnini döndürür."""
    # .env değerlerini ortama yükle
    load_dotenv()
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    if provider == "groq":
        return _ask_groq(prompt, system, temperature)
    if provider == "ollama":
        return _ask_ollama(prompt, system, temperature)
    raise LLMError(f"Bilinmeyen LLM_PROVIDER: '{provider}'. 'groq' ya da 'ollama' yaz.")


# Dosya doğrudan çalışınca bu blok çalışır, import'ta çalışmaz
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Kullanım: py llm.py "sorun"')
        sys.exit(1)
    start = time.time()
    try:
        answer = ask(sys.argv[1])
    except LLMError as error:
        print(f"Hata: {error}")
        sys.exit(1)
    print(answer)
    print(f"\n(Süre: {time.time() - start:.1f} sn)")
