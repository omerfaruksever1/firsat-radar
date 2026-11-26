"""Fiyat hesaplayıcı: hedef kâra göre her satış kanalı için satış fiyatı ve verilen fiyattan kâr.

Komisyon satış fiyatının yüzdesi olarak kesilir, bu yüzden fiyat şöyle bulunur:
    net kâr = fiyat − alış − kargo − fiyat × oran
    hedef marj m ise:   fiyat = (alış + kargo) / (1 − oran − m)
    hedef tutar K ise:  fiyat = (alış + kargo + K) / (1 − oran)
3. aşamadaki ürün taraması da "en iyi pazar" hesabında bu fonksiyonları kullanacak.
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
