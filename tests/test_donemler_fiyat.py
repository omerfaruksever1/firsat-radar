from datetime import date

import pandas as pd
import pytest

import donemler
import fiyat


# ---------- Dönemler ----------

@pytest.mark.parametrize("secim, bugun, beklenen", [
    # Bu ay: ayın 27'si → geçen ayın ilk 27 günüyle karşılaştırılır
    ("Bu ay", date(2026, 11, 27), (date(2026, 11, 1), date(2026, 11, 27), date(2026, 10, 1), date(2026, 10, 27))),
    # 31 Mart: Şubat 28 gün çektiği için önceki dönem Şubat sonunda biter
    ("Bu ay", date(2026, 3, 31), (date(2026, 3, 1), date(2026, 3, 31), date(2026, 2, 1), date(2026, 2, 28))),
    # Ocak: önceki dönem bir önceki yılın Aralık ayı
    ("Geçen ay", date(2026, 1, 15), (date(2025, 12, 1), date(2025, 12, 31), date(2025, 11, 1), date(2025, 11, 30))),
    ("Son 30 gün", date(2026, 11, 27), (date(2026, 10, 29), date(2026, 11, 27), date(2026, 9, 29), date(2026, 10, 28))),
    ("Bu yıl", date(2026, 11, 27), (date(2026, 1, 1), date(2026, 11, 27), date(2025, 1, 1), date(2025, 11, 27))),
])
def test_donem_araliklari(secim, bugun, beklenen):
    assert donemler.aralik(secim, bugun) == beklenen


def test_tumu_ve_ozel():
    bugun = date(2026, 11, 27)
    assert donemler.aralik("Tümü", bugun, ilk_tarih=date(2026, 5, 3)) == (date(2026, 5, 3), bugun, None, None)
    assert donemler.aralik("Özel", bugun, ozel=(date(2026, 11, 11), date(2026, 11, 20))) == \
        (date(2026, 11, 11), date(2026, 11, 20), date(2026, 11, 1), date(2026, 11, 10))
    with pytest.raises(ValueError):
        donemler.aralik("Yanlış", bugun)


def test_filtrele_uclar_dahil():
    df = pd.DataFrame({"tarih": pd.to_datetime(["2026-10-31", "2026-11-01", "2026-11-30", "2026-12-01"])})
    assert len(donemler.filtrele(df, date(2026, 11, 1), date(2026, 11, 30))) == 2


def test_ay_sonu():
    assert donemler.ay_sonu(date(2028, 2, 10)) == date(2028, 2, 29)  # artık yıl
    assert donemler.ay_sonu(date(2026, 12, 31)) == date(2026, 12, 31)


# ---------- Fiyat hesaplayıcı ----------

def test_hedef_marjdan_fiyat():
    # (300 + 45) / (1 − 0,15 − 0,25) = 575
    p = fiyat.oneri_fiyat(300, 45, 15, fiyat.HEDEF_TURLERI[0], 25)
    assert p == pytest.approx(575)
    net, komisyon, marj = fiyat.fiyattan_kar(300, 45, 15, p)
    assert komisyon == pytest.approx(86.25)
    assert marj == pytest.approx(25)


def test_hedef_tutardan_fiyat():
    # (300 + 45 + 100) / (1 − 0,15) ≈ 523,53 → net kâr tam 100
    p = fiyat.oneri_fiyat(300, 45, 15, fiyat.HEDEF_TURLERI[1], 100)
    assert fiyat.fiyattan_kar(300, 45, 15, p)[0] == pytest.approx(100)


def test_ulasilamaz_hedef():
    assert fiyat.oneri_fiyat(100, 0, 60, fiyat.HEDEF_TURLERI[0], 45) is None  # komisyon + marj = %105


def kanallar():
    return pd.DataFrame({"ad": ["Trendyol", "Elden", "Dolap"], "komisyon_orani": [15.0, 0.0, 10.0]})


def test_kanal_tablosu_hedef_modu():
    t = fiyat.kanal_tablosu(300, 45, kanallar(), fiyat.HEDEF_TURLERI[0], 25).set_index("kanal")
    assert t.loc["Trendyol", "fiyat"] == 575  # yukarı yuvarlanır
    assert t.loc["Elden", "kargo"] == 0  # elden teslimde kargo yok
    assert t.loc["Elden", "fiyat"] == 400  # 300 / 0,75
    assert (t["marj"] >= 25).all()


def test_kanal_tablosu_fiyat_modu_ve_ulasilamaz():
    t = fiyat.kanal_tablosu(300, 45, kanallar(), fiyat=500, kargosuz=()).set_index("kanal")
    assert t.loc["Elden", "net_kar"] == pytest.approx(155)
    assert t.loc["Trendyol", "net_kar"] == pytest.approx(80)
    ulasilamaz = fiyat.kanal_tablosu(100, 0, kanallar(), fiyat.HEDEF_TURLERI[0], 88).set_index("kanal")
    assert pd.isna(ulasilamaz.loc["Trendyol", "fiyat"])
    assert ulasilamaz.loc["Elden", "fiyat"] == 834  # 100 / 0,12 = 833,3 → 834
