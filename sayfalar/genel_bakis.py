"""Genel Bakış: bu ayın özeti (KPI kartları), haftalık satış kârı, son satışlar. Görünüm: tasarim/01-genel-bakis.html.
Satış eklemek için "+ Satış ekle" düğmesi açılır pencereyi açar."""

from datetime import date

import streamlit as st

import donemler
import styles
import veritabani as db
import yorum
from arayuz import formlar
from arayuz.ortak import (AYLAR, kart, mesaji_goster, ozet_kartlari, sag_butonlar, sayfa_basligi,
                          son_haftalar_grafigi, tespitleri_goster, yuzde)

GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
BEKLEME_UYARI = 30

bugun = date.today()
sag = sayfa_basligi("Genel Bakış", f"{AYLAR[bugun.month - 1]} {bugun.year} · {bugun.day} "
                                   f"{AYLAR[bugun.month - 1]} {GUNLER[bugun.weekday()]}")
with sag_butonlar(sag):
    if st.button("Fiyat hesapla"):
        st.switch_page("sayfalar/fiyat_hesapla.py")
    if st.button("Satış ekle", icon=":material/add:", type="primary"):
        formlar.yeni_satis_penceresi()
mesaji_goster("satis_mesaj")

tum = db.satislari_getir()
bas, bit, o_bas, o_bit = donemler.aralik("Bu ay", bugun)
bu_ay = donemler.filtrele(tum, bas, bit)
gecen_ay = donemler.filtrele(tum, o_bas, o_bit)
gider = db.giderleri_getir(bas, bit)["tutar"].sum()
stok = db.stoklari_getir()
hedef = float(db.ayar_getir("aylik_hedef", "0"))

# ---------- KPI kartları ----------
ciro, kar = bu_ay["ciro"].sum(), bu_ay["net_kar"].sum()
marj = kar / ciro * 100 if ciro else 0.0
gecen_ciro = gecen_ay["ciro"].sum()
if gecen_ciro:
    degisim = (ciro - gecen_ciro) / gecen_ciro * 100
    ciro_alt = (f"{'▲' if degisim >= 0 else '▼'} {yuzde(abs(degisim), 0)} geçen ayın aynı dönemine göre",
                styles.RENK["kar"] if degisim >= 0 else styles.RENK["zarar"])
else:
    ciro_alt = (f"{len(bu_ay)} satış · {int(bu_ay['adet'].sum())} adet", None)

gercek = kar - gider
if hedef > 0:
    kar_kart = dict(alt=f"Hedef {styles.para(hedef)} · {yuzde(gercek / hedef * 100, 0)}"
                        + (f" · giderler sonrası {styles.para(gercek)}" if gider else ""),
                    cubuk=(gercek / hedef, styles.RENK["kar"]))
else:
    kar_kart = dict(alt=f"Ek giderler sonrası {styles.para(gercek)}" if gider else "Komisyon + kargo düşülmüş")

uzun_bekleyen = int((stok["bekleme_gun"] >= BEKLEME_UYARI).sum())
stok_alt = (f"{int(stok['kalan'].sum())} ürün · {uzun_bekleyen}'si {BEKLEME_UYARI}+ gündür bekliyor"
            if uzun_bekleyen else f"{int(stok['kalan'].sum())} ürün satılmayı bekliyor")

ozet_kartlari([
    dict(baslik="Bu ay ciro", deger=styles.para(ciro), alt=ciro_alt[0], alt_rengi=ciro_alt[1]),
    dict(baslik="Satış kârı", deger=styles.para(kar), deger_rengi=styles.kar_rengi(kar), **kar_kart),
    dict(baslik="Gerçek kâr", deger=styles.para(gercek), deger_rengi=styles.kar_rengi(gercek),
         alt=f"Satış kârı − giderler ({styles.para(gider)})"),
    dict(baslik="Kâr marjı", deger=yuzde(marj), cubuk=marj / 50,
         alt="Satış kârı ÷ ciro"),
    dict(baslik="Elimdekiler", deger=styles.para(stok["sermaye"].sum()), alt=stok_alt,
         alt_rengi=styles.RENK["uyari"] if uzun_bekleyen else None),
])

# ---------- Haftalık satış kârı + son satışlar ----------
sol, sag = st.columns([1.6, 1], gap="small")
with sol, kart("gb_haftalik", height="stretch"):
    ust = st.columns([3, 2], vertical_alignment="center")
    ust[0].subheader("Haftalık satış kârı", anchor=False)
    with sag_butonlar(ust[1]):
        st.page_link("sayfalar/raporlar.py", label="Detaylı rapor →")
    son_haftalar_grafigi(tum, bugun)
    if not bu_ay.empty:
        tespitler = yorum.akilli_ozet(bu_ay, gecen_ay, gider)[:2]
        isabet = yorum.tahmin_isabeti(bu_ay)
        if isabet is not None:
            tespitler.append(("bilgi", f"Tahmin isabeti: Fırsat Takibi'nde tahmin ettiğin satış fiyatları bu ay "
                                       f"ortalama {yuzde(isabet, 0)} tuttu."))
        tespitleri_goster(tespitler)

with sag, kart("gb_son", height="stretch"):
    ust = st.columns([3, 2], vertical_alignment="center")
    ust[0].subheader("Son satışlar", anchor=False)
    with sag_butonlar(ust[1]):
        st.page_link("sayfalar/satislarim.py", label="Tümü →")
    if tum.empty:
        styles.bos_kart("Henüz satış yok. Sağ üstteki <b>+ Satış ekle</b> ile ilk satışını kaydet.")
    else:
        def gun_metni(gun):
            fark = (bugun - gun).days
            return "bugün" if fark == 0 else "dün" if fark == 1 else f"{gun.day} {AYLAR[gun.month - 1][:3]}"

        styles.html("".join(
            styles.liste_satiri(f"{r.urun_adi}{f' ×{r.adet}' if r.adet > 1 else ''}"
                                f"{' · 2. el' if r.durum == 'İkinci el' else ''}",
                                f"{r.pazar} · {gun_metni(r.tarih.date())}", styles.kar_metni(r.net_kar))
            for r in tum.head(6).itertuples()))
