import requests
from bs4 import BeautifulSoup
import ollama
import re
import os


class AtilimAsistani:
    def __init__(self):
        self.html_content = ""

    def html_yukle(self, dosya_yolu):
        """HTML dosyasını yükler"""
        try:
            with open(dosya_yolu, 'r', encoding='utf-8') as f:
                self.html_content = f.read()
            return True
        except Exception as e:
            print(f"HTML yükleme hatası: {str(e)}")
            return False

    def icerik_isle(self):
        """HTML içeriğini temizler ve işler"""
        if not self.html_content:
            return ""

        try:
            soup = BeautifulSoup(self.html_content, 'html.parser')

            # Gereksiz elementleri kaldır
            for element in soup(['script', 'style', 'nav', 'footer',
                                 'header', 'iframe', 'form', 'meta', 'link']):
                element.decompose()

            # Ana içerik bölümünü bul
            main_content = soup.find('main') or soup.find(id='content') or soup

            # Önemli bilgileri çıkar
            elements = main_content.find_all(['h1', 'h2', 'h3', 'p', 'table', 'ul', 'li'])
            temiz_metin = '\n'.join([elem.get_text(' ', strip=True) for elem in elements])

            return temiz_metin[:10000]  # 10,000 karakterle sınırla

        except Exception as e:
            print(f"İçerik işleme hatası: {str(e)}")
            return ""

    def soru_cevapla(self, soru):
        """Kullanıcı sorusuna yanıt verir"""
        bilgi = self.icerik_isle()

        if not bilgi:
            return "Bilgi yüklenemedi. Lütfen HTML dosyasını kontrol edin."

        prompt = f"""
        SENARYO: Sen Atılım Üniversitesi'nin resmi bilgi asistanısın.

        GÖREVLER:
        1. SADECE aşağıdaki verilen bilgilere göre cevap ver
        2. Bilgi yoksa "Bu bilgi kaynaklarda bulunmuyor" de
        3. Asla tahmin yapma veya link önerme
        4. En fazla 2 cümle ile cevapla

        VERİLEN BİLGİLER:
        {bilgi}

        SORU: {soru}

        CEVAP:
        """

        try:
            response = ollama.chat(
                model='llama3',
                messages=[{'role': 'user', 'content': prompt}],
                options={
                    'temperature': 0.0,  # Tamamen bilgiye dayalı
                    'num_ctx': 2048
                }
            )

            cevap = response['message']['content'].strip()

            # Cevabı kontrol et
            if not cevap or len(cevap.split()) < 3:
                return "Bu bilgi kaynaklarda bulunmuyor"

            return cevap

        except Exception as e:
            return f"Sistem hatası: {str(e)}"


if __name__ == "__main__":
    # Asistanı oluştur
    asistan = AtilimAsistani()

    # HTML dosyasını yükle (script ile aynı dizinde olmalı)
    if not asistan.html_yukle('atilim_uni.html'):
        exit()

    print("\nAtılım Üniversitesi Bilgi Asistanına Hoş Geldiniz!")
    print("Çıkmak için 'çıkış' yazabilirsiniz.\n")

    while True:
        soru = input("\n\033[1mSoru:\033[0m ").strip()

        if soru.lower() in ['çıkış', 'exit', 'quit']:
            print("Görüşmek üzere!")
            break

        if not soru:
            print("Lütfen geçerli bir soru girin.")
            continue

        cevap = asistan.soru_cevapla(soru)
        print(f"\n\033[1mCevap:\033[0m {cevap}")
        print("-" * 60)