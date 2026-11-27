"""Ekran testleri: uygulama, geçici bir veritabanıyla gerçek bir Streamlit sunucusunda başlatılır ve
Streamlit'in "agent API"si ile tarayıcısız gezilir (sayfa değiştirme, form doldurma, düğme ve pencereler).

Not: Bu arayüz tablodan satır seçmeyi desteklemez; testler kaydı tablonun altındaki seçim kutusundan seçer.
"""

from datetime import date, timedelta

import pytest

from arayuz_yardimci import sunucu
from conftest import satis

SAYFALAR = ["", "firsat-takibi", "elimdekiler", "satislarim", "giderler", "raporlar", "fiyat-hesapla",
            "ayarlar", "yardim"]


@pytest.fixture(scope="module")
def uygulama(tmp_path_factory):
    with sunucu(tmp_path_factory.mktemp("arayuz") / "test.db") as u:
        yield u


@pytest.fixture
def vt_ayni(uygulama, monkeypatch):
    """Testin, sunucunun kullandığı veritabanına doğrudan veri ekleyebilmesi için."""
    import veritabani as db
    monkeypatch.setattr(db, "VERITABANI_YOLU", uygulama.db_yolu)
    monkeypatch.setattr(db, "VERITABANI_ADRESI", None)
    return db


def test_01_bos_veritabaninda_tum_sayfalar_acilir(uygulama):
    for sayfa in SAYFALAR:
        assert uygulama.sayfa(sayfa).cevap["status"] == "ready", sayfa


def test_02_genel_bakis_satis_ekle_penceresi(uygulama, vt_ayni):
    ekran = uygulama.sayfa()
    assert ekran.kpi_sayisi() == 5
    assert "Kaydet" not in ekran.dugme_etiketleri()  # sayfada büyük satış formu yok
    ekran = ekran.tikla("Satış ekle")
    assert ekran.tur("dialog")
    ekran = ekran.tikla("Satışı kaydet")
    assert "Lütfen ürün adını yazın." in ekran.metinler("error")
    ekran = ekran.doldur(yeni_urun="Laptop standı", yeni_alis=310.0, yeni_satis=649.0, yeni_kargo=60.0,
                         yeni_adet=2, yeni_durum="İkinci el", yeni_kaynak="Toptancı A")
    ekran = ekran.doldur(yeni_komisyon=71.0)
    assert any("₺416,00" in m for m in ekran.metinler("markdown"))  # canlı kâr önizlemesi
    ekran = ekran.tikla("Satışı kaydet")
    assert "“Laptop standı” kaydedildi. Satış kârı: ₺416,00" in ekran.metinler("success")
    assert ekran.icerir("Laptop standı ×2")  # Son satışlar listesinde
    r = vt_ayni.satislari_getir().iloc[0]
    assert (r.durum, r.kaynak, r.tarih.date()) == ("İkinci el", "Toptancı A", date.today())


def test_03_yeni_satis_penceresi_ve_otomatik_komisyon(uygulama, vt_ayni):
    tablo = vt_ayni.kanallari_getir()
    tablo.loc[tablo.ad == "Dolap", "komisyon_orani"] = 10
    vt_ayni.kanallari_kaydet(tablo)
    ekran = uygulama.sayfa("satislarim").tikla("Yeni satış")
    assert ekran.tur("dialog")
    ekran = ekran.doldur(yeni_satis=250.0).doldur(yeni_pazar="Dolap")
    assert ekran.deger("yeni_komisyon") == 25.0
    ekran = ekran.doldur(yeni_urun="Kot ceket", yeni_alis=80.0, yeni_durum="İkinci el", yeni_kargo=0.0,
                         yeni_kategori="Vintage giyim", yeni_kaynak="Bit pazarı", yeni_notlar="Hafif yıpranmış")
    ekran = ekran.tikla("Satışı kaydet")
    assert any("“Kot ceket” kaydedildi. Satış kârı: ₺145,00" in m for m in ekran.metinler("success"))
    r = vt_ayni.satislari_getir().query("urun_adi == 'Kot ceket'").iloc[0]
    assert (r.kategori, r.kaynak, r.notlar, r.komisyon) == ("Vintage giyim", "Bit pazarı", "Hafif yıpranmış", 25)


def test_04_turkce_arama_zarar_ve_donem_filtresi(uygulama, vt_ayni):
    vt_ayni.satis_ekle(satis(urun_adi="İphone kılıfı"))
    vt_ayni.satis_ekle(satis(urun_adi="Zararlı satış", satis_fiyati=50, gun_once=20))
    ekran = uygulama.sayfa("satislarim").doldur(st_arama="iphone")
    assert ekran.tur("dataframe")[0]["data"]["row_count"] == 1
    ekran = ekran.doldur(st_arama="", st_zarar=True)
    tum = vt_ayni.satislari_getir()
    assert ekran.tur("dataframe")[0]["data"]["row_count"] == (tum["net_kar"] < 0).sum()
    ekran = ekran.doldur(st_zarar=False, st_donem="Bu hafta")
    bu_hafta = date.today() - timedelta(days=date.today().weekday())
    assert ekran.tur("dataframe")[0]["data"]["row_count"] == (tum["tarih"].dt.date >= bu_hafta).sum()
    assert ekran.icerir("satış gösteriliyor")


def test_05_satis_duzenleme_ve_silme_penceresi(uygulama, vt_ayni):
    vt_ayni.satis_ekle(satis(urun_adi="Silinecek ürün"))
    kayit_id = int(vt_ayni.satislari_getir().iloc[0].id)
    ekran = uygulama.sayfa("satislarim").sec("st_secili", f"No {kayit_id} ·").tikla("Düzenle / sil")
    assert ekran.deger(f"duzenle_{kayit_id}_urun") == "Silinecek ürün"
    ekran = ekran.doldur(**{f"duzenle_{kayit_id}_adet": 7}).tikla("Değişiklikleri kaydet")
    assert f"No {kayit_id} güncellendi." in ekran.metinler("success")
    assert vt_ayni.satislari_getir().query("id == @kayit_id").iloc[0].adet == 7

    ekran = ekran.sec("st_secili", f"No {kayit_id} ·").tikla("Düzenle / sil").tikla("Sil")
    assert any("silmek istediğine emin misin" in m for m in ekran.metinler("warning"))
    ekran = ekran.tikla("Evet, sil")
    assert "Kayıt silindi." in ekran.metinler("success")
    assert vt_ayni.satislari_getir().query("id == @kayit_id").empty


def test_06_elimdekiler_ekle_sat_ve_geri_al(uygulama, vt_ayni):
    ekran = uygulama.sayfa("elimdekiler")
    assert ekran.icerir("Elinde bekleyen ürün yok")
    ekran = ekran.tikla("Elimdekiler'e ekle")  # form sayfanın sağında, sürekli açık
    assert "Lütfen ürün adını yazın." in ekran.metinler("error")
    ekran = ekran.doldur(stok_yeni_urun="Deri çanta", stok_yeni_alis=150.0, stok_yeni_adet=3,
                         stok_yeni_hedef=420.0, stok_yeni_durum="İkinci el", stok_yeni_kaynak="Komşu")
    assert ekran.icerir("+₺810,00")  # hedef fiyattan kalan önizlemesi: (420 − 150) × 3
    ekran = ekran.tikla("Elimdekiler'e ekle")
    assert "“Deri çanta” Elimdekiler'e eklendi." in ekran.metinler("success")
    assert ekran.kpi_sayisi() == 3
    assert ekran.deger("stok_yeni_urun") == ""  # form temizlendi
    stok_id = int(vt_ayni.stoklari_getir().iloc[0].id)

    ekran = ekran.sec("el_secili", "Deri çanta").tikla("Sat")
    onek = f"stok_sat_{stok_id}"
    assert ekran.deger(f"{onek}_urun") == "Deri çanta"  # stok bilgileri hazır gelir
    assert ekran.deger(f"{onek}_alis") == 150.0 and ekran.deger(f"{onek}_satis") == 420.0
    ekran = ekran.doldur(**{f"{onek}_adet": 2, f"{onek}_pazar": "Elden", f"{onek}_kargo": 0.0,
                            f"{onek}_komisyon": 0.0}).tikla("Satışı kaydet")
    assert any("“Deri çanta” satıldı. Satış kârı: ₺540,00" in m for m in ekran.metinler("success"))
    assert vt_ayni.stoklari_getir().iloc[0].kalan == 1
    satis_id = int(vt_ayni.satislari_getir().query("urun_adi == 'Deri çanta'").iloc[0].id)

    # Stoktan yapılan satış silinince ürünler Elimdekiler'e geri döner
    ekran = uygulama.sayfa("satislarim").sec("st_secili", f"No {satis_id} ·").tikla("Düzenle / sil")
    assert any("Elimdekiler'den yapıldı" in m for m in ekran.metinler("caption"))
    ekran.tikla("Sil").tikla("Evet, sil")
    assert vt_ayni.stoklari_getir().iloc[0].kalan == 3


