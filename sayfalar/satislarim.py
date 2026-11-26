"""Satışlarım: satış listesi, arama/filtre, Excel'e aktarma; ekleme ve düzenleme açılır pencerede."""

from datetime import date

import pandas as pd
import streamlit as st

import veritabani as db
import yorum
from arayuz import formlar
from arayuz.ortak import (bos_durum, excel_dosyasi, kart, kayit_secimi, mesaji_goster, sag_butonlar,
                          sayfa_basligi, secenekler, secimli_tablo, tablo_bicimi, tr_tarih)

sag = sayfa_basligi("Satışlarım", "Satışlarını gör, ara, düzenle ve Excel'e aktar.")
with sag_butonlar(sag):
    if st.button("Yeni satış", icon=":material/add:", type="primary"):
        formlar.yeni_satis_penceresi()
mesaji_goster("satis_mesaj")

tum = db.satislari_getir()
if tum.empty:
    with kart("st_bos"):
        bos_durum("Henüz satış kaydı yok. Sağ üstteki **Yeni satış** düğmesiyle ilk satışını ekle. Önce aldığın "
                  "ürünleri **Elimdekiler**'e kaydedip oradan da satabilirsin.", ":material/receipt_long:")
    st.stop()

with kart("st_liste"):
    c1, c2, c3, c4 = st.columns([3, 2, 2, 2], vertical_alignment="bottom")
    arama = c1.text_input("Ürün ara", icon=":material/search:", placeholder="Ürün adının bir kısmını yaz",
                          key="st_arama")
    kanal_filtre = c2.multiselect("Satış kanalı", secenekler(db.kanal_adlari(), tum["pazar"].unique()),
                                  placeholder="Tüm kanallar", key="st_kanal")
    durum_filtre = c3.multiselect("Durum", db.DURUMLAR, placeholder="Hepsi", key="st_durum")
    gorunen = tum
    if arama:
        gorunen = gorunen[gorunen["urun_adi"].map(yorum.kucuk_harf).str.contains(yorum.kucuk_harf(arama),
                                                                               regex=False)]
    if kanal_filtre:
        gorunen = gorunen[gorunen["pazar"].isin(kanal_filtre)]
    if durum_filtre:
        gorunen = gorunen[gorunen["durum"].isin(durum_filtre)]
    c4.download_button(
        "Excel'e aktar", icon=":material/download:", data=excel_dosyasi(gorunen),
        file_name=f"firsatradar_satislar_{date.today():%Y-%m-%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch",
        help="Ekranda listelenen (filtrelenmiş) kayıtları, tüm ayrıntılarıyla Excel dosyası olarak indirir.",
    )

    st.caption(f"{len(gorunen)} / {len(tum)} satış gösteriliyor. Ayrıntılar için bir satıra tıkla.")
    tablo = pd.DataFrame({
        "Tarih": gorunen["tarih"], "Ürün": gorunen["urun_adi"], "Durum": gorunen["durum"],
        "Kanal": gorunen["pazar"], "Adet": gorunen["adet"], "Alış": gorunen["alis_fiyati"],
        "Satış": gorunen["satis_fiyati"], "Net kâr": gorunen["net_kar"], "Marj": gorunen["marj"],
    })
    secimli_tablo(tablo_bicimi(tablo, para=["Alış", "Satış", "Net kâr"], yuzdeler=["Marj"], tarih=["Tarih"],
                               kar=["Net kâr", "Marj"]),
                  gorunen["id"], "st_tablo", "st_secili", alt="Satış kayıtları tablosu")

    kayitlar = {int(r.id): r for r in gorunen.itertuples()}
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    with c1:
        secili = kayit_secimi("Seçili satış", kayitlar,
                              lambda i: f"No {i} · {tr_tarih(kayitlar[i].tarih)} · {kayitlar[i].urun_adi} · "
                                        f"{kayitlar[i].pazar}", "st_secili")
    with c2:
        if st.button("Düzenle / sil", icon=":material/edit:", disabled=secili is None):
            formlar.satis_duzenle_penceresi(secili)
