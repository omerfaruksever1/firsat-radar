"""Fırsat Takibi: kayıtlar, kanal/kâr değerlendirmesi, satın alıp Elimdekiler'e aktarma, yorumlar ve
tahmin isabeti."""

import math
from datetime import date, timedelta

import pandas as pd

import fiyat
import yorum
from conftest import satis


def firsat(**degerler):
    kayit = dict(urun_adi="iPhone 13", durum="İkinci el", kaynak_turu="İkinci el ilan", kaynak="Sahibinden",
                 link="", alis_fiyati=1000, adet=1, kargo=50, piyasa_fiyati=1500, kanal="", kategori="", notlar="")
    kayit.update(degerler)
    return kayit


def kanallar(**oranlar):
    adlar = ["Trendyol", "Dolap", "Elden"]
    return pd.DataFrame({"id": range(len(adlar)), "ad": adlar,
                         "komisyon_orani": [oranlar.get(a, 0.0) for a in adlar]})


def test_ekle_getir_guncelle_sil(vt):
    fid = vt.firsat_ekle(firsat(link="sahibinden.com/ilan/123", eklenme_tarihi=date.today() - timedelta(days=3)))
    r = vt.firsatlari_getir().iloc[0]
    assert (r.id, r.urun_adi, r.takip, r.bekleme_gun) == (fid, "iPhone 13", "Takipte", 3)
    assert r.link == "https://sahibinden.com/ilan/123"  # eksik "https://" eklenir

    vt.firsat_guncelle(fid, firsat(piyasa_fiyati=1700))  # takip verilmezse değişmez
    assert vt.firsatlari_getir().iloc[0][["piyasa_fiyati", "takip"]].tolist() == [1700, "Takipte"]
    vt.firsat_guncelle(fid, firsat(takip=vt.VAZGECILDI))
    assert vt.firsatlari_getir(vt.TAKIPTE).empty and len(vt.firsatlari_getir(vt.VAZGECILDI)) == 1

    vt.firsat_sil(fid)
    assert vt.firsatlari_getir().empty


def test_satin_al_elimdekilere_aktarir(vt):
    fid = vt.firsat_ekle(firsat(adet=2, kategori="Elektronik"))
    stok_id = vt.firsati_satin_al(fid, dict(urun_adi="iPhone 13", durum="İkinci el", kategori="Elektronik",
                                            kaynak="Sahibinden", alis_fiyati=950, adet=2, alis_tarihi=date.today(),
                                            hedef_fiyat=1500, notlar=""))
    s = vt.stoklari_getir().iloc[0]
    assert (s.id, s.alis_fiyati, s.kalan, s.hedef_fiyat) == (stok_id, 950, 2, 1500)
    f = vt.firsatlari_getir().iloc[0]
    assert (f.takip, f.stok_id) == ("Alındı", stok_id)
    assert "Sahibinden" in vt.kullanilan_degerler("kaynak")

    vt.firsat_sil(fid)  # fırsat silinse de stok kalır
    assert len(vt.stoklari_getir()) == 1


def test_tahmin_isabeti(vt):
    fid = vt.firsat_ekle(firsat(piyasa_fiyati=1500))
    stok_id = vt.firsati_satin_al(fid, dict(urun_adi="iPhone 13", alis_fiyati=1000, adet=2,
                                            alis_tarihi=date.today(), hedef_fiyat=1500))
    vt.satis_ekle(satis(urun_adi="Başka ürün"))  # fırsattan gelmeyen satış hesaba katılmaz
    assert yorum.tahmin_isabeti(vt.satislari_getir()) is None
    vt.stoktan_sat(stok_id, satis(urun_adi="iPhone 13", alis_fiyati=1000, satis_fiyati=1350, adet=1))
    vt.stoktan_sat(stok_id, satis(urun_adi="iPhone 13", alis_fiyati=1000, satis_fiyati=1500, adet=1))
    df = vt.satislari_getir()
    assert df["tahmini_fiyat"].notna().sum() == 2
    assert math.isclose(yorum.tahmin_isabeti(df), 95.0)  # sapmalar %10 ve %0 → ortalama %5


