"""Fırsat Takibi: almayı düşündüğün ürünlerin listesi. Uygulama her kanaldaki satış kârını hesaplar, fırsatları
sıralar; "Claude'a sor" ile piyasa fiyatı araştırılır, "Satın aldım" ile ürün Elimdekiler'e geçer.
Görünüm: tasarim/02-urun-taramalari.html."""

import pandas as pd
import streamlit as st

import fiyat
import styles
import veritabani as db
import yorum
from arayuz import formlar
from arayuz.ortak import (ana_renk, bos_durum, claude_a_sor, kart, kayit_secimi, mesaji_goster, ozet_kartlari,
                          sag_butonlar, sayfa_basligi, secimli_tablo, tablo_bicimi, tespitleri_goster, tl, yuzde,
                          zarar_rengi)

SIRALAMA = {"Satış kârı %": "marj", "Kâr / adet": "net_kar", "Toplam kâr": "toplam_kar"}

hepsi = db.firsatlari_getir()
sayilar = hepsi["takip"].value_counts()
sag = sayfa_basligi("Fırsat Takibi", "Gözüne kestirdiğin ürünler · her kanalda komisyon ve kargo düşülmüş kâr",
                    styles.badge(f"{sayilar.get(db.TAKIPTE, 0)} takipte", "mavi") if not hepsi.empty else None)
with sag_butonlar(sag):
    if st.button("Fırsat ekle", icon=":material/add:", type="primary"):
        formlar.firsat_ekle_penceresi()
mesaji_goster("firsat_mesaj")

if hepsi.empty:
    with kart("bos_ft"):
        bos_durum("Takip listen boş. Bir ilanda, toptancıda ya da mağaza indiriminde gözüne bir ürün kestirdiğinde "
                  "**Fırsat ekle** ile buraya kaydet:\n"
                  "1. Ürünü, alış fiyatını ve bildiğin kadarıyla kaça satabileceğini yaz.\n"
                  "2. Satış fiyatını bilmiyorsan **Claude'a sor** ile internetten araştırt (ücretsiz).\n"
                  "3. Uygulama her kanalda komisyon ve kargo düşülmüş satış kârını hesaplar, fırsatları sıralar.\n"
                  "4. Aldığında **Satın aldım** de; ürün Elimdekiler'e geçer.")
    st.stop()

kanallar = db.kanallari_getir()
gorunum = st.segmented_control(
    "Liste", [db.TAKIPTE, db.ALINDI, db.VAZGECILDI], key="ft_gorunum", default=db.TAKIPTE,
    format_func=lambda t: f"{t} ({sayilar.get(t, 0)})", label_visibility="collapsed") or db.TAKIPTE
df = fiyat.firsatlari_degerlendir(hepsi[hepsi["takip"] == gorunum], kanallar)

if gorunum == db.TAKIPTE and not df.empty:
    fiyatli = df[df["marj"].notna()]
    guclu = int((df["degerlendirme"] == fiyat.DEGERLENDIRMELER[0]).sum())
    beklenen_ciro = (fiyatli["piyasa_fiyati"] * fiyatli["adet"]).sum()
    beklenen_kar = fiyatli["toplam_kar"].sum()
    ortalama = beklenen_kar / beklenen_ciro * 100 if beklenen_ciro else None
    en_iyi = fiyatli.iloc[0] if not fiyatli.empty else None
    ozet_kartlari([
        dict(baslik="Takipteki ürün", deger=str(len(df)),
             alt=f"▲ {guclu} güçlü fırsat" if guclu else "Henüz güçlü fırsat yok",
             alt_rengi=styles.RENK["kar"] if guclu else None),
        dict(baslik="Ortalama satış kârı", deger=yuzde(ortalama, 0) if ortalama is not None else "—",
             deger_rengi=styles.kar_rengi(ortalama or 0), alt="Tahmini fiyatı girilen ürünlerde"),
        dict(baslik="En iyi fırsat", deger=yuzde(en_iyi["marj"], 0) if en_iyi is not None else "—",
             alt=en_iyi["urun_adi"] if en_iyi is not None else "Tahmini satış fiyatı gir"),
        dict(baslik="Beklenen satış kârı", deger=styles.para(beklenen_kar), deger_rengi=styles.kar_rengi(beklenen_kar),
             alt=f"Gereken sermaye {styles.para((df['alis_fiyati'] * df['adet']).sum())}"),
    ])

