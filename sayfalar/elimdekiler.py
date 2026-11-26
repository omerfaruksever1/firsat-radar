"""Elimdekiler: aldığın ama henüz satmadığın ürünler (stok). Buradan tek tıkla satış yapılır."""

import pandas as pd
import streamlit as st

import veritabani as db
import yorum
from arayuz import formlar
from arayuz.ortak import (bos_durum, kart, kayit_secimi, mesaji_goster, ozet_kartlari, sag_butonlar,
                          sayfa_basligi, secimli_tablo, tablo_bicimi, tespitleri_goster, tl, tr_tarih)

sag = sayfa_basligi("Elimdekiler", "Aldığın ama henüz satmadığın ürünler. Satınca buradan tek tıkla satışa dönüştür.")
with sag_butonlar(sag):
    if st.button("Ürün ekle", icon=":material/add:", type="primary"):
        formlar.stok_ekle_penceresi()
mesaji_goster("stok_mesaj")

stok = db.stoklari_getir()
if stok.empty:
    with kart("el_bos"):
        bos_durum("Elinde bekleyen ürün yok. Bir ürünü aldığında **Ürün ekle** ile buraya kaydet; sattığında "
                  "tek tıkla satışa dönüştür. Böylece hangi ürünün kaç gündür beklediğini ve elinde ne kadar "
                  "para bağlı olduğunu görürsün.", ":material/inventory_2:")
    st.stop()

ozet_kartlari([
    ("Elimdeki ürün", f"{int(stok['kalan'].sum())} adet", f"{len(stok)} farklı kayıt"),
    ("Bağlı sermaye", tl(stok["sermaye"].sum()), "Alış fiyatı × elde kalan adet"),
    ("Ortalama bekleme", f"{stok['bekleme_gun'].mean():.0f} gün", "Alış tarihinden bugüne"),
    ("En uzun bekleyen", f"{stok['bekleme_gun'].max()} gün", stok.loc[stok["bekleme_gun"].idxmax(), "urun_adi"]),
], "el_ozet")

with kart("el_tespit"):
    tespitleri_goster(yorum.stok_ozeti(stok))

with kart("el_liste"):
    st.subheader("Ürünler", anchor=False)
    tablo = pd.DataFrame({
        "Ürün": stok["urun_adi"], "Durum": stok["durum"], "Kategori": stok["kategori"],
        "Nereden": stok["kaynak"], "Alış tarihi": stok["alis_tarihi"], "Bekleme (gün)": stok["bekleme_gun"],
        "Kalan": stok["kalan"], "Alış fiyatı": stok["alis_fiyati"],
        "Hedef fiyat": stok["hedef_fiyat"], "Not": stok["notlar"],
    })
    secimli_tablo(tablo_bicimi(tablo, para=["Alış fiyatı", "Hedef fiyat"], tarih=["Alış tarihi"],
                               sifir_bos=["Hedef fiyat"]),
                  stok["id"], "el_tablo", "el_secili", alt="Elimdeki ürünler tablosu")

    kayitlar = {int(r.id): r for r in stok.itertuples()}
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    with c1:
        secili = kayit_secimi("Seçili ürün", kayitlar,
                              lambda i: f"{kayitlar[i].urun_adi} · {kayitlar[i].kalan} adet · "
                                        f"{tr_tarih(kayitlar[i].alis_tarihi)}", "el_secili")
    with c2.container(horizontal=True):
        if st.button("Sat", icon=":material/sell:", type="primary", disabled=secili is None):
            formlar.stoktan_sat_penceresi(secili)
        if st.button("Düzenle / sil", icon=":material/edit:", disabled=secili is None):
            formlar.stok_duzenle_penceresi(secili)
