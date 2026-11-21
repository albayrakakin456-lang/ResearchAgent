"""OpenAlex API anahtarının .env içinde olup olmadığını kontrol eder."""
import os

from dotenv import load_dotenv

# .env dosyasını oku ve değerleri ortam değişkenlerine yükle
load_dotenv()

# Anahtarı al; yoksa boş metin döner
key = os.getenv("OPENALEX_API_KEY", "").strip()

# Sadece var/yok bilgisini yaz, anahtarın kendisini asla yazdırma
print(f"anahtar bulundu: {'evet' if key else 'hayır'}")
