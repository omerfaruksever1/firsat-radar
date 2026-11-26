import sqlite3
from datetime import date, timedelta

import pandas as pd
import pytest

import veritabani
from conftest import sadece_dosya_veritabani, satis


def test_kar_hesabi():
    net, marj = veritabani.kar_hesapla(alis=100, satis=250, kargo=30, komisyon=20, adet=2)
    assert net == 200
    assert marj == pytest.approx(40.0)


def test_kar_hesabi_sifir_satista_marj_sifir():
    assert veritabani.kar_hesapla(0, 0, 0, 0, 1) == (0, 0.0)


def test_ekle_getir_ve_hesaplanan_sutunlar(vt):
    vt.satis_ekle(satis(urun_adi="  Kulaklık  ", adet=3, durum="İkinci el", kategori="Elektronik",
                        kaynak="Toptancı A", notlar="Kutulu"))
    df = vt.satislari_getir()
    r = df.iloc[0]
    assert r.urun_adi == "Kulaklık"  # baştaki/sondaki boşluklar temizlenir
    assert (r.ciro, r.maliyet, r.net_kar) == (600, 450, 150)
    assert r.marj == pytest.approx(25.0)
    assert (r.durum, r.kategori, r.kaynak, r.notlar) == ("İkinci el", "Elektronik", "Toptancı A", "Kutulu")


def test_bos_kategori_ve_kaynak_kaydedilebilir(vt):
    vt.satis_ekle(satis(kategori=None, kaynak=None, notlar=None))
    r = vt.satislari_getir().iloc[0]
    assert (r.kategori, r.kaynak, r.notlar) == ("", "", "")


def test_tarih_filtresi_ve_siralama(vt):
    for gun in (0, 10, 40):
        vt.satis_ekle(satis(gun_once=gun, urun_adi=f"{gun} gün"))
    df = vt.satislari_getir(baslangic=date.today() - timedelta(days=30))
    assert list(df.urun_adi) == ["0 gün", "10 gün"]  # en yeni en üstte


def test_guncelle_ve_sil(vt):
    vt.satis_ekle(satis())
    kayit_id = int(vt.satislari_getir().iloc[0].id)
    vt.satis_guncelle(kayit_id, satis(urun_adi="Yeni ad", adet=5, pazar="Elden"))
    r = vt.satislari_getir().iloc[0]
    assert (r.urun_adi, r.adet, r.pazar) == ("Yeni ad", 5, "Elden")
    vt.satis_sil(kayit_id)
    assert vt.satislari_getir().empty


@sadece_dosya_veritabani
def test_eski_veritabani_yeni_yapiya_gecer(tmp_path, monkeypatch):
    """1. aşamadan kalan veritabanı (yeni sütunlar ve tablolar yok) kayıt kaybetmeden güncellenir."""
    db = veritabani
    yol = tmp_path / "eski.db"
    c = sqlite3.connect(yol)
    c.execute("""CREATE TABLE satislar (id INTEGER PRIMARY KEY AUTOINCREMENT, urun_adi TEXT NOT NULL,
                 alis_fiyati REAL NOT NULL, satis_fiyati REAL NOT NULL, pazar TEXT NOT NULL,
                 kargo REAL NOT NULL DEFAULT 0, komisyon REAL NOT NULL DEFAULT 0,
                 tarih TEXT NOT NULL, adet INTEGER NOT NULL DEFAULT 1)""")
    c.execute("INSERT INTO satislar (urun_adi, alis_fiyati, satis_fiyati, pazar, tarih) "
              "VALUES ('Eski ürün', 10, 20, 'Trendyol', '2026-01-01')")
    c.commit()
    c.close()

    monkeypatch.setattr(db, "VERITABANI_YOLU", yol)
    db.tablolari_olustur()
    db.tablolari_olustur()  # ikinci kez çalışması da sorunsuz olmalı
    r = db.satislari_getir().iloc[0]
    assert (r.urun_adi, r.durum, r.kategori) == ("Eski ürün", "Sıfır", "")
    assert db.kanal_adlari() == db.VARSAYILAN_KANALLAR


