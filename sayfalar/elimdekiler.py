"""Elimdekiler: aldığın ama henüz satmadığın ürünler (stok). Buradan tek tıkla satış yapılır.
Görünüm: tasarim/03-elimdekiler.html — solda liste, sağda sürekli açık "Ürün ekle" formu."""

import pandas as pd
import streamlit as st

import styles
import veritabani as db
import yorum
from arayuz import formlar
from arayuz.ortak import (bos_durum, kart, kayit_secimi, mesaji_goster, ozet_kartlari, sayfa_basligi,
                          secimli_tablo, tablo_bicimi, tespitleri_goster, tr_tarih)

ORTA, UZUN = 15, 30  # bekleme rengi sınırları (gün)
SIRALAMA = ["En uzun bekleyen", "En yeni", "En çok para bağlı", "Ada göre"]


def bekleme_stili(gun):
    if gun > UZUN:
        return f"color: {styles.RENK['zarar']}; background-color: #2A1517"
    if gun >= ORTA:
        return f"color: {styles.RENK['uyari']}; background-color: #2A2111"
    return f"color: {styles.RENK['kar']}; background-color: #12261D"


sayfa_basligi("Elimdekiler", "Aldığın ama henüz satmadığın ürünler")
mesaji_goster("stok_mesaj")
stok = db.stoklari_getir()

liste_sutunu, form_sutunu = st.columns([2.2, 1], gap="medium")

with form_sutunu, kart("el_ekle"):
    st.subheader("Ürün ekle", anchor=False)
    formlar.stok_ekle_paneli()

with liste_sutunu:
    if stok.empty:
        with kart("bos_el"):
            bos_durum("Elinde bekleyen ürün yok. Bir ürünü aldığında sağdaki **Ürün ekle** formuyla kaydet; "
                      "sattığında tek tıkla satışa dönüştür. Böylece hangi ürünün kaç gündür beklediğini ve elinde "
                      "ne kadar para bağlı olduğunu görürsün.")
        st.stop()

    potansiyel = ((stok["hedef_fiyat"] - stok["alis_fiyati"]) * stok["kalan"])[stok["hedef_fiyat"] > 0].sum()
    uzun = int((stok["bekleme_gun"] > UZUN).sum())
    ozet_kartlari([
        dict(baslik="Bağlı para", deger=styles.para(stok["sermaye"].sum()),
             alt=f"{len(stok)} ürün · {int(stok['kalan'].sum())} adet"),
        dict(baslik="Hedef fiyattan potansiyel kâr", deger=styles.para(potansiyel),
             deger_rengi=styles.kar_rengi(potansiyel), alt="Kargo ve komisyon hariç"),
        dict(baslik="Ortalama bekleme", deger=f"{stok['bekleme_gun'].mean():.0f} gün",
             alt=f"{uzun} ürün {UZUN}+ gündür bekliyor" if uzun else "Uzun bekleyen ürün yok",
             alt_rengi=styles.RENK["uyari"] if uzun else None),
    ])

    with kart("el_liste"):
        c1, c2, c3 = st.columns([2, 1, 1])
        arama = c1.text_input("Ürün ara", placeholder="Ürün ara…", key="el_arama", label_visibility="collapsed")
        kategoriler = ["Tüm kategoriler", *sorted(k for k in stok["kategori"].unique() if k)]
        kategori = c2.selectbox("Kategori", kategoriler, key="el_kategori", label_visibility="collapsed")
        siralama = c3.selectbox("Sırala", SIRALAMA, key="el_sirala", label_visibility="collapsed")

        gorunen = stok
        if arama:
            gorunen = gorunen[gorunen["urun_adi"].map(yorum.kucuk_harf).str.contains(yorum.kucuk_harf(arama),
                                                                                   regex=False)]
        if kategori != kategoriler[0]:
            gorunen = gorunen[gorunen["kategori"] == kategori]
        gorunen = {
            "En uzun bekleyen": lambda d: d.sort_values("bekleme_gun", ascending=False),
            "En yeni": lambda d: d.sort_values("alis_tarihi", ascending=False),
            "En çok para bağlı": lambda d: d.sort_values("sermaye", ascending=False),
            "Ada göre": lambda d: d.sort_values("urun_adi", key=lambda s: s.map(yorum.kucuk_harf)),
        }[siralama](gorunen)

        tablo = pd.DataFrame({
            "Ürün": gorunen["urun_adi"], "Adet": gorunen["kalan"], "Alış": gorunen["alis_fiyati"],
            "Hedef": gorunen["hedef_fiyat"], "Bekliyor": gorunen["bekleme_gun"],
            "Bilgi": [" · ".join(x for x in [d, k, n] if x)
                      for d, k, n in zip(gorunen["durum"], gorunen["kategori"], gorunen["kaynak"])],
            "Alış tarihi": gorunen["alis_tarihi"], "Not": gorunen["notlar"],
        })
        stil = (tablo_bicimi(tablo, para=["Alış", "Hedef"], tarih=["Alış tarihi"], sifir_bos=["Hedef"])
                .format(lambda v: f"{v} gün", subset=["Bekliyor"]).map(bekleme_stili, subset=["Bekliyor"]))
        secimli_tablo(stil, gorunen["id"], "el_tablo", "el_secili", alt="Elimdeki ürünler tablosu",
                      column_config={"Ürün": st.column_config.TextColumn(width="medium")})
        styles.html(f'<div style="font-size:13px;color:{styles.RENK["soluk"]}">Bekleme rengi: '
                    f'<span style="color:{styles.RENK["kar"]}">0–{ORTA - 1} gün</span> · '
                    f'<span style="color:{styles.RENK["uyari"]}">{ORTA}–{UZUN}</span> · '
                    f'<span style="color:{styles.RENK["zarar"]}">{UZUN}+</span> — Sat\'a basınca alış bilgileri '
                    "hazır gelen satış formu açılır.</div>")

        kayitlar = {int(r.id): r for r in gorunen.itertuples()}
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

    with kart("el_tespit"):
        st.subheader("Akıllı özet", anchor=False)
        tespitleri_goster(yorum.stok_ozeti(stok))
