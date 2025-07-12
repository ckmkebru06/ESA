import requests
from bs4 import BeautifulSoup
import ollama
import re
import json


class AtilimAsistani:
    def __init__(self):
        self.url_listesi = {
            "genel": "https://www.atilim.edu.tr/tr",
            "iletisim": "https://www.atilim.edu.tr/tr/oim/page/5666/iletisim",
            "rektorluk": "https://www.atilim.edu.tr/tr/home/page/4048/rektorluk",
            "akreditasyon": "https://www.atilim.edu.tr/tr/home/page/2954/akreditasyonlarimiz",
            "ucret": "https://www.atilim.edu.tr/tr/mali-isler-ve-butce-direktorlugu/page/2901/egitim-ogretim-ucretleri",
            "takvim": "https://www.atilim.edu.tr/tr/oim/page/5977/akademik-takvim-2024-2025",
            "bilgisayar": "https://www.atilim.edu.tr/tr/compe/page/1595/akademik-personel",
            "yazilim": "https://www.atilim.edu.tr/tr/se/page/2286/akademik-personel",
            "makine": "https://www.atilim.edu.tr/tr/me/page/2290/akademik-personel",
            "mufredat": "https://www.atilim.edu.tr/tr/compe/page/1598/mufredat"
        }
        self.tum_icerik = {}
        self._tum_icerikleri_yukle()

    def _tum_icerikleri_yukle(self):
        for isim, url in self.url_listesi.items():
            try:
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                resp.encoding = "utf-8"
                soup = BeautifulSoup(resp.text, "html.parser")

                if isim == "mufredat":
                    icerik = self._mufredat_ayikla(soup)
                elif "akademik-personel" in url:
                    icerik = self._akademik_personel_ayikla(soup)
                else:
                    icerik = self._genel_sayfa_ayikla(soup)

                self.tum_icerik[isim] = icerik
            except Exception as e:
                self.tum_icerik[isim] = {}

    def _mufredat_ayikla(self, soup):
        dersler_by_donem = {}

        for card in soup.find_all("a", class_="lesson_card"):
            try:
                data_str = card.get("data-lesson-data", "")
                data_json = json.loads(data_str)

                donem = str(data_json.get("semester"))
                kod = data_json.get("code", "")
                ad = data_json.get("name", "")
                teori = data_json.get("theory", 0)
                uygulama = data_json.get("practice", 0)
                akts = data_json.get("akts", 0)

                satir = f"{kod} | {ad} | Teorik: {teori} | Uygulama: {uygulama} | AKTS: {akts}"
                if donem not in dersler_by_donem:
                    dersler_by_donem[donem] = []
                dersler_by_donem[donem].append(satir)
            except Exception:
                continue

        return dersler_by_donem

    def _genel_sayfa_ayikla(self, soup):
        for tag in soup(["script", "style", "nav", "footer", "header", "iframe", "form", "meta", "link"]):
            tag.decompose()
        metinler = [tag.get_text(" ", strip=True) for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "p", "li"])]
        return " ".join(metinler)

    def _akademik_personel_ayikla(self, soup):
        icerik = []

        kartlar = soup.find_all("div", class_="staff-academician")
        for kart in kartlar:
            isim_tag = kart.find("h4", class_="colorRed")
            if isim_tag:
                isim = isim_tag.get_text(" ", strip=True)
                if isim:
                    icerik.append(isim)

        tablolar = soup.find_all('table')
        for tablo in tablolar:
            for satir in tablo.find_all('tr'):
                hucreler = [hucre.get_text(" ", strip=True) for hucre in satir.find_all(['td', 'th'])]
                if hucreler:
                    icerik.append(" | ".join(hucreler))

        return "\n".join(icerik)

    def _ilgili_kaynak(self, soru):
        s = soru.lower()
        if any(x in s for x in ["müfredat", "ders programı", "hangi ders", "curriculum"]):
            return "mufredat"
        if any(x in s for x in ["bölüm başkanı", "başkan yardımcısı", "vice chair", "head"]):
            if "yazılım" in s:
                return "yazilim"
            elif "bilgisayar" in s:
                return "bilgisayar"
            elif "makine" in s:
                return "makine"
        if "akademik kadro" in s or "personel" in s:
            if "yazılım" in s:
                return "yazilim"
            elif "bilgisayar" in s:
                return "bilgisayar"
            elif "makine" in s:
                return "makine"
        if any(x in s for x in ["iletişim", "telefon", "konum"]):
            return "iletisim"
        if any(x in s for x in ["rektör", "rektörlük"]):
            return "rektorluk"
        if "akreditasyon" in s:
            return "akreditasyon"
        if "ücret" in s or "fiyat" in s:
            return "ucret"
        if "takvim" in s or "sınav" in s:
            return "takvim"
        return "genel"

    def _donem_no_bul(self, soru):
        soru = soru.lower()
        eslesmeler = {
            "1": ["1", "birinci", "ilk"],
            "2": ["2", "ikinci"],
            "3": ["3", "üçüncü"],
            "4": ["4", "dördüncü"],
            "5": ["5", "beşinci"],
            "6": ["6", "altıncı"],
            "7": ["7", "yedinci"],
            "8": ["8", "sekizinci"]
        }
        for sayi, kaliplar in eslesmeler.items():
            if any(k in soru for k in kaliplar):
                return sayi
        return None

    def soru_cevapla(self, soru: str):
        soru = soru.strip()
        if not soru:
            return "Lütfen geçerli bir soru giriniz."

        konu = self._ilgili_kaynak(soru)

        if konu == "mufredat":
            donem_no = self._donem_no_bul(soru)
            data = self.tum_icerik.get("mufredat", {})
            if not data:
                return "Müfredat bilgisi bulunamadı."
            if donem_no in data:
                dersler = data[donem_no]
                return f"{donem_no}. Yarıyıl dersleri:\n" + "\n".join(dersler)
            return "Belirtilen döneme ait müfredat bulunamadı."

        icerik = self.tum_icerik.get(konu, "")
        if not icerik:
            return "Bu konuda elimde bilgi bulunmamaktadır."

        prompt = f"""AŞAĞIDAKİ VERİYE GÖRE SORUYU CEVAPLA. SADECE TÜRKÇE CEVAP VER. KISA, NET, MAKS 3 CÜMLELİK CEVAP OLSUN.

METİN:
{icerik}

SORU: {soru}
CEVAP:"""

        try:
            yanit = ollama.chat(
                model="llama3",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1}
            )
            return yanit["message"]["content"].strip()
        except Exception as e:
            return f"Hata oluştu: {e}"


if __name__ == "__main__":
    print("Atılım Üniversitesi Bilgi Asistanı (Türkçe)")
    print("Çıkmak için: çıkış\n")

    asistan = AtilimAsistani()

    while True:
        soru = input("\nSoru: ").strip()
        if soru.lower() in ["çıkış", "exit", "quit"]:
            break

        cevap = asistan.soru_cevapla(soru)
        print(f"\nYanıt: {cevap}\n{'-' * 50}")
