"""Raporlar: hazır dönemler, özet kartları ve üç sekme (Özet, Kanallar ve ürünler, Ürün yorumu)."""

from datetime import date

import pandas as pd
import streamlit as st

import donemler
import veritabani as db
import yorum
from arayuz.ortak import (bos_durum, claude_a_sor, haftalik_kar_grafigi, kar_grafigi, kart, ozet_kartlari,
                          sayfa_basligi, tablo_bicimi, tespitleri_goster, tl, tr_tarih, yuzde)

sayfa_basligi("Raporlar", "Dönem seç; rakamlar, yorumlar ve grafikler o döneme göre hesaplanır.")
tum = db.satislari_getir()
if tum.empty:
    with kart("rp_bos"):
        bos_durum("Rapor oluşturmak için önce satış eklemelisin.", ":material/bar_chart:")
    st.stop()

bugun = date.today()
c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
secim = c1.segmented_control("Dönem", donemler.DONEMLER, default="Bu ay", key="rp_donem", required=True,
                             wrap=True)
ozel = None
if secim == "Özel":
    ozel = c2.date_input("Tarih aralığı", value=(bugun.replace(day=1), bugun), format="DD.MM.YYYY",
                         key="rp_ozel")
    if len(ozel) != 2:
        st.info("Lütfen takvimden bitiş tarihini de seç.")
        st.stop()
bas, bit, o_bas, o_bit = donemler.aralik(secim, bugun, tum["tarih"].min().date(), ozel)
df = donemler.filtrele(tum, bas, bit)
onceki = donemler.filtrele(tum, o_bas, o_bit) if o_bas else None
gider = db.giderleri_getir(bas, bit)["tutar"].sum()

karsilastirma = f" · karşılaştırma: {tr_tarih(o_bas)} – {tr_tarih(o_bit)}" if o_bas else ""
st.caption(f"{tr_tarih(bas)} – {tr_tarih(bit)} · {len(df)} satış{karsilastirma}")
if df.empty:
    with kart("rp_donem_bos"):
        bos_durum("Bu dönemde satış yok. Yukarıdan başka bir dönem seç.", ":material/event_busy:")
    st.stop()

ciro, kar = df["ciro"].sum(), df["net_kar"].sum()
ozet_kartlari([
    ("Toplam ciro", tl(ciro), f"{len(df)} satış · {int(df['adet'].sum())} adet"),
    ("Toplam maliyet", tl(df["maliyet"].sum()), "Alış + kargo + komisyon"),
    ("Net kâr", tl(kar), f"Kâr marjı {yuzde(kar / ciro * 100 if ciro else 0.0)}"),
    ("Gerçek kâr", tl(kar - gider), f"Ek giderler ({tl(gider)}) düşülmüş" if gider else "Bu dönemde ek gider yok"),
], "rp_ozet")

ozet_sekme, kanal_sekme, urun_sekme = st.tabs(["Özet", "Kanallar ve ürünler", "Ürün yorumu"], key="rp_sekme")

with ozet_sekme:
    urunler = (df.groupby("urun_adi").agg(adet=("adet", "sum"), ciro=("ciro", "sum"), net_kar=("net_kar", "sum"))
                 .sort_values("net_kar", ascending=False))
    en_iyi = urunler.iloc[0]
    with kart("rp_ozet_yorum"):
        st.subheader("Akıllı Özet", anchor=False)
        st.caption("Verilerine bakılarak otomatik çıkarılan tespitler. Ücretsizdir; yapay zeka kullanılmaz.")
        st.markdown(f":material/emoji_events: **En kârlı ürün:** {urunler.index[0]} — net kâr "
                    f"**{tl(en_iyi['net_kar'])}**, {int(en_iyi['adet'])} adet satış, ciro {tl(en_iyi['ciro'])}")
        tespitleri_goster(yorum.akilli_ozet(df, onceki, gider))
        claude_a_sor(yorum.donem_istemi(df, bas, bit))
    with kart("rp_haftalik"):
        st.subheader("Haftalık Kâr", anchor=False)
        haftalik_kar_grafigi(df, bas, bit)