def test_07_stok_duzenle_ve_sil(uygulama, vt_ayni):
    stok_id = int(vt_ayni.stoklari_getir().iloc[0].id)
    ekran = uygulama.sayfa("elimdekiler").sec("el_secili", "Deri çanta").tikla("Düzenle / sil")
    ekran = ekran.doldur(**{f"stok_duzenle_{stok_id}_hedef": 0.0}).tikla("Değişiklikleri kaydet")
    assert vt_ayni.stoklari_getir().iloc[0].hedef_fiyat == 0
    ekran = ekran.sec("el_secili", "Deri çanta").tikla("Düzenle / sil").tikla("Sil").tikla("Evet, sil")
    assert "Ürün Elimdekiler'den silindi." in ekran.metinler("success")
    assert vt_ayni.stoklari_getir().empty


def test_08_giderler(uygulama, vt_ayni):
    ekran = uygulama.sayfa("giderler")
    assert ekran.icerir("Henüz gider yok")
    ekran = ekran.tikla("Kaydet")  # form sayfanın sağında, sürekli açık
    assert "Tutar 0'dan büyük olmalı." in ekran.metinler("error")
    ekran = ekran.doldur(gider_tutar=180.0, gider_aciklama="Kargo poşeti").tikla("Kaydet")
    assert "₺180,00 gider kaydedildi." in ekran.metinler("success")
    assert vt_ayni.giderleri_getir().iloc[0].kategori == "Ambalaj"  # varsayılan kategori
    assert ekran.icerir("giderleri") and ekran.icerir("₺180")
    ekran = ekran.sec("gd_secili", "₺180,00").tikla("Evet, sil")
    assert "Gider silindi." in ekran.metinler("success")
    assert vt_ayni.giderleri_getir().empty
    vt_ayni.gider_ekle(dict(tarih=date.today(), kategori="Ambalaj", tutar=100))


def test_09_raporlar_donemler_sekmeler_ve_yorumlar(uygulama, vt_ayni):
    vt_ayni.satis_ekle(satis(gun_once=35, urun_adi="Eski satış"))
    ekran = uygulama.sayfa("raporlar")
    assert ekran.kpi_sayisi() == 5
    assert ekran.icerir("−₺100")  # Giderler kartı
    assert len(ekran.tur("altair_chart")) == 2
    assert len(ekran.tur("code")) == 1  # Claude'a sor metni
    assert any("₺100 ek giderin var" in m for m in ekran.metinler("markdown"))
    for donem in ["Geçen ay", "Son 30 gün", "Bu yıl", "Tümü"]:
        ekran = ekran.doldur(rp_donem=donem)
    ekran = ekran.doldur(rp_donem="Özel")
    bugun = date.today()
    ekran = ekran.doldur(rp_ozel=[str(bugun - timedelta(days=400)), str(bugun - timedelta(days=380))])
    assert ekran.icerir("Bu dönemde satış yok")
    ekran = ekran.doldur(rp_donem="Tümü").doldur(rp_sekme="Ürün yorumu").doldur(rp_urun_sec="Kot ceket")
    assert any("Kot ceket" in m for m in ekran.metinler("code"))


def test_10_fiyat_hesapla(uygulama, vt_ayni):
    ekran = uygulama.sayfa("fiyat-hesapla")
    assert ekran.icerir("alış fiyatını")
    ekran = ekran.doldur(fh_alis=300.0, fh_kargo=45.0, fh_hedef_marj=25.0)
    tablo = ekran.tur("dataframe")[0]["data"]
    assert tablo["row_count"] == len(vt_ayni.kanal_adlari())
    assert ekran.icerir("%25 kâr için önerilen satış fiyatı") and ekran.icerir("En düşük fiyat: Elden")
    ekran = ekran.doldur(fh_hizli="%30")  # hızlı seçim hedef marjı doldurur
    assert ekran.deger("fh_hedef_marj") == 30.0
    ekran = ekran.doldur(fh_mod="Fiyattan kâr hesapla").doldur(fh_fiyat=500.0)
    assert ekran.icerir("₺500 fiyattan her kanalda kâr") and ekran.icerir("En çok kazandıran")


def test_11_ayarlar_varsayilanlar_ve_genel_bakis_hedefi(uygulama, vt_ayni):
    ekran = uygulama.sayfa("ayarlar").doldur(ay_kargo=45.0, ay_hedef=5000.0).tikla("Kaydet")
    assert "Varsayılanlar kaydedildi." in ekran.metinler("success")
    assert (vt_ayni.ayar_getir("varsayilan_kargo"), vt_ayni.ayar_getir("aylik_hedef")) == ("45.0", "5000.0")
    ekran = uygulama.sayfa()
    assert ekran.icerir("Hedef ₺5.000")  # Satış kârı kartında aylık hedef ilerlemesi
    ekran = ekran.tikla("Satış ekle")
    assert ekran.deger("yeni_kargo") == 45.0  # varsayılan kargo yeni formlarda hazır


