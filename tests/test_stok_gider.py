from datetime import date, timedelta

import pandas as pd
import pytest

import yorum
from conftest import satis


def stok(gun_once=10, **degerler):
    kayit = dict(urun_adi="Ceket", durum="İkinci el", kategori="Giyim", kaynak="Bit pazarı", alis_fiyati=100,
                 adet=3, hedef_fiyat=250, notlar="", alis_tarihi=date.today() - timedelta(days=gun_once))
    kayit.update(degerler)
    return kayit


def tek_stok(vt):
    return vt.stoklari_getir(sadece_eldekiler=False).iloc[0]


def test_stok_ekle_ve_hesaplanan_sutunlar(vt):
    vt.stok_ekle(stok(gun_once=12))
    r = tek_stok(vt)
    assert (r.adet, r.kalan, r.bekleme_gun, r.sermaye) == (3, 3, 12, 300)


def test_stoktan_satis_kalani_dusurur_ve_satis_suresini_hesaplar(vt):
    vt.stok_ekle(stok(gun_once=12))
    stok_id = int(tek_stok(vt).id)
    vt.stoktan_sat(stok_id, satis(urun_adi="Ceket", adet=2, gun_once=2))
    assert tek_stok(vt).kalan == 1
    s = vt.satislari_getir().iloc[0]
    assert s.stok_id == stok_id and s.satis_suresi == 10

    with pytest.raises(vt.StokYetersiz):
        vt.stoktan_sat(stok_id, satis(adet=2))
    assert tek_stok(vt).kalan == 1  # hatalı satış hiçbir şeyi değiştirmez
    assert len(vt.satislari_getir()) == 1

    vt.stoktan_sat(stok_id, satis(adet=1))
    assert vt.stoklari_getir().empty  # elde kalmadı: Elimdekiler listesinden çıkar
    assert len(vt.stoklari_getir(sadece_eldekiler=False)) == 1


def test_stoktan_satisi_duzenlemek_ve_silmek_stogu_duzeltir(vt):
    vt.stok_ekle(stok(adet=5))
    stok_id = int(tek_stok(vt).id)
    vt.stoktan_sat(stok_id, satis(adet=2))
    satis_id = int(vt.satislari_getir().iloc[0].id)

    vt.satis_guncelle(satis_id, satis(adet=4))
    assert tek_stok(vt).kalan == 1
    with pytest.raises(vt.StokYetersiz):
        vt.satis_guncelle(satis_id, satis(adet=6))  # elde 1 + satılmış 4 = en fazla 5
    assert vt.satislari_getir().iloc[0].adet == 4

    vt.satis_sil(satis_id)
    assert tek_stok(vt).kalan == 5  # ürünler Elimdekiler'e geri döndü


def test_stok_silinse_de_satis_kalir_ve_duzenlenebilir(vt):
    vt.stok_ekle(stok())
    stok_id = int(tek_stok(vt).id)
    vt.stoktan_sat(stok_id, satis(adet=1))
    vt.stok_sil(stok_id)
    satis_id = int(vt.satislari_getir().iloc[0].id)
    vt.satis_guncelle(satis_id, satis(adet=9))
    vt.satis_sil(satis_id)
    assert vt.satislari_getir().empty


def test_stok_guncelle_kalan_ve_toplam_adet(vt):
    vt.stok_ekle(stok(adet=5))
    stok_id = int(tek_stok(vt).id)
    vt.stoktan_sat(stok_id, satis(adet=2))  # adet 5, kalan 3
    vt.stok_guncelle(stok_id, stok(urun_adi="Deri ceket", kalan=4, hedef_fiyat=0))
    r = tek_stok(vt)
    assert (r.urun_adi, r.kalan, r.adet, r.hedef_fiyat) == ("Deri ceket", 4, 6, 0)


def test_kullanilan_degerler_stoktakileri_de_onerir(vt):
    vt.stok_ekle(stok(kaynak="Stoktaki kaynak", kategori="Antika"))
    vt.satis_ekle(satis(kaynak="Satıştaki kaynak"))
    assert vt.kullanilan_degerler("kaynak") == ["Satıştaki kaynak", "Stoktaki kaynak"]
    assert vt.kullanilan_degerler("kategori") == ["Antika"]


def test_giderler(vt):
    bugun = date.today()
    vt.gider_ekle(dict(tarih=bugun, kategori="Ambalaj", aciklama=" Poşet ", tutar=120))
    vt.gider_ekle(dict(tarih=bugun - timedelta(days=40), kategori="Yeni tür", tutar=80))
    assert vt.giderleri_getir()["tutar"].sum() == 200
    son = vt.giderleri_getir(bugun - timedelta(days=7), bugun)
    assert list(son.aciklama) == ["Poşet"]
    assert "Yeni tür" in vt.gider_kategorileri() and "Ambalaj" in vt.gider_kategorileri()
    vt.gider_sil(int(son.iloc[0].id))
    assert len(vt.giderleri_getir()) == 1


# ---------- Yorumlar ----------

def test_stok_ozeti(vt):
    assert yorum.stok_ozeti(vt.stoklari_getir()) == [("bilgi", "Elinde bekleyen ürün yok.")]
    vt.stok_ekle(stok(urun_adi="Eski ürün", gun_once=90, adet=1, alis_fiyati=200, hedef_fiyat=150))
    vt.stok_ekle(stok(urun_adi="Yeni ürün", gun_once=5, adet=2, alis_fiyati=100, hedef_fiyat=300))
    metin = " ".join(m for _, m in yorum.stok_ozeti(vt.stoklari_getir()))
    assert "Elinde 3 adet ürün var; bunlara ₺400 bağlı" in metin
    assert "1 ürün 60 günden uzun süredir satılmadı: Eski ürün (90 gün)" in metin
    assert "Hedef satış fiyatı alış fiyatının altında veya eşit: Eski ürün" in metin
    assert "yaklaşık ₺350 brüt kazanç" in metin  # (150−200)×1 + (300−100)×2


def test_akilli_ozet_gider_ve_satis_suresi(vt):
    for gun in (20, 10):
        vt.stok_ekle(stok(gun_once=gun, adet=1))
    for r in vt.stoklari_getir().itertuples():
        vt.stoktan_sat(int(r.id), satis(adet=1))
    df = vt.satislari_getir()
    tespitler = yorum.akilli_ozet(df, gider=500)
    metin = " ".join(m for _, m in tespitler)
    assert "ortalama 15 günde satılmış" in metin
    # 2 satış × ₺50 kâr = ₺100; ₺500 gider düşünce gerçek kâr -₺400 → uyarı
    assert ("uyari", "Bu dönemde ₺500 ek giderin var (ambalaj, ilan vb.). Satış kârından düşünce gerçek "
                     "kârın -₺400.") in tespitler


def test_negatif_yuzde_bicimi(vt):
    vt.satis_ekle(satis(alis_fiyati=150, satis_fiyati=100, kargo=0, komisyon=0))
    metin = " ".join(m for _, m in yorum.urun_yorumu(vt.satislari_getir(), "Ürün"))
    assert "marj -%50,0" in metin


def test_ortak_bicimler():
    from arayuz.ortak import tablo_bicimi, tl, yuzde
    assert tl(1234.5) == "₺1.234,50" and tl(-1234.5, 0) == "-₺1.234"
    assert yuzde(12.34) == "%12,3" and yuzde(-5) == "-%5,0"
    html = tablo_bicimi(pd.DataFrame({"t": [-5.0, 0.0, None]}), para=["t"], kar=["t"], sifir_bos=["t"]).to_html()
    assert "-₺5,00" in html and html.count("—") == 2
