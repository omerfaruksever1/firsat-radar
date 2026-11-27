"""Fiyat Hesapla: hedef kâra göre her kanalda satış fiyatı, ya da verilen fiyattan her kanalda kâr.
Görünüm: tasarim/07-fiyat-hesapla.html — solda giriş kartı, sağda kanal tablosu."""

import streamlit as st

import fiyat
import styles
import veritabani as db
from arayuz.ortak import PARA, kart, sayfa_basligi, tablo_bicimi, tl, yuzde

MODLAR = ["Hedef kârdan fiyat bul", "Fiyattan kâr hesapla"]
HIZLI_MARJLAR = [15, 20, 25, 30]


def hizli_marj():
    secilen = st.session_state.get("fh_hizli")
    if secilen:
        st.session_state.fh_hedef_marj = float(secilen.strip("%"))


sayfa_basligi("Fiyat Hesapla", "Komisyon ve kargo dahil, her kanalda kaça satman gerektiğini gör")
kanallar = db.kanallari_getir()
stok = db.stoklari_getir()
st.session_state.setdefault("fh_hedef_marj", 25.0)

giris, sonuc_sutunu = st.columns([1, 1.95], gap="small")
with giris, kart("fh_giris", height="stretch"):
    mod = st.segmented_control("Ne hesaplansın?", MODLAR, default=MODLAR[0], key="fh_mod", required=True,
                               width="stretch", label_visibility="collapsed")
    if not stok.empty:
        urunler = {int(r.id): r for r in stok.itertuples()}

        def stoktan_doldur():
            secili = st.session_state.fh_stok
            if secili is not None:
                st.session_state.fh_alis = float(urunler[secili].alis_fiyati)

        st.selectbox("Elimdekilerden ürün seç (isteğe bağlı)", list(urunler), index=None, key="fh_stok",
                     format_func=lambda i: f"{urunler[i].urun_adi} · alış {tl(urunler[i].alis_fiyati)}",
                     placeholder="Seçersen alış fiyatı otomatik dolar", on_change=stoktan_doldur)
    alis = st.number_input("Alış fiyatı ₺ / adet", key="fh_alis", **PARA)
    kargo = st.number_input("Kargo ücreti ₺ / adet", key="fh_kargo",
                            value=float(db.ayar_getir("varsayilan_kargo", "0")), **PARA)
    if mod == MODLAR[0]:
        hedef_turu = st.segmented_control("Hedef", fiyat.HEDEF_TURLERI, default=fiyat.HEDEF_TURLERI[0],
                                          key="fh_hedef_turu", required=True, width="stretch")
        if hedef_turu == fiyat.HEDEF_TURLERI[0]:
            hedef = st.number_input("Hedef kâr marjı %", min_value=0.0, max_value=95.0, step=1.0,
                                    key="fh_hedef_marj", label_visibility="collapsed",
                                    help="Satış fiyatının yüzde kaçı sana kâr kalsın?")
            st.pills("Hızlı seçim", [f"%{m}" for m in HIZLI_MARJLAR], key="fh_hizli", on_change=hizli_marj,
                     label_visibility="collapsed", width="stretch")
        else:
            hedef = st.number_input("Hedef kâr ₺ / adet", value=100.0, key="fh_hedef_tutar",
                                    label_visibility="collapsed", **PARA)
        satis_fiyati = None
    else:
        hedef_turu = hedef = None
        satis_fiyati = st.number_input("Satış fiyatı ₺", value=0.0, key="fh_fiyat", **PARA)
    elden_kargosuz = st.checkbox("Elden satışta kargo yok", value=True, key="fh_elden")

with sonuc_sutunu, kart("fh_sonuc", height="stretch"):
    if alis <= 0 or (mod == MODLAR[1] and not satis_fiyati):
        st.subheader("Kanallara göre sonuç", anchor=False)
        styles.bos_kart("Hesaplama için soldan <b>alış fiyatını</b> gir." if alis <= 0 else
                        "Karşılaştırmak için <b>satış fiyatını</b> gir.")
        st.stop()

    sonuc = fiyat.kanal_tablosu(alis, kargo, kanallar, hedef_turu, hedef, satis_fiyati,
                                kargosuz=("Elden",) if elden_kargosuz else ())
    gecerli = sonuc.dropna(subset=["fiyat"])
    ust_sol, ust_sag = st.columns([3, 2], vertical_alignment="center")
    if mod == MODLAR[0]:
        sonuc = sonuc.sort_values("fiyat", na_position="last")
        hedef_metni = yuzde(hedef, 0) if hedef_turu == fiyat.HEDEF_TURLERI[0] else tl(hedef, 0)
        ust_sol.subheader(f"{hedef_metni} kâr için önerilen satış fiyatı", anchor=False)
        ust_sol.caption("Komisyon oranları Ayarlar'dan gelir · fiyatlar yukarı yuvarlanır")
        if not gecerli.empty:
            en_iyi = gecerli.loc[gecerli["fiyat"].idxmin()]
            ust_sag.html(f'<div style="text-align:right">{styles.badge("En düşük fiyat: " + en_iyi["kanal"], "yesil")}'
                         "</div>")
    else:
        sonuc = sonuc.sort_values("net_kar", ascending=False)
        en_iyi = sonuc.iloc[0]
        ust_sol.subheader(f"{tl(satis_fiyati, 0)} fiyattan her kanalda kâr", anchor=False)
        ust_sol.caption("Komisyon oranları Ayarlar'dan gelir")
        ust_sag.html(f'<div style="text-align:right">{styles.badge("En çok kazandıran: " + en_iyi["kanal"], "yesil")}'
                     "</div>")

    st.dataframe(
        tablo_bicimi(sonuc[["kanal", "oran", "fiyat", "komisyon", "kargo", "net_kar", "marj"]].rename(
            columns={"kanal": "Kanal", "oran": "Komisyon", "fiyat": "Satış fiyatı", "komisyon": "Kesinti",
                     "kargo": "Kargo", "net_kar": "Net kâr", "marj": "Marj"}),
                     para=["Satış fiyatı", "Kesinti", "Kargo", "Net kâr"], yuzdeler=["Komisyon", "Marj"],
                     kar=["Net kâr", "Marj"]),
        hide_index=True, width="stretch", alt="Satış kanallarına göre fiyat ve kâr tablosu")
    if len(gecerli) < len(sonuc):
        st.caption(":orange[:material/warning:] Komisyon + hedef marj %100'ü geçtiği için bazı kanallarda bu "
                   "hedefe ulaşılamıyor (—).")
    if (kanallar["komisyon_orani"] == 0).all():
        st.caption(":orange[:material/warning:] Hiçbir kanalın komisyon oranı girilmemiş; sonuçlar komisyonsuz "
                   "hesaplandı. Oranları **Ayarlar** sayfasından gir.")
    else:
        st.caption("Komisyon oranları Ayarlar sayfasında girdiğin değerlerden gelir. Oranı 0 olan kanallarda "
                   "komisyon düşülmez.")
