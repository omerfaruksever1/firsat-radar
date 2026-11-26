"""Ürün taraması için ÖRNEK veri. Gerçek tarama 3. aşamada bu dosyanın yerini alacak."""

import pandas as pd

# (ürün, kaynak, alış ₺, önerilen satış ₺, pazar komisyonu + kargo ₺, en iyi pazar,
#  satılabilirlik puanı 0–100, 30 günde tahmini satış adedi)
_URUNLER = [
    ("Laptop standı (alüminyum)", "Toptancı A", 310, 649, 131, "Trendyol", 86, 40),
    ("Manuel kahve öğütücü", "İthalatçı B", 420, 899, 227, "Amazon TR", 74, 25),
    ("Mekanik klavye (60%)", "Toptancı C", 1150, 1999, 429, "Hepsiburada", 63, 18),
    ("LED masa lambası", "Üretici D", 260, 499, 149, "Trendyol", 51, 12),
    ("Telefon tutucu (araç)", "Toptancı A", 120, 249, 107, "Kendi sitem", 34, 6),
]

# Ekrandaki sıralama seçeneği → sütun adı
SIRALAMA = {
    "Satılabilirlik": "satilabilirlik",
    "Net kâr %": "marj",
    "Tahmini satış": "tahmini_satis",
}


def firsatlar():
    df = pd.DataFrame(_URUNLER, columns=[
        "urun", "kaynak", "alis", "satis", "masraf", "pazar", "satilabilirlik", "tahmini_satis",
    ])
    df["kar_adet"] = df["satis"] - df["alis"] - df["masraf"]
    df["marj"] = df["kar_adet"] / df["satis"] * 100
    return df
