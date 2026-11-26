import re
from datetime import date

import pandas as pd

import yorum
from conftest import satis


def metinler(tespitler, tur=None):
    return [m for t, m in tespitler if tur is None or t == tur]


def veri(vt, *kayitlar):
    for k in kayitlar:
        vt.satis_ekle(k)
    return vt.satislari_getir()


def test_bos_donem():
    assert yorum.akilli_ozet(pd.DataFrame()) == [("bilgi", "Bu dönemde satış yok.")]


def test_onceki_donemle_karsilastirma(vt):
    df = veri(vt, satis(gun_once=1, satis_fiyati=300), satis(gun_once=40, satis_fiyati=200))
    simdi, once = df[df.tarih == df.tarih.max()], df[df.tarih < df.tarih.max()]
    tespit = yorum.akilli_ozet(simdi, once)
    assert any("Ciron önceki döneme göre %50,0 arttı" in m for m in metinler(tespit, "iyi"))
    assert any("Kâr marjın yükseldi" in m for m in metinler(tespit))


def test_onceki_donem_bos_ise_bilgi_verir(vt):
    df = veri(vt, satis())
    tespit = yorum.akilli_ozet(df, df.iloc[0:0])
    assert any("karşılaştırma yapılamadı" in m for m in metinler(tespit, "bilgi"))


def test_toplam_zarar_ve_zararli_urun(vt):
    df = veri(vt, satis(urun_adi="Kılıf", alis_fiyati=50, satis_fiyati=40, kargo=10, komisyon=0))
    uyarilar = metinler(yorum.akilli_ozet(df), "uyari")
    assert any("toplamda zarardasın" in m for m in uyarilar)
    assert any("Zarar ettiren ürün: “Kılıf”" in m for m in uyarilar)


def test_toplamda_karli_ama_zararina_yapilmis_satis(vt):
    df = veri(vt,
              satis(urun_adi="Kılıf", pazar="Trendyol", alis_fiyati=20, satis_fiyati=45, kargo=30, komisyon=7, adet=4),
              satis(urun_adi="Kılıf", pazar="Elden", alis_fiyati=20, satis_fiyati=60, kargo=0, komisyon=0, adet=2))
    uyarilar = metinler(yorum.akilli_ozet(df), "uyari")
    assert any("1 satışı zararına yapmışsın: Kılıf (Trendyol, -₺48)" in m for m in uyarilar)


def test_kanal_durum_kategori_karsilastirmasi(vt):
    df = veri(vt,
              satis(pazar="Elden", durum="İkinci el", kategori="Giyim", alis_fiyati=50, kargo=0, komisyon=0),
              satis(pazar="Trendyol", durum="Sıfır", kategori="Elektronik", alis_fiyati=150, kargo=10, komisyon=30))
    bilgiler = " ".join(metinler(yorum.akilli_ozet(df), "bilgi"))
    assert "En kârlı kanalın Elden" in bilgiler
    assert "İkinci el ürünlerde marjın %75,0, sıfır ürünlerde %5,0" in bilgiler
    assert "En çok kazandıran kategori: Giyim" in bilgiler


def test_az_veri_notu(vt):
    df = veri(vt, satis())
    assert any("sadece 1 satış var" in m for m in metinler(yorum.akilli_ozet(df)))


def test_turkce_ek_hatasi_yok(vt):
    """Sayıdan sonra kesme işaretiyle ek getirilmez (ör. %48,6'i gibi yanlış ekler).
    Tek istisna her zaman doğru olan "₺100'lük" ifadesi."""
    df = veri(vt, satis(gun_once=1, urun_adi="A"), satis(gun_once=2, urun_adi="B", satis_fiyati=500),
              satis(gun_once=40, alis_fiyati=10))
    tum_metin = " ".join(metinler(yorum.akilli_ozet(df.iloc[:2], df.iloc[2:]) + yorum.urun_yorumu(df, "A")))
    assert not re.search(r"\d'[a-zığüşöç]", tum_metin.replace("₺100'lük", "")), tum_metin


def test_urun_yorumu(vt):
    df = veri(vt,
              satis(gun_once=5, urun_adi="Kılıf", pazar="Trendyol", alis_fiyati=20, satis_fiyati=45, kargo=30,
                    komisyon=7, adet=4),
              satis(gun_once=1, urun_adi="Kılıf", pazar="Web sitem", alis_fiyati=20, satis_fiyati=60, kargo=10,
                    komisyon=0, adet=2, durum="İkinci el"))
    tespit = yorum.urun_yorumu(df, "Kılıf")
    hepsi = " ".join(metinler(tespit))
    assert "toplam 6 adet sattın; net kâr ₺12" in hepsi
    assert "Trendyol satışında adet başına maliyet ₺57" in hepsi
    assert "Satış fiyatını yükselttin (ilk satış ₺45 → son satış ₺60)" in hepsi
    assert "Adet başına en çok Web sitem kanalında" in hepsi
    assert "İkinci el ürünlerde fiyat" in hepsi
    assert yorum.urun_yorumu(df, "Olmayan") == [("bilgi", "Bu ürün için satış yok.")]


def test_claude_istemleri_verileri_icerir(vt):
    df = veri(vt, satis(urun_adi="Oyun konsolu", durum="İkinci el", pazar="Sahibinden", satis_fiyati=1100))
    donem = yorum.donem_istemi(df, date(2026, 11, 1), date(2026, 11, 30))
    assert "01.11.2026 – 30.11.2026" in donem and "Oyun konsolu" in donem and "Sahibinden" in donem
    assert "İnternette" in donem
    urun = yorum.urun_istemi(df, "Oyun konsolu")
    assert "“Oyun konsolu” ürününü (İkinci el)" in urun and "ikinci el fiyatlarına" in urun


def test_claude_istemi_uzun_listeyi_kisaltir(vt):
    df = veri(vt, *[satis(urun_adi=f"Ürün {i}") for i in range(65)])
    assert "… ve 5 satış daha" in yorum.donem_istemi(df, date.today(), date.today())


def test_turkce_kucuk_harf():
    assert yorum.kucuk_harf("İkinci El IŞIK") == "ikinci el ışık"
    assert "i̇" not in yorum.kucuk_harf("İphone")  # Python'un lower() fonksiyonundaki bozuk "i̇" oluşmaz