with kanal_sekme:
    sol, sag = st.columns(2)
    with sol, kart("rp_kanal", height="stretch"):
        st.subheader("Kanala Göre Kâr", anchor=False)
        kanallar = (df.groupby("pazar").agg(adet=("adet", "sum"), ciro=("ciro", "sum"),
                                            net_kar=("net_kar", "sum")).sort_values("net_kar", ascending=False))
        kar_grafigi(kanallar.reset_index(), "pazar", "Kanal", yatay=True, yukseklik=max(160, 32 * len(kanallar)),
                    aciklama="Satış kanallarına göre net kâr çubuk grafiği")
        toplam_kar = kanallar["net_kar"].sum()
        st.dataframe(
            tablo_bicimi(pd.DataFrame({
                "Kanal": kanallar.index, "Adet": kanallar["adet"].values, "Ciro": kanallar["ciro"].values,
                "Net kâr": kanallar["net_kar"].values,
                "Kâr payı": (kanallar["net_kar"] / toplam_kar * 100).values if toplam_kar else 0.0,
            }), para=["Ciro", "Net kâr"], yuzdeler=["Kâr payı"], kar=["Net kâr"]),
            hide_index=True, width="stretch", alt="Satış kanallarına göre satış ve kâr tablosu",
        )
    with sag, kart("rp_urun", height="stretch"):
        st.subheader("Ürünlere Göre Kâr", anchor=False)
        st.dataframe(
            tablo_bicimi(pd.DataFrame({"Ürün": urunler.index, "Adet": urunler["adet"].values,
                                       "Ciro": urunler["ciro"].values, "Net kâr": urunler["net_kar"].values}),
                         para=["Ciro", "Net kâr"], kar=["Net kâr"]),
            hide_index=True, width="stretch", height=min(420, 38 * (len(urunler) + 1)),
            alt="Ürünlere göre kâr tablosu",
        )

    sol, sag = st.columns(2)
    for sutun, alan, baslik, sutun_adi, ad in [(sol, "durum", "Sıfır / İkinci El", "Durum", "rp_durum"),
                                                (sag, "kategori", "Kategorilere Göre", "Kategori", "rp_kategori")]:
        with sutun, kart(ad, height="stretch"):
            st.subheader(baslik, anchor=False)
            grup = (df.assign(**{alan: df[alan].replace("", "Belirtilmemiş")})
                      .groupby(alan).agg(adet=("adet", "sum"), ciro=("ciro", "sum"), net_kar=("net_kar", "sum"))
                      .sort_values("net_kar", ascending=False))
            st.dataframe(
                tablo_bicimi(pd.DataFrame({sutun_adi: grup.index,
                                           "Adet": grup["adet"].values, "Ciro": grup["ciro"].values,
                                           "Net kâr": grup["net_kar"].values,
                                           "Marj": (grup["net_kar"] / grup["ciro"] * 100).values}),
                             para=["Ciro", "Net kâr"], yuzdeler=["Marj"], kar=["Net kâr", "Marj"]),
                hide_index=True, width="stretch", alt=f"{baslik} satış ve kâr tablosu",
            )

with urun_sekme, kart("rp_urun_yorum"):
    st.subheader("Ürün Yorumu", anchor=False)
    st.caption("Bir ürünü seç; tüm zamanlardaki satışlarına bakılarak yorumlanır.")
    tum_urunler = tum.groupby("urun_adi")["net_kar"].sum().sort_values(ascending=False).index
    urun = st.selectbox("Ürün", list(tum_urunler), key="rp_urun_sec")
    tespitleri_goster(yorum.urun_yorumu(tum, urun))
    claude_a_sor(yorum.urun_istemi(tum, urun))