def test_12_dolu_veritabaninda_tum_sayfalar_acilir(uygulama, vt_ayni):
    vt_ayni.stok_ekle(dict(urun_adi="Bekleyen", alis_fiyati=10, adet=1, alis_tarihi=date.today() - timedelta(days=70)))
    for sayfa in SAYFALAR:
        assert uygulama.sayfa(sayfa).cevap["status"] == "ready", sayfa
    assert any((uygulama.db_yolu.parent / "yedekler").glob("otomatik_*.db"))  # otomatik günlük yedek


def test_13_firsat_takibi_ekle_degerlendir_satin_al(uygulama, vt_ayni):
    ekran = uygulama.sayfa("firsat-takibi")
    assert ekran.icerir("Takip listen boş")
    ekran = ekran.tikla("Fırsat ekle").tikla("Listeye ekle")
    assert "Lütfen ürün adını yazın." in ekran.metinler("error")
    assert ekran.deger("firsat_yeni_kargo") == 45.0  # Ayarlar'daki varsayılan kargo
    ekran = ekran.doldur(firsat_yeni_urun="iPhone 13", firsat_yeni_alis=1000.0, firsat_yeni_piyasa=1500.0,
                         firsat_yeni_durum="İkinci el", firsat_yeni_kaynak="Sahibinden",
                         firsat_yeni_link="sahibinden.com/ilan/1")
    # Dolap %10 (3. test); otomatik seçimde komisyonsuz Trendyol: 1500 − 1000 − 45 = 455
    assert any("₺455,00" in m and "Güçlü fırsat" in m for m in ekran.metinler("markdown"))
    ekran = ekran.tikla("Listeye ekle")
    assert "“iPhone 13” takip listesine eklendi." in ekran.metinler("success")
    assert ekran.kpi_sayisi() == 4
    assert ekran.dugme_etiketleri().count("Satın aldım") == 1  # eklenen ürün seçili gelir
    assert any("iPhone 13" in m and "sahibinden.com/ilan/1" in m for m in ekran.metinler("code"))
    fid = int(vt_ayni.firsatlari_getir().iloc[0].id)

    # İkinci, fiyatı bilinmeyen ürün: toplu "Claude'a sor" çıkmaz (tek ürün), uyarı çıkar
    vt_ayni.firsat_ekle(dict(urun_adi="Kahve makinesi", alis_fiyati=800, kaynak_turu="Mağaza indirimi"))
    ekran = uygulama.sayfa("firsat-takibi")
    assert any("tahmini satış fiyatı girilmemiş" in m for m in ekran.metinler("markdown"))

    ekran = ekran.sec("ft_secili", "iPhone 13").tikla("Satın aldım")
    assert ekran.deger(f"firsat_al_{fid}_hedef") == 1500.0
    ekran = ekran.doldur(**{f"firsat_al_{fid}_alis": 950.0}).tikla("Elimdekiler'e ekle")
    assert any("Elimdekiler'e eklendi" in m for m in ekran.metinler("success"))
    s = vt_ayni.stoklari_getir().query("urun_adi == 'iPhone 13'").iloc[0]
    assert (s.alis_fiyati, s.hedef_fiyat, s.durum) == (950, 1500, "İkinci el")
    assert vt_ayni.firsatlari_getir(vt_ayni.ALINDI).iloc[0].id == fid

    ekran = ekran.sec("ft_gorunum", "Alındı")
    assert "Satın aldım" not in ekran.dugme_etiketleri()

    # Vazgeçme: kayıt silinmez, Vazgeçildi listesine geçer
    kid = int(vt_ayni.firsatlari_getir(vt_ayni.TAKIPTE).iloc[0].id)
    ekran = uygulama.sayfa("firsat-takibi").sec("ft_secili", "Kahve").tikla("Düzenle / sil")
    ekran = ekran.doldur(**{f"firsat_duzenle_{kid}_takip": "Vazgeçildi"}).tikla("Değişiklikleri kaydet")
    assert "“Kahve makinesi” güncellendi." in ekran.metinler("success")
    assert vt_ayni.firsatlari_getir(vt_ayni.VAZGECILDI).iloc[0].id == kid
    assert uygulama.sayfa().cevap["status"] == "ready"  # Genel Bakış (tahmin isabeti) açılır


def test_14_gider_excel_dosyasi(vt_ayni):
    from io import BytesIO

    import pandas as pd

    from arayuz.ortak import gider_excel_dosyasi
    vt_ayni.gider_ekle(dict(tarih=date.today(), kategori="Ambalaj", tutar=75, aciklama="Koli bandı"))
    tablo = pd.read_excel(BytesIO(gider_excel_dosyasi(vt_ayni.giderleri_getir())))
    assert list(tablo.columns) == ["Tarih", "Kategori", "Açıklama", "Tutar (₺)"]
    assert (tablo["Tutar (₺)"] == 75).any()
