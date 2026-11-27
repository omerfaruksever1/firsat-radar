"""FırsatRadar — giriş noktası: sayfa ayarları, tema ve sol menü. Sayfalar `sayfalar/` klasöründedir.
Görünüm: tasarim/ klasörü ("Gece Terminali"), ortak CSS styles.py."""

import streamlit as st

import veritabani as db
from arayuz.giris import gizli_ayar, sifre_kontrolu
from arayuz.ortak import durum_karti, menu_hazirla, tema_uygula

st.set_page_config(page_title="FırsatRadar", page_icon=":material/radar:", layout="wide")
tema_uygula()

# İnternette yayınlanan sitede bu iki ayar Streamlit'in "secrets" bölümünden gelir. Bilgisayarda ikisi de
# yoktur: şifre sorulmaz ve firsat_radar.db dosyası kullanılır.
if adres := gizli_ayar("veritabani_adresi"):
    db.adres_ayarla(adres)
if sifre := gizli_ayar("site_sifresi"):
    sifre_kontrolu(sifre)

db.gunluk_yedek_al()
db.tablolari_olustur()

# Sol menüdeki sayaçlar: takipteki fırsat ve elde bekleyen ürün sayısı
menu_hazirla({"firsat-takibi": len(db.firsatlari_getir(db.TAKIPTE)), "elimdekiler": len(db.stoklari_getir())})

menu = {
    "": [
        st.Page("sayfalar/genel_bakis.py", title="Genel Bakış", default=True,
                help="Bu ayın özeti, aylık hedef, hızlı satış kaydı ve son satışlar."),
    ],
    "Alım-satım": [
        st.Page("sayfalar/firsat_takibi.py", title="Fırsat Takibi", url_path="firsat-takibi",
                help="Almayı düşündüğün ürünler: her kanaldaki satış kârı, en iyi fırsatlar, Claude'a sor."),
        st.Page("sayfalar/elimdekiler.py", title="Elimdekiler", url_path="elimdekiler",
                help="Aldığın ama henüz satmadığın ürünler; tek tıkla satışa dönüştür."),
        st.Page("sayfalar/satislarim.py", title="Satışlarım", url_path="satislarim",
                help="Satış ekle, düzenle, sil ve Excel'e aktar."),
        st.Page("sayfalar/giderler.py", title="Giderler", url_path="giderler",
                help="Ürüne bağlı olmayan masraflar: ambalaj, ilan ücreti, abonelik…"),
    ],
    "Analiz": [
        st.Page("sayfalar/raporlar.py", title="Raporlar", url_path="raporlar",
                help="Dönem seçerek ciro, maliyet, kâr, akıllı özet ve grafikler."),
        st.Page("sayfalar/fiyat_hesapla.py", title="Fiyat Hesapla", url_path="fiyat-hesapla",
                help="Hedef kârına göre her satış kanalında kaça satman gerektiğini hesaplar."),
    ],
    "Uygulama": [
        st.Page("sayfalar/ayarlar.py", title="Ayarlar", url_path="ayarlar",
                help="Satış kanalları, komisyon oranları, varsayılan kargo, aylık hedef ve yedekleme."),
        st.Page("sayfalar/yardim.py", title="Yardım", url_path="yardim",
                help="Uygulamanın nasıl kullanılacağı, yedekler ve sık sorulanlar."),
    ],
}

sayfa = st.navigation(menu)
durum_karti()
sayfa.run()