def test_degerlendirme_esikleri():
    assert [fiyat.degerlendirme(m) for m in [30, 25, 12, 0, -5, None, math.nan]] == [
        "Güçlü fırsat", "Güçlü fırsat", "Değerlendirilebilir", "Zayıf", "Zararına",
        "Piyasa fiyatı yok", "Piyasa fiyatı yok"]


def test_en_iyi_kanal():
    k = kanallar(Trendyol=20, Dolap=10)
    # Otomatik seçimde elden satış hesaba katılmaz: Dolap 1500 − 1000 − 50 − 150 = 300
    assert fiyat.en_iyi_kanal(1000, 50, 1500, k) == {"kanal": "Dolap", "net_kar": 300, "marj": 20}
    # Kanal elle seçilirse o kanal; elden satışta kargo düşülmez
    assert fiyat.en_iyi_kanal(1000, 50, 1500, k, "Elden")["net_kar"] == 500
    assert fiyat.en_iyi_kanal(1000, 50, 1500, k, "Trendyol")["net_kar"] == 150
    assert fiyat.en_iyi_kanal(1000, 50, 0, k) is None  # piyasa fiyatı yok


def test_firsatlari_degerlendir_siralar():
    df = pd.DataFrame([dict(firsat(urun_adi=ad, alis_fiyati=alis, piyasa_fiyati=piyasa, adet=adet), id=i)
                       for i, (ad, alis, piyasa, adet) in enumerate(
                           [("Fiyatsız", 100, 0, 1), ("Zararlı", 1000, 900, 1), ("İyi", 500, 1000, 3)])])
    sonuc = fiyat.firsatlari_degerlendir(df, kanallar())
    assert sonuc["urun_adi"].tolist() == ["İyi", "Zararlı", "Fiyatsız"]
    assert sonuc["degerlendirme"].tolist() == ["Güçlü fırsat", "Zararına", "Piyasa fiyatı yok"]
    assert sonuc.loc[0, "toplam_kar"] == 450 * 3
    assert pd.isna(sonuc.loc[2, "net_kar"])


def test_firsat_ozeti_ve_claude_metinleri(vt):
    vt.firsat_ekle(firsat(urun_adi="İyi ürün", alis_fiyati=500, piyasa_fiyati=1000))
    vt.firsat_ekle(firsat(urun_adi="Zararlı ürün", alis_fiyati=1000, piyasa_fiyati=900))
    vt.firsat_ekle(firsat(urun_adi="Fiyatsız ürün", piyasa_fiyati=0, link="https://ornek.com/ilan",
                          eklenme_tarihi=date.today() - timedelta(days=20)))
    df = fiyat.firsatlari_degerlendir(vt.firsatlari_getir(), vt.kanallari_getir())
    tespitler = yorum.firsat_ozeti(df)
    metin = " ".join(m for _, m in tespitler)
    assert tespitler[0][0] == "iyi" and "En iyi görünen: İyi ürün" in metin
    assert "zarar ettiren 1 ürün var: Zararlı ürün" in metin
    assert "1 ürünün tahmini satış fiyatı girilmemiş" in metin
    assert "1 ürün 14 günden uzun süredir listede" in metin

    r = next(df[df["urun_adi"] == "Fiyatsız ürün"].itertuples())
    istem = yorum.firsat_istemi(r)
    assert "“Fiyatsız ürün” (ikinci el" in istem and "https://ornek.com/ilan" in istem
    assert "Sahibinden" in istem and "TAHMİNİ SATIŞ FİYATI" in istem
    toplu = yorum.firsat_listesi_istemi(df, en_fazla=2)
    assert "1. “" in toplu and "2. “" in toplu and "3. “" not in toplu and "1 ürün daha" in toplu
    assert yorum.firsat_ozeti(df.iloc[0:0]) == [("bilgi", "Takip listende ürün yok.")]
