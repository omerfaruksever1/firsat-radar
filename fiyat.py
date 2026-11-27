"""Fiyat hesaplayıcı: hedef kâra göre her satış kanalı için satış fiyatı ve verilen fiyattan kâr.

Komisyon satış fiyatının yüzdesi olarak kesilir, bu yüzden fiyat şöyle bulunur:
    net kâr = fiyat − alış − kargo − fiyat × oran
    hedef marj m ise:   fiyat = (alış + kargo) / (1 − oran − m)
    hedef tutar K ise:  fiyat = (alış + kargo + K) / (1 − oran)
Fırsat Takibi sayfası da "en kârlı kanal" hesabında bu fonksiyonları kullanır.
"""

import math

import pandas as pd

HEDEF_TURLERI = ["Kâr marjı (%)", "Kâr tutarı (₺)"]


def oneri_fiyat(alis, kargo, oran, hedef_turu, hedef):
    """Hedefe ulaşmak için gereken satış fiyatı; mümkün değilse None (ör. komisyon + marj ≥ %100)."""
    oran = oran / 100
    if hedef_turu == HEDEF_TURLERI[0]:
        payda = 1 - oran - hedef / 100
        pay = alis + kargo
    else:
        payda = 1 - oran
        pay = alis + kargo + hedef
    if payda <= 0:
        return None
    return pay / payda


def fiyattan_kar(alis, kargo, oran, fiyat):
    """Verilen fiyatta (net kâr, komisyon tutarı, marj %)."""
    komisyon = fiyat * oran / 100
    net = fiyat - alis - kargo - komisyon
    return net, komisyon, (net / fiyat * 100 if fiyat else 0.0)


def kanal_tablosu(alis, kargo, kanallar, hedef_turu=None, hedef=None, fiyat=None, kargosuz=("Elden",)):
    """Her kanal için satış fiyatı, komisyon, net kâr ve marj.

    `fiyat` verilirse o fiyattan kâr hesaplanır; verilmezse hedefe göre fiyat önerilir (yukarı yuvarlanır).
    `kargosuz` kanallarda kargo düşülmez (elden teslim).
    """
    satirlar = []
    for kanal in kanallar.itertuples():
        kanal_kargo = 0.0 if kanal.ad in kargosuz else kargo
        if fiyat is None:
            ham = oneri_fiyat(alis, kanal_kargo, kanal.komisyon_orani, hedef_turu, hedef)
            satis = math.ceil(ham) if ham is not None else None
        else:
            satis = fiyat
        if satis is None:
            satirlar.append({"kanal": kanal.ad, "oran": kanal.komisyon_orani, "kargo": kanal_kargo,
                             "fiyat": None, "komisyon": None, "net_kar": None, "marj": None})
            continue
        net, komisyon, marj = fiyattan_kar(alis, kanal_kargo, kanal.komisyon_orani, satis)
        satirlar.append({"kanal": kanal.ad, "oran": kanal.komisyon_orani, "kargo": kanal_kargo,
                         "fiyat": satis, "komisyon": komisyon, "net_kar": net, "marj": marj})
    return pd.DataFrame(satirlar)


# ---------- Fırsat Takibi ----------

GUCLU_MARJ, ORTA_MARJ = 25, 10  # % kâr marjı eşikleri
DEGERLENDIRMELER = ["Güçlü fırsat", "Değerlendirilebilir", "Zayıf", "Zararına", "Piyasa fiyatı yok"]


def degerlendirme(marj):
    """Kâr marjına (%) göre fırsatın etiketi; marj yoksa (piyasa fiyatı girilmemiş) "Piyasa fiyatı yok"."""
    if marj is None or pd.isna(marj):
        return DEGERLENDIRMELER[4]
    if marj >= GUCLU_MARJ:
        return DEGERLENDIRMELER[0]
    if marj >= ORTA_MARJ:
        return DEGERLENDIRMELER[1]
    if marj >= 0:
        return DEGERLENDIRMELER[2]
    return DEGERLENDIRMELER[3]


def en_iyi_kanal(alis, kargo, piyasa, kanallar, kanal="", kargosuz=("Elden",)):
    """Piyasa fiyatından satılırsa kanal, adet başı net kâr ve marj. `kanal` boşsa en kârlı kanal seçilir;
    otomatik seçimde elden satış (kargosuz kanallar) hesaba katılmaz, çünkü kargo düşülmediği için hep o
    kazanırdı. Elden satmayı düşünüyorsan kanalı elle seçebilirsin. Piyasa fiyatı girilmemişse (0) None."""
    if not piyasa or kanallar.empty:
        return None
    if kanal and kanal in set(kanallar["ad"]):
        kanallar = kanallar[kanallar["ad"] == kanal]
    elif (~kanallar["ad"].isin(kargosuz)).any():
        kanallar = kanallar[~kanallar["ad"].isin(kargosuz)]
    tablo = kanal_tablosu(alis, kargo, kanallar, fiyat=piyasa, kargosuz=kargosuz)
    en_iyi = tablo.loc[tablo["net_kar"].idxmax()]
    return {"kanal": en_iyi["kanal"], "net_kar": en_iyi["net_kar"], "marj": en_iyi["marj"]}


def firsatlari_degerlendir(df, kanallar):
    """Fırsat listesine kanal, net kâr (adet başı ve toplam), marj ve değerlendirme sütunlarını ekler; en
    kârlıdan en az kârlıya sıralar (piyasa fiyatı olmayanlar sonda)."""
    sonuclar = [en_iyi_kanal(r.alis_fiyati, r.kargo, r.piyasa_fiyati, kanallar, r.kanal) for r in df.itertuples()]
    df = df.assign(
        satis_kanali=[s["kanal"] if s else None for s in sonuclar],
        net_kar=[s["net_kar"] if s else math.nan for s in sonuclar],
        marj=[s["marj"] if s else math.nan for s in sonuclar],
    )
    df["toplam_kar"] = df["net_kar"] * df["adet"]
    df["degerlendirme"] = [degerlendirme(m) for m in df["marj"]]
    return df.sort_values(["marj", "id"], ascending=[False, False], na_position="last").reset_index(drop=True)
