import ollama
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time

# 📌 **Fakülteler ve Bölümler İçin Web Sayfaları**
FAKULTE_SAYFALARI = {
    "mühendislik": "https://www.atilim.edu.tr/tr/foe",
    "fen edebiyat": "https://www.atilim.edu.tr/tr/artsci",
    "güzel sanatlar tasarım ve mimarlık": "https://www.atilim.edu.tr/tr/gsf",
    "hukuk": "https://www.atilim.edu.tr/tr/law",
    "işletme": "https://www.atilim.edu.tr/tr/fom",
    "sağlık bilimleri": "https://www.atilim.edu.tr/tr/sbf",
    "sivil havacılık": "https://www.atilim.edu.tr/tr/shyo"
}

# 📌 **Doğru Web Sayfasını Seçme**
def uygun_web_sayfasi(soru):
    soru = soru.lower()
    for fakulte, url in FAKULTE_SAYFALARI.items():
        if fakulte in soru:
            return url
    return "https://www.atilim.edu.tr/tr"

# 🌍 **Selenium ile Taban Puanları Çekme**
def taban_puanlari_cek():
    site_url = "https://www.kariyer.net/universite-taban-puanlari/atilim-universitesi"

    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Görünmez modda çalıştır

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(site_url)
    time.sleep(5)

    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        table = soup.find("table")

        if not table:
            return "⚠️ Taban puan bilgisi bulunamadı."

        rows = table.find_all("tr")[1:6]  # İlk 5 bölümü al
        taban_puanlar = [row.get_text(strip=True) for row in rows]

        driver.quit()
        return "\n".join(taban_puanlar)
    except Exception as e:
        driver.quit()
        return f"⚠️ Hata: {e}"

# 🌍 **Web'den Bilgi Çekme**
def webden_bilgi_cek(soru):
    if "taban puan" in soru or "puanı kaç" in soru:
        return taban_puanlari_cek()

    site_url = uygun_web_sayfasi(soru)
    print(f"🔍 Veri çekmeye çalışılan URL: {site_url}")

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(site_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = [p.get_text(strip=True) for p in soup.find_all(["p", "h1", "h2"])]

        if not paragraphs:
            return "⚠️ Web sitesinde yeterli bilgi bulunamadı."

        temizlenmis_bilgi = " ".join(paragraphs)[:1500]  # İlk 1500 karakteri al

        return temizlenmis_bilgi
    except requests.exceptions.RequestException as e:
        return f"⚠️ Bilgi çekilemedi. Hata: {e}"

# 🚀 **Ollama ile Chatbot**
def chatbot_sor(soru):
    okul_bilgisi = webden_bilgi_cek(soru)

    prompt = f"""
    🎓 Sen Atılım Üniversitesi hakkında bilgi veren bir asistansın.
    ✅ **Sadece web sitesinden gelen bilgilere dayalı olarak cevap ver.**
    ❌ **Eğer bilgi bulamazsan, 'Bu konuda elimde kesin bir bilgi yok' de.**
    📌 **Kaynak olmadan tahminde bulunma!**

    🔎 **Sorulan Soru**:
    {soru}

    📝 **Çekilen Bilgi**:
    {okul_bilgisi}

    🔍 **Yanıtın**:
    """

    yanit = ollama.chat(model="llama3", messages=[{"role": "user", "content": prompt}])
    return f"🔹 **Soru**: {soru}\n💡 **Yanıt**: {yanit['message']['content']}"

# ✅ **Test Çalıştırma**
print(chatbot_sor("Bilgisayar mühendisliği bölümü hakkında bilgi verir misin?"))
print(chatbot_sor("Atılım Üniversitesi kaç yılında kuruldu?"))
print(chatbot_sor("Hukuk Fakültesi'nde hangi dersler var?"))
print(chatbot_sor("Atılım Üniversitesi tıp fakültesi taban puanı nedir?"))
