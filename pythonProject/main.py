import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from langchain.prompts import PromptTemplate
from langchain_mistralai.chat_models import ChatMistralAI
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel
import time

# 🔑 API Key
API_KEY = "lo1LjGVmdgjhOhCpo31zr4IatKXEeLHI"

# 🎯 Mistral AI Modeli
llm = ChatMistralAI(
    mistral_api_key=API_KEY,
    model="mistral-tiny",
    temperature=0.3,
    max_tokens=300
)


# 📌 Doğru Sayfa Seçme Fonksiyonu
def uygun_web_sayfasi(soru):
    soru = soru.lower()

    fakulte_sayfalari = {
        "mühendislik": "https://www.atilim.edu.tr/tr/foe",
        "fen edebiyat": "https://www.atilim.edu.tr/tr/fef",
        "hukuk": "https://www.atilim.edu.tr/tr/hukuk",
        "işletme": "https://www.atilim.edu.tr/tr/isletme",
        "sağlık bilimleri": "https://www.atilim.edu.tr/tr/sbf",
        "taban puan": "https://www.kariyer.net/universite-taban-puanlari/atilim-universitesi"
    }

    for fakulte, url in fakulte_sayfalari.items():
        if fakulte in soru:
            return url

    return "https://www.atilim.edu.tr/tr"


# 🌍 **Selenium ile Kariyer.net'ten Taban Puanı Çekme**
def taban_puanlari_cek():
    site_url = "https://www.kariyer.net/universite-taban-puanlari/atilim-universitesi"

    # Chrome Headless Mode (Arka planda çalıştırmak için)
    chrome_options = Options()
    chrome_options.add_argument("--headless")

    # WebDriver başlat
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(site_url)

    time.sleep(5)  # Sayfanın yüklenmesini bekle

    # Sayfadaki tabloyu bul
    try:
        table = driver.find_element("xpath", "//table")
        rows = table.find_elements("tag name", "tr")[1:6]  # İlk 5 satır
        taban_puanlar = [row.text for row in rows]

        driver.quit()  # Tarayıcıyı kapat
        return "\n".join(taban_puanlar)
    except Exception as e:
        driver.quit()
        return f"Taban puan bilgisi çekilemedi: {e}"


# 🌍 **Web'den Bilgi Çekme Fonksiyonu**
def webden_bilgi_cek(soru):
    if "taban puan" in soru or "puanı kaç" in soru:
        return taban_puanlari_cek()

    site_url = uygun_web_sayfasi(soru)
    try:
        response = requests.get(site_url, timeout=5)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = [p.get_text(strip=True) for p in soup.find_all(["p", "h1", "h2"])]

        return " ".join(paragraphs)[:1500] if paragraphs else "Web sitesinde yeterli bilgi bulunamadı."
    except requests.exceptions.RequestException as e:
        return f"Bilgi çekilemedi. Hata: {e}"


# 🚀 **Prompt Mühendisliği**
template = """
Sen Atılım Üniversitesi hakkında bilgi veren bir asistansın.
Sorulara doğru ve güncel bilgilerle cevap vermeye odaklan.
Eğer bilgi yetersizse, cevap vermediğini belirt.
Sadece verilen bilgiler doğrultusunda konuş, tahmin yapma.

Eğer taban puanı sorulursa, kariyer.net üzerindeki verilere bakarak doğru bilgi ver.
Eğer üniversitenin kuruluş yılı gibi kesin tarihi sorulursa ve verdiğin bilgilerde yoksa, "Bu konuda elimde kesin bir bilgi yok" diyerek cevap ver.

🎓 **Üniversite Bilgileri**:
{bilgi}

📌 **Soru**: {soru}
📝 **Yanıt**:
"""

prompt = PromptTemplate(input_variables=["bilgi", "soru"], template=template)

# 💾 Bellek Yönetimi
message_history = ChatMessageHistory()
memory = ConversationBufferMemory(chat_memory=message_history)

# 🔗 LangChain Akışı
chain = (
        {"bilgi": RunnablePassthrough(), "soru": RunnablePassthrough()}
        | prompt
        | llm
)


# 🗣 **Chatbot Yanıt Fonksiyonu**
def chatbot_sor(soru):
    okul_bilgisi = webden_bilgi_cek(soru)
    yanit = chain.invoke({"bilgi": okul_bilgisi, "soru": soru})

    memory.save_context({"input": soru}, {"output": str(yanit)})

    return f"🔹 **Soru**: {soru}\n💡 **Yanıt**: {yanit}"


# ✅ **Test Çalıştırma**
print(chatbot_sor("Bilgisayar mühendisliği bölümü hakkında bilgi verir misin?"))
print(chatbot_sor("Atılım Üniversitesi kaç yılında kuruldu?"))
print(chatbot_sor("Hukuk Fakültesi'nde hangi dersler var?"))
print(chatbot_sor("Atılım Üniversitesi tıp ffakültesi taban puanı nedir?"))
