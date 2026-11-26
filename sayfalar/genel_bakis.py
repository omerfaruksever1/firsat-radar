"""Genel Bakış: bu ayın özeti, aylık hedef, hızlı satış kaydı, bu ayın raporu ve son satışlar."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

import donemler
import veritabani as db
import yorum
from arayuz import formlar
from arayuz.ortak import (AYLAR, haftalik_kar_grafigi, kart, mesaji_goster, ozet_kartlari, sag_butonlar,
                          sayfa_basligi, tablo_bicimi, tespitleri_goster, tl, tr_tarih, yuzde)

bugun = date.today()
sag = sayfa_basligi("Genel Bakış", f"{tr_tarih(bugun)} · {AYLAR[bugun.month - 1]} {bugun.year} özeti")
with sag_butonlar(sag):
    if st.button("Fiyat hesapla", icon=":material/calculate:"):
        st.switch_page("sayfalar/fiyat_hesapla.py")
    if st.button("Elimdekiler'e ekle", icon=":material/add_box:", type="primary"):
        formlar.stok_ekle_penceresi()
mesaji_goster("stok_mesaj")

tum = db.satislari_getir()
bas, bit, o_bas, o_bit = donemler.aralik("Bu ay", bugun)
bu_ay = donemler.filtrele(tum, bas, bit)
gecen_ay = donemler.filtrele(tum, o_bas, o_bit)
gider = db.giderleri_getir(bas, bit)["tutar"].sum()
stok = db.stoklari_getir()

ciro, kar = bu_ay["ciro"].sum(), bu_ay["net_kar"].sum()
marj = kar / ciro * 100 if ciro else 0.0
gecen_marj = gecen_ay["net_kar"].sum() / gecen_ay["ciro"].sum() * 100 if gecen_ay["ciro"].sum() else None
ozet_kartlari([
    ("Bu ay ciro", tl(ciro), f"{len(bu_ay)} satış · {int(bu_ay['adet'].sum())} adet"),
    ("Bu ay net kâr", tl(kar),
     f"Ek giderler sonrası {tl(kar - gider)}" if gider else "Komisyon ve kargo düşülmüş"),
    ("Kâr marjı", yuzde(marj),
     f"Geçen ayın aynı dönemi {yuzde(gecen_marj)}" if gecen_marj is not None else "Net kâr ÷ ciro"),
    ("Elimdekiler", tl(stok["sermaye"].sum()), f"{int(stok['kalan'].sum())} ürün satılmayı bekliyor"),
], "gb_ozet")

hedef = float(db.ayar_getir("aylik_hedef", "0"))
if hedef > 0:
    gercek = kar - gider
    with kart("gb_hedef"):
        oran = max(0.0, min(gercek / hedef, 1.0))
        st.progress(oran, text=f"**Aylık kâr hedefi:** {tl(gercek)} / {tl(hedef)} ({yuzde(gercek / hedef * 100, 0)})")
        if gercek >= hedef:
            st.caption(":blue[:material/celebration:] Bu ayın hedefine ulaştın!")
        else:
            kalan_gun = (donemler.ay_sonu(bugun) - bugun).days + 1
            st.caption(f"Hedefe {tl(hedef - gercek)} kaldı · ayın bitmesine {kalan_gun} gün var.")

sol, sag = st.columns(2)
with sol, kart("gb_kayit", height="stretch"):
    st.subheader("Satış Kaydı Ekle", anchor=False)
    st.caption("Her satıştan sonra gir; raporlar otomatik güncellenir. Satış bugünün tarihiyle kaydedilir.")
    formlar.hizli_satis_formu("hizli")
    st.button("Kaydet", type="primary", width="stretch", on_click=formlar.hizli_satisi_kaydet, args=("hizli",))
    mesaji_goster("hizli_mesaj")

with sag, kart("gb_rapor", height="stretch"):
    ust = st.columns([3, 2], vertical_alignment="center")
    ust[0].subheader("Bu Ayın Raporu", anchor=False)
    with sag_butonlar(ust[1]):
        st.page_link("sayfalar/raporlar.py", label="Detaylı rapor", icon=":material/arrow_forward:",
                     icon_position="right")
    if bu_ay.empty:
        st.caption("Bu ay henüz satış yok. Soldaki formdan ilk satışını ekleyebilirsin.")
    else:
        st.table({
            "Toplam ciro": tl(ciro),
            "Toplam maliyet (alış + kargo + komisyon)": tl(bu_ay["maliyet"].sum()),
            "Net kâr": tl(kar),
            "En kârlı ürün": bu_ay.groupby("urun_adi")["net_kar"].sum().idxmax(),
            "Tahmin isabeti": "— (3. aşamada)",
        }, border="horizontal", width="stretch")
        tespitleri_goster(yorum.akilli_ozet(bu_ay, gecen_ay, gider)[:2])
    st.caption("Gerçekleşen net kâr (son 4 hafta)")
    dort_hafta_once = bugun - timedelta(weeks=3, days=bugun.weekday())
    haftalik_kar_grafigi(donemler.filtrele(tum, dort_hafta_once, bugun), dort_hafta_once, bugun,
                         yukseklik=150, eksen_basligi=None)

if not tum.empty:
    with kart("gb_son"):
        ust = st.columns([3, 2], vertical_alignment="center")
        ust[0].subheader("Son Satışlar", anchor=False)
        with sag_butonlar(ust[1]):
            st.page_link("sayfalar/satislarim.py", label="Tüm satışlar", icon=":material/arrow_forward:",
                         icon_position="right")
        son = tum.head(5)
        st.dataframe(
            tablo_bicimi(pd.DataFrame({"Tarih": son["tarih"], "Ürün": son["urun_adi"], "Kanal": son["pazar"],
                                       "Durum": son["durum"], "Adet": son["adet"], "Net kâr": son["net_kar"]}),
                         para=["Net kâr"], tarih=["Tarih"], kar=["Net kâr"]),
            hide_index=True, width="stretch", alt="Son 5 satış",
        )
