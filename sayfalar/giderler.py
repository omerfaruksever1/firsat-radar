"""Giderler: belirli bir ürüne ait olmayan masraflar (ambalaj, ilan ücreti, abonelik…).
Görünüm: tasarim/05-giderler.html — solda bu ayın dağılımı ve liste, sağda sürekli açık "Gider ekle" formu."""

from datetime import date

import pandas as pd
import streamlit as st

import donemler
import styles
import veritabani as db
from arayuz import formlar
from arayuz.ortak import (AYLAR, bos_durum, gider_excel_dosyasi, kart, kayit_secimi, mesaji_goster, sayfa_basligi, secimli_tablo,
                          tablo_bicimi, tl, tr_tarih)

sayfa_basligi("Giderler", "Ürüne bağlı olmayan masraflar — raporlarda gerçek kârdan düşülür")
mesaji_goster("gider_mesaj")
giderler = db.giderleri_getir()
bugun = date.today()

liste_sutunu, form_sutunu = st.columns([1.55, 1], gap="medium")
with form_sutunu, kart("gd_ekle"):
    st.subheader("Gider ekle", anchor=False)
    formlar.gider_ekle_paneli()

with liste_sutunu:
    if giderler.empty:
        with kart("bos_gd"):
            bos_durum("Henüz gider yok. Kargo poşeti, ilan ücreti, mağaza aboneliği gibi ürüne ait olmayan "
                      "masrafları sağdaki formdan ekle.")
        st.stop()

    def toplam(secim):
        bas, bit, *_ = donemler.aralik(secim, bugun)
        return donemler.filtrele(giderler, bas, bit)

    bu_ay = toplam("Bu ay")
    # Kategori renkleri: dağılım çubuğu ve tablodaki rozetler aynı rengi kullanır
    kategoriler = list(giderler.groupby("kategori")["tutar"].sum().sort_values(ascending=False).index)
    renk = {k: styles.YIGIN_RENKLERI[i % len(styles.YIGIN_RENKLERI)] for i, k in enumerate(kategoriler)}

    with kart("gd_ay"):
        styles.html(
            '<div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:14px">'
            f'<span style="font-size:16px;font-weight:600">{AYLAR[bugun.month - 1]} giderleri</span>'
            f'<span class="fr-mono" style="font-size:22px">{styles.para(bu_ay["tutar"].sum())}</span>'
            "</div>")
        if bu_ay.empty:
            styles.html(f'<div style="color:{styles.RENK["metin2"]}">Bu ay henüz gider yok.</div>')
        else:
            dagilim = bu_ay.groupby("kategori")["tutar"].sum().reindex(
                [k for k in kategoriler if k in set(bu_ay["kategori"])])
            styles.html(styles.yigin_cubuk(list(dagilim.items()), [renk[k] for k in dagilim.index]))
        styles.html(f'<div style="margin:12px 0 6px;font-size:13px;color:{styles.RENK["soluk"]}">'
                    f'Geçen ay {styles.mono(styles.para(toplam("Geçen ay")["tutar"].sum()))} · '
                    f'{bugun.year} toplamı {styles.mono(styles.para(toplam("Bu yıl")["tutar"].sum()))}</div>')

    with kart("gd_liste"):
        tablo = pd.DataFrame({"Tarih": giderler["tarih"], "Kategori": giderler["kategori"],
                              "Açıklama": giderler["aciklama"], "Tutar": giderler["tutar"]})
        stil = tablo_bicimi(tablo, para=["Tutar"], tarih=["Tarih"]).map(
            lambda k: f"color: {renk.get(k, styles.RENK['metin2'])}", subset=["Kategori"])
        secimli_tablo(stil, giderler["id"], "gd_tablo", "gd_secili", alt="Gider kayıtları tablosu",
                      column_config={"Açıklama": st.column_config.TextColumn(width="medium")})
        st.download_button("Excel'e aktar", data=gider_excel_dosyasi(giderler), icon=":material/download:",
                           file_name=f"firsatradar_giderler_{bugun:%Y-%m-%d}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        kayitlar = {int(r.id): r for r in giderler.itertuples()}
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
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
