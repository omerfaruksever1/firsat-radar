"""Rapor dönemleri: hazır seçeneklerin tarih aralığı ve karşılaştırılacak önceki dönem."""

from datetime import date, timedelta

DONEMLER = ["Bu ay", "Geçen ay", "Son 30 gün", "Bu yıl", "Tümü", "Özel"]


def _ay_basi(gun):
    return gun.replace(day=1)


def _onceki_ay_basi(gun):
    return _ay_basi(_ay_basi(gun) - timedelta(days=1))


def ay_sonu(gun):
    sonraki = (gun.replace(day=28) + timedelta(days=4)).replace(day=1)
    return sonraki - timedelta(days=1)


def _ayni_gune_kadar(bas, gun_sayisi, ust_sinir):
    """`bas` gününden itibaren `gun_sayisi` gün, ama `ust_sinir`ı aşmadan (kısa aylar için)."""
    return min(bas + timedelta(days=gun_sayisi), ust_sinir)


def aralik(secim, bugun=None, ilk_tarih=None, ozel=None):
    """(başlangıç, bitiş, önceki_başlangıç, önceki_bitiş) döndürür; önceki dönem yoksa son ikisi None.

    Önceki dönem adil karşılaştırma içindir: "Bu ay" ayın 10'unda seçildiyse geçen ayın da ilk 10 günü
    alınır; "Bu yıl" geçen yılın aynı tarihine kadarki kısmıyla karşılaştırılır.
    """
    bugun = bugun or date.today()
    if secim == "Bu ay":
        bas = _ay_basi(bugun)
        o_bas = _onceki_ay_basi(bugun)
        return bas, bugun, o_bas, _ayni_gune_kadar(o_bas, (bugun - bas).days, bas - timedelta(days=1))
    if secim == "Geçen ay":
        bas = _onceki_ay_basi(bugun)
        return bas, ay_sonu(bas), _onceki_ay_basi(bas), bas - timedelta(days=1)
    if secim == "Son 30 gün":
        bas = bugun - timedelta(days=29)
        return bas, bugun, bas - timedelta(days=30), bas - timedelta(days=1)
    if secim == "Bu yıl":
        bas = bugun.replace(month=1, day=1)
        o_bas = bas.replace(year=bas.year - 1)
        return bas, bugun, o_bas, _ayni_gune_kadar(o_bas, (bugun - bas).days, bas - timedelta(days=1))
    if secim == "Tümü":
        return min(ilk_tarih or bugun, bugun), bugun, None, None
    if secim == "Özel":
        bas, bit = ozel
        gun = (bit - bas).days + 1
        return bas, bit, bas - timedelta(days=gun), bas - timedelta(days=1)
    raise ValueError(f"Bilinmeyen dönem: {secim}")


def filtrele(df, bas, bit, sutun="tarih"):
    """Tarih sütunu [bas, bit] aralığında olan satırlar."""
    gunler = df[sutun].dt.date
    return df[(gunler >= bas) & (gunler <= bit)]