def test_kanal_oran_yeniden_adlandirma_ve_ekleme(vt):
    vt.satis_ekle(satis(pazar="Kendi sitem"))
    tablo = vt.kanallari_getir()
    tablo.loc[tablo.ad == "Trendyol", "komisyon_orani"] = 15
    tablo.loc[tablo.ad == "Kendi sitem", "ad"] = "Web sitem"
    tablo = pd.concat([tablo, pd.DataFrame([{"id": None, "ad": "Instagram", "komisyon_orani": None}])],
                      ignore_index=True)
    vt.kanallari_kaydet(tablo)

    assert vt.komisyon_orani("Trendyol") == 15
    assert vt.komisyon_orani("Instagram") == 0
    assert vt.komisyon_orani("Olmayan kanal") == 0
    assert "Web sitem" in vt.kanal_adlari() and "Kendi sitem" not in vt.kanal_adlari()
    assert vt.kanal_adlari()[-1] == "Instagram"  # sıra korunur
    assert vt.satislari_getir().iloc[0].pazar == "Web sitem"  # eski satış yeni ada taşındı


def test_kanal_silmek_eski_satislari_silmez(vt):
    vt.satis_ekle(satis(pazar="Letgo"))
    tablo = vt.kanallari_getir()
    vt.kanallari_kaydet(tablo[tablo.ad != "Letgo"])
    assert "Letgo" not in vt.kanal_adlari()
    assert vt.satislari_getir().iloc[0].pazar == "Letgo"


def test_ayarlar(vt):
    assert vt.ayar_getir("varsayilan_kargo", "0") == "0"
    vt.ayar_kaydet("varsayilan_kargo", 45.5)
    vt.ayar_kaydet("varsayilan_kargo", 50)
    assert vt.ayar_getir("varsayilan_kargo") == "50"


def test_kullanilan_degerler(vt):
    vt.satis_ekle(satis(kaynak="B kişisi"))
    vt.satis_ekle(satis(kaynak="A toptancı"))
    vt.satis_ekle(satis(kaynak="A toptancı"))
    vt.satis_ekle(satis(kaynak=""))
    assert vt.kullanilan_degerler("kaynak") == ["A toptancı", "B kişisi"]


def test_yedek_dosyasi_gecerli_bir_veritabani(vt, tmp_path):
    vt.satis_ekle(satis(urun_adi="Yedeklenen"))
    yol = tmp_path / "indirilen.db"
    yol.write_bytes(vt.yedek_dosyasi())
    c = sqlite3.connect(yol)
    assert c.execute("SELECT urun_adi FROM satislar").fetchall() == [("Yedeklenen",)]
    c.close()


@sadece_dosya_veritabani
def test_gunluk_yedek_gunde_bir_kez_ve_eskileri_temizler(vt):
    klasor = vt.VERITABANI_YOLU.parent / "yedekler"
    klasor.mkdir()
    elle = klasor / "elle_alinmis.db"
    elle.write_bytes(b"x")
    for i in range(20):  # 20 eski otomatik yedek
        (klasor / f"otomatik_2025-01-{i + 1:02d}.db").write_bytes(b"x")

    vt.gunluk_yedek_al(saklanacak_gun=14)
    bugunku = klasor / f"otomatik_{date.today().isoformat()}.db"
    assert bugunku.exists()
    ilk_zaman = bugunku.stat().st_mtime_ns
    vt.gunluk_yedek_al(saklanacak_gun=14)  # aynı gün tekrar: üzerine yazmaz
    assert bugunku.stat().st_mtime_ns == ilk_zaman

    assert len(list(klasor.glob("otomatik_*.db"))) == 14
    assert elle.exists()  # elle alınan yedeğe dokunulmaz