with kart("ft_liste"):
    baslik_sol, baslik_sag = st.columns([3, 2], vertical_alignment="center")
    with baslik_sol:
        st.subheader({db.TAKIPTE: "Fırsat ürünler", db.ALINDI: "Satın aldıkların",
                      db.VAZGECILDI: "Vazgeçtiklerin"}[gorunum], anchor=False)
        st.caption("Bir satıra tıkla: Satın aldım, Düzenle ve Claude'a sor aşağıda çıkar.")
    if df.empty:
        bos_durum({db.TAKIPTE: "Takipte ürün yok. **Fırsat ekle** ile yeni bir ürün ekleyebilirsin.",
                   db.ALINDI: "Henüz listeden satın aldığın ürün yok.",
                   db.VAZGECILDI: "Vazgeçtiğin ürün yok."}[gorunum])
        st.stop()
    with sag_butonlar(baslik_sag):
        siralama = st.segmented_control("Sırala", list(SIRALAMA), default="Satış kârı %", key="ft_sirala",
                                        label_visibility="collapsed") or "Satış kârı %"
    df = df.sort_values([SIRALAMA[siralama], "id"], ascending=False, na_position="last").reset_index(drop=True)

    tablo = pd.DataFrame({
        "Ürün": df["urun_adi"], "Alış": df["alis_fiyati"],
        "Kaynak": [k or t for t, k in zip(df["kaynak_turu"], df["kaynak"])],
        "Önerilen": df["piyasa_fiyati"], "En iyi pazar": df["satis_kanali"].fillna("—"),
        # Piyasa fiyatı yoksa kâr hesaplanamaz: 0 yazılır, tabloda "—" görünür
        "Marj %": df["marj"].fillna(0), "Kâr / adet": df["net_kar"].fillna(0), "Adet": df["adet"],
        "Değerlendirme": df["degerlendirme"], "Durum": df["durum"], "Listede (gün)": df["bekleme_gun"],
        "Link": df["link"].replace("", None),
    })
    renkler = {fiyat.DEGERLENDIRMELER[0]: f"color: {styles.RENK['kar']}; font-weight: 600",
               fiyat.DEGERLENDIRMELER[1]: f"color: {ana_renk()}",
               fiyat.DEGERLENDIRMELER[2]: f"color: {styles.RENK['uyari']}",
               fiyat.DEGERLENDIRMELER[3]: f"color: {zarar_rengi()}; font-weight: 600",
               fiyat.DEGERLENDIRMELER[4]: f"color: {styles.RENK['soluk']}"}
    stil = tablo_bicimi(tablo, para=["Alış", "Önerilen", "Kâr / adet"], yuzdeler=["Marj %"],
                        kar=["Kâr / adet", "Marj %"], sifir_bos=["Önerilen", "Kâr / adet", "Marj %"])
    stil = stil.map(lambda v: renkler.get(v, ""), subset=["Değerlendirme"])
    secimli_tablo(stil, df["id"], "ft_tablo", "ft_secili", alt="Fırsat takip listesi",
                  column_config={"Ürün": st.column_config.TextColumn(width="medium"),
                                 "Link": st.column_config.LinkColumn(display_text="Aç")})
    styles.html(
        f'<div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;font-size:13px;'
        f'color:{styles.RENK["soluk"]}"><span>Satış kârı = Tahmini satış − Alış − Komisyon − Kargo (adet başına)</span>'
        f'<span><span style="color:{styles.RENK["kar"]}">●</span> %{fiyat.GUCLU_MARJ}+ güçlü &nbsp; '
        f'<span style="color:{ana_renk()}">●</span> %{fiyat.ORTA_MARJ}–{fiyat.GUCLU_MARJ} orta &nbsp; '
        f'<span style="color:{styles.RENK["uyari"]}">●</span> &lt;%{fiyat.ORTA_MARJ} zayıf</span></div>')

    kayitlar = {int(r.id): r for r in df.itertuples()}
    secili = kayit_secimi("Seçili ürün", kayitlar,
                          lambda i: f"{kayitlar[i].urun_adi} · alış {tl(kayitlar[i].alis_fiyati, 0)} · "
                                    f"{kayitlar[i].degerlendirme}", "ft_secili")
    if secili is not None:
        r = kayitlar[secili]
        with st.container(horizontal=True):
            if gorunum == db.TAKIPTE and st.button("Satın aldım", icon=":material/shopping_bag:", type="primary"):
                formlar.firsat_satin_al_penceresi(secili)
            if st.button("Düzenle / sil", icon=":material/edit:"):
                formlar.firsat_duzenle_penceresi(secili)
            if r.link:
                st.link_button("İlanı aç", r.link, icon=":material/open_in_new:")
            if gorunum == db.ALINDI:
                st.page_link("sayfalar/elimdekiler.py", label="Elimdekiler'e git", icon=":material/inventory_2:")
        if r.piyasa_fiyati > 0:
            with st.expander("Tüm kanallarda kâr", icon=":material/compare_arrows:"):
                karsilastirma = fiyat.kanal_tablosu(r.alis_fiyati, r.kargo, kanallar, fiyat=r.piyasa_fiyati)
                st.dataframe(
                    tablo_bicimi(karsilastirma[["kanal", "oran", "kargo", "komisyon", "net_kar", "marj"]].rename(
                        columns={"kanal": "Kanal", "oran": "Komisyon oranı", "kargo": "Kargo",
                                 "komisyon": "Komisyon", "net_kar": "Satış kârı / adet", "marj": "Marj"}),
                        para=["Kargo", "Komisyon", "Satış kârı / adet"], yuzdeler=["Komisyon oranı", "Marj"],
                        kar=["Satış kârı / adet", "Marj"]),
                    hide_index=True, width="stretch")
                st.caption(f"{tl(r.piyasa_fiyati)} fiyattan satılırsa, adet başına. Komisyon oranlarını Ayarlar'dan "
                           "değiştirebilirsin; elden satışta kargo düşülmez.")
        claude_a_sor(yorum.firsat_istemi(r), "Claude'a sor: bu ürün kaça satılır, almaya değer mi?")

if gorunum == db.TAKIPTE:
    with kart("ft_tespit"):
        st.subheader("Akıllı özet", anchor=False)
        tespitleri_goster(yorum.firsat_ozeti(df))
        fiyatsiz = df[df["marj"].isna()]
        if len(fiyatsiz) > 1:
            claude_a_sor(yorum.firsat_listesi_istemi(fiyatsiz),
                         f"Claude'a sor: fiyatı bilinmeyen {len(fiyatsiz)} ürünün piyasa fiyatı")
