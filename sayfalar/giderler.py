"""Giderler: belirli bir ürüne ait olmayan masraflar (ambalaj, ilan ücreti, abonelik…)."""

from datetime import date

import pandas as pd
import streamlit as st

import donemler
import veritabani as db
from arayuz import formlar
from arayuz.ortak import (bos_durum, kart, kayit_secimi, mesaji_goster, ozet_kartlari, sag_butonlar,
                          sayfa_basligi, secimli_tablo, tablo_bicimi, tl, tr_tarih)

sag = sayfa_basligi("Giderler", "Ürüne bağlı olmayan masraflar. Raporlarda satış kârından düşülerek gerçek kârın "
                                "hesaplanır.")
with sag_butonlar(sag):
    if st.button("Gider ekle", icon=":material/add:", type="primary"):
        formlar.gider_ekle_penceresi()
mesaji_goster("gider_mesaj")

giderler = db.giderleri_getir()
if giderler.empty:
    with kart("gd_bos"):
        bos_durum("Henüz gider kaydı yok. Kargo poşeti, ilan öne çıkarma ücreti, mağaza aboneliği gibi belirli bir "
                  "ürüne ait olmayan masraflarını **Gider ekle** ile kaydet.", ":material/payments:")
    st.stop()

bugun = date.today()


def toplam(secim):
    bas, bit, *_ = donemler.aralik(secim, bugun)
    return donemler.filtrele(giderler, bas, bit)["tutar"].sum()


ozet_kartlari([
    ("Bu ay", tl(toplam("Bu ay")), "Bu ayki giderler"),
    ("Geçen ay", tl(toplam("Geçen ay")), "Geçen ayın tamamı"),
    ("Bu yıl", tl(toplam("Bu yıl")), f"{bugun.year} yılı toplamı"),
], "gd_ozet")

with kart("gd_liste"):
    st.subheader("Gider Kayıtları", anchor=False)
    tablo = pd.DataFrame({"Tarih": giderler["tarih"], "Kategori": giderler["kategori"],
                          "Açıklama": giderler["aciklama"], "Tutar": giderler["tutar"]})
    secimli_tablo(tablo_bicimi(tablo, para=["Tutar"], tarih=["Tarih"]), giderler["id"], "gd_tablo", "gd_secili",
                  alt="Gider kayıtları tablosu")
    kayitlar = {int(r.id): r for r in giderler.itertuples()}
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    with c1:
        secili = kayit_secimi("Seçili gider", kayitlar,
                              lambda i: f"{tr_tarih(kayitlar[i].tarih)} · {kayitlar[i].kategori} · "
                                        f"{tl(kayitlar[i].tutar)}", "gd_secili")
    with c2.popover("Sil", icon=":material/delete:", disabled=secili is None):
        st.write("Seçili gider silinsin mi? Bu işlem geri alınamaz.")
        if st.button("Evet, sil", type="primary"):
            db.gider_sil(secili)
            st.session_state.gider_mesaj = ("ok", "Gider silindi.")
            st.rerun()
