"""Ortak test ayarları: her test kendi geçici veritabanını kullanır, gerçek kayıtlara dokunulmaz.

FIRSATRADAR_TEST_PG_URL ortam değişkenine BOŞ bir test PostgreSQL veritabanının adresi verilirse, veritabanı
testleri dosya yerine o veritabanında çalışır (her testten önce tablolar silinip yeniden kurulur).
Gerçek verilerin olduğu veritabanının adresini buraya VERMEYİN.
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

PROJE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJE))

import veritabani as db  # noqa: E402

TEST_PG_ADRESI = os.environ.get("FIRSATRADAR_TEST_PG_URL")
sadece_dosya_veritabani = pytest.mark.skipif(bool(TEST_PG_ADRESI), reason="yalnızca SQLite dosyasıyla anlamlı")


@pytest.fixture
def vt(tmp_path, monkeypatch):
    """Boş, kurulmuş geçici veritabanı."""
    monkeypatch.setattr(db, "VERITABANI_YOLU", tmp_path / "test.db")
    monkeypatch.setattr(db, "VERITABANI_ADRESI", TEST_PG_ADRESI)
    if TEST_PG_ADRESI:
        db.tablolari_sil()
    db.tablolari_olustur()
    return db


def satis(gun_once=0, **degerler):
    """Varsayılanlarla doldurulmuş bir satış kaydı."""
    kayit = dict(urun_adi="Ürün", pazar="Trendyol", alis_fiyati=100, satis_fiyati=200, kargo=20,
                 komisyon=30, adet=1, durum="Sıfır", kategori="", kaynak="", notlar="",
                 tarih=date.today() - timedelta(days=gun_once))
    kayit.update(degerler)
    return kayit
