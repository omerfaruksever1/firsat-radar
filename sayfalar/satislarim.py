"""Satışlarım: satış listesi, arama/filtre, Excel'e aktarma; ekleme ve düzenleme açılır pencerede.
Görünüm: tasarim/04-satislarim.html."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

import styles
import veritabani as db
import yorum
from arayuz import formlar
from arayuz.ortak import (AYLAR, bos_durum, excel_dosyasi, kart, kayit_secimi, mesaji_goster, sag_butonlar,
                          sayfa_basligi, secimli_tablo, tablo_bicimi, tr_tarih)

DONEMLER = ["Bu hafta", "Bu ay", "Son 90 gün", "Tümü"]

tum = db.satislari_getir()
bugun = date.today()
bu_ay = tum[tum["tarih"].dt.date >= bugun.replace(day=1)]
ozet = (f"{AYLAR[bugun.month - 1]} ayında {len(bu_ay)} satış · {styles.para(bu_ay['ciro'].sum())} ciro · "
        f"{styles.mono(styles.para(bu_ay['net_kar'].sum()) + ' net', styles.kar_rengi(bu_ay['net_kar'].sum()))}")
sag = sayfa_basligi("Satışlarım", ozet if not tum.empty else "Satışlarını gör, ara, düzenle ve Excel'e aktar.")

if tum.empty:
    with sag_butonlar(sag):
        if st.button("Yeni satış", icon=":material/add:", type="primary"):
            formlar.yeni_satis_penceresi()
    mesaji_goster("satis_mesaj")
    with kart("bos_st"):
        bos_durum("Henüz satış kaydı yok. Sağ üstteki **Yeni satış** düğmesiyle ilk satışını ekle. Önce aldığın "
                  "ürünleri **Elimdekiler**'e kaydedip oradan da satabilirsin.")
    st.stop()

# ---------- Filtreler ----------
c1, c2, c3, c4 = st.columns([2.2, 2.4, 1.3, 1.5], vertical_alignment="center")
arama = c1.text_input("Ara", placeholder="Ürün, kanal veya not ara…", key="st_arama", label_visibility="collapsed")
donem = c2.segmented_control("Dönem", DONEMLER, default="Tümü", key="st_donem", required=True,
                             label_visibility="collapsed")
kanallar = ["Kanal: Tümü", *sorted(set(db.kanal_adlari()) | set(tum["pazar"].unique()))]
kanal = c3.selectbox("Kanal", kanallar, key="st_kanal", label_visibility="collapsed")
sadece_zarar = c4.toggle("Sadece zarardakiler", key="st_zarar")

gorunen = tum
if arama:
    aranan = yorum.kucuk_harf(arama)
    metin = (gorunen["urun_adi"] + " " + gorunen["pazar"] + " " + gorunen["notlar"]).map(yorum.kucuk_harf)
    gorunen = gorunen[metin.str.contains(aranan, regex=False)]
baslangic = {"Bu hafta": bugun - timedelta(days=bugun.weekday()), "Bu ay": bugun.replace(day=1),
             "Son 90 gün": bugun - timedelta(days=89)}.get(donem)
if baslangic:
    gorunen = gorunen[gorunen["tarih"].dt.date >= baslangic]
if kanal != kanallar[0]:
    gorunen = gorunen[gorunen["pazar"] == kanal]
if sadece_zarar:
    gorunen = gorunen[gorunen["net_kar"] < 0]

with sag_butonlar(sag):
    st.download_button(
        "Excel'e aktar", data=excel_dosyasi(gorunen),
        file_name=f"firsatradar_satislar_{bugun:%Y-%m-%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Ekranda listelenen (filtrelenmiş) kayıtları, tüm ayrıntılarıyla Excel dosyası olarak indirir.")
    if st.button("Yeni satış", icon=":material/add:", type="primary"):
        formlar.yeni_satis_penceresi()
mesaji_goster("satis_mesaj")

# ---------- Liste ----------
with kart("st_liste"):
    if gorunen.empty:
        bos_durum("Bu filtrelere uyan satış yok. Dönemi **Tümü** yap ya da aramayı temizle.")
        st.stop()
    kesinti = (gorunen["kargo"] + gorunen["komisyon"]) * gorunen["adet"]
    tablo = pd.DataFrame({
        "Tarih": gorunen["tarih"], "Ürün": gorunen["urun_adi"], "Kanal": gorunen["pazar"],
        "Durum": gorunen["durum"].replace("İkinci el", "2. el"), "Adet": gorunen["adet"],
        "Alış": gorunen["alis_fiyati"] * gorunen["adet"], "Satış": gorunen["ciro"], "Kesinti": kesinti,
        "Satış kârı": gorunen["net_kar"], "Marj": gorunen["marj"],
    })
    secimli_tablo(tablo_bicimi(tablo, para=["Alış", "Satış", "Kesinti", "Satış kârı"], yuzdeler=["Marj"],
                               tarih=["Tarih"], kar=["Satış kârı", "Marj"]),
                  gorunen["id"], "st_tablo", "st_secili", alt="Satış kayıtları tablosu",
                  column_config={"Ürün": st.column_config.TextColumn(width="medium")})

    toplam_kar = gorunen["net_kar"].sum()
    parcalar = [("Adet", str(int(gorunen["adet"].sum())), None),
                ("Alış", styles.para(tablo["Alış"].sum()), None),
                ("Satış", styles.para(gorunen["ciro"].sum()), None),
                ("Kesinti", styles.para(kesinti.sum()), styles.RENK["metin2"]),
                ("Satış kârı", styles.para(toplam_kar, isaret=True), styles.kar_rengi(toplam_kar))]
    styles.html(
        '<div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 28px;padding:12px 2px 4px;'
        f'border-top:1px solid {styles.RENK["kenarlik"]}"><b>Toplam</b>'
        f'<span style="color:{styles.RENK["metin2"]};flex:1">{len(gorunen)} / {len(tum)} satış gösteriliyor</span>'
        + "".join(f'<span style="color:{styles.RENK["soluk"]};font-size:12px">{ad.upper()} '
                  f'{styles.mono(f"<b>{deger}</b>", renk)}</span>' for ad, deger, renk in parcalar)
        + "</div>")

    kayitlar = {int(r.id): r for r in gorunen.itertuples()}
    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    with c1:
        secili = kayit_secimi("Seçili satış", kayitlar,
                              lambda i: f"No {i} · {tr_tarih(kayitlar[i].tarih)} · {kayitlar[i].urun_adi} · "
                                        f"{kayitlar[i].pazar}", "st_secili")
    with c2:
        if st.button("Düzenle / sil", icon=":material/edit:", disabled=secili is None):
            formlar.satis_duzenle_penceresi(secili)
