"""Fiyat Hesapla: hedef kâra göre her kanalda satış fiyatı, ya da verilen fiyattan her kanalda kâr."""

import streamlit as st

import fiyat
import veritabani as db
from arayuz.ortak import PARA, kart, sayfa_basligi, tablo_bicimi, tl, yuzde

sayfa_basligi("Fiyat Hesapla", "Komisyonu ve kargoyu hesaba katarak her satış kanalında kaça satman gerektiğini "
                               "ya da ne kadar kazanacağını gör.")
kanallar = db.kanallari_getir()
stok = db.stoklari_getir()

with kart("fh_giris"):
    if not stok.empty:
        urunler = {int(r.id): r for r in stok.itertuples()}

        def stoktan_doldur():
            secili = st.session_state.fh_stok
            if secili is not None:
                st.session_state.fh_alis = float(urunler[secili].alis_fiyati)

        st.selectbox("Elimdekilerden ürün seç (isteğe bağlı)", list(urunler), index=None, key="fh_stok",
                     format_func=lambda i: f"{urunler[i].urun_adi} · alış {tl(urunler[i].alis_fiyati)}",
                     placeholder="Seçersen alış fiyatı otomatik dolar", on_change=stoktan_doldur)
    c1, c2 = st.columns(2)
    alis = c1.number_input("Alış fiyatı ₺ / adet", key="fh_alis", **PARA)
    kargo = c2.number_input("Kargo ücreti ₺ / adet", key="fh_kargo",
                            value=float(db.ayar_getir("varsayilan_kargo", "0")), **PARA)
    mod = st.segmented_control("Ne hesaplansın?", ["Hedef kârdan fiyat bul", "Fiyattan kâr hesapla"],
                               default="Hedef kârdan fiyat bul", key="fh_mod", required=True)
    c1, c2 = st.columns(2)
    if mod == "Hedef kârdan fiyat bul":
        hedef_turu = c1.radio("Hedef", fiyat.HEDEF_TURLERI, horizontal=True, key="fh_hedef_turu")
        if hedef_turu == fiyat.HEDEF_TURLERI[0]:
            hedef = c2.number_input("Hedef kâr marjı %", min_value=0.0, max_value=95.0, value=25.0, step=1.0,
                                    key="fh_hedef_marj", help="Satış fiyatının yüzde kaçı sana kâr kalsın?")
        else:
            hedef = c2.number_input("Hedef kâr ₺ / adet", value=100.0, key="fh_hedef_tutar", **PARA)
        satis_fiyati = None
    else:
        hedef_turu = hedef = None
        satis_fiyati = c1.number_input("Satış fiyatı ₺", value=0.0, key="fh_fiyat", **PARA)
    elden_kargosuz = st.checkbox("Elden satışta kargo yok", value=True, key="fh_elden")

if alis <= 0:
    st.caption("Hesaplama için alış fiyatını gir.")
    st.stop()
if mod == "Fiyattan kâr hesapla" and not satis_fiyati:
    st.caption("Karşılaştırmak için satış fiyatını gir.")
    st.stop()

sonuc = fiyat.kanal_tablosu(alis, kargo, kanallar, hedef_turu, hedef, satis_fiyati,
                            kargosuz=("Elden",) if elden_kargosuz else ())
with kart("fh_sonuc"):
    st.subheader("Kanallara Göre Sonuç", anchor=False)
    gecerli = sonuc.dropna(subset=["fiyat"])
    if mod == "Hedef kârdan fiyat bul":
        sonuc = sonuc.sort_values("fiyat", na_position="last")
        if not gecerli.empty:
            en_iyi = gecerli.loc[gecerli["fiyat"].idxmin()]
            st.markdown(f":blue[:material/check_circle:] Hedefine en düşük fiyatla **{en_iyi['kanal']}** kanalında "
                        f"ulaşırsın: **{tl(en_iyi['fiyat'], 0)}**. Fiyatlar yukarı yuvarlanmıştır.")
    else:
        sonuc = sonuc.sort_values("net_kar", ascending=False)
        en_iyi = sonuc.iloc[0]
        st.markdown(f":blue[:material/check_circle:] {tl(satis_fiyati, 0)} fiyatla en çok **{en_iyi['kanal']}** "
                    f"kanalında kazanırsın: adet başına **{tl(en_iyi['net_kar'])}** "
                    f"(marj {yuzde(en_iyi['marj'])}).")
    if len(gecerli) < len(sonuc):
        st.caption(":orange[:material/warning:] Komisyon + hedef marj %100'ü geçtiği için bazı kanallarda bu "
                   "hedefe ulaşılamıyor (—).")
    st.dataframe(
        tablo_bicimi(sonuc.rename(columns={"kanal": "Kanal", "oran": "Komisyon oranı", "kargo": "Kargo",
                                           "fiyat": "Satış fiyatı", "komisyon": "Komisyon", "net_kar": "Net kâr",
                                           "marj": "Marj"}),
                     para=["Kargo", "Satış fiyatı", "Komisyon", "Net kâr"], yuzdeler=["Komisyon oranı", "Marj"],
                     kar=["Net kâr", "Marj"]),
        hide_index=True, width="stretch", alt="Satış kanallarına göre fiyat ve kâr tablosu",
    )
    if (kanallar["komisyon_orani"] == 0).all():
        st.caption(":orange[:material/warning:] Hiçbir kanalın komisyon oranı girilmemiş; sonuçlar komisyonsuz "
                   "hesaplandı. Oranları **Ayarlar** sayfasından gir.")
    else:
        st.caption("Komisyon oranları Ayarlar sayfasından gelir. Oranı 0 olan kanallarda komisyon düşülmez.")
