"""Ürün Taramaları: şimdilik örnek veri; gerçek tarama 3. aşamada gelecek."""

import streamlit as st

import ornek_tarama
from arayuz.ortak import kart, ozet_kartlari, sag_butonlar, sayfa_basligi, tl, yuzde


def tl0(tutar):
    return tl(tutar, 0)


sag = sayfa_basligi("Ürün Taramaları", "Son tarama: bugün 09:00 · Sonraki otomatik tarama: yarın 09:00 (örnek)")
with sag_butonlar(sag):
    ipucu = "Gerçek ürün taraması 3. aşamada eklenecek."
    st.button("Tarama Zamanla", disabled=True, help=ipucu)
    st.button("Şimdi Tara", type="primary", disabled=True, help=ipucu)

firsat = ornek_tarama.firsatlar()
ozet_kartlari([
    ("Bulunan fırsat", f"{len(firsat)} ürün", "Son taramada · örnek veri"),
    ("Ortalama net kâr", yuzde(firsat["marj"].mean(), 0), "Fırsat ürünlerde · örnek veri"),
    ("En yüksek satılabilirlik", str(firsat["satilabilirlik"].max()),
     firsat.loc[firsat["satilabilirlik"].idxmax(), "urun"]),
    ("30 günde tahmini satış", f"~{firsat['tahmini_satis'].sum()} adet", "Tüm fırsat ürünlerde"),
], "ut_ozet")

with kart("ut_tarama"):
    sol, sag = st.columns([4, 1], vertical_alignment="bottom")
    sol.subheader("Tarama Sonuçları: Fırsat Ürünler", anchor=False)
    sol.caption("Sistem ürünleri bulur, fiyatları karşılaştırır ve en uygun pazarı önerir. :orange-badge[Örnek veri]")
    siralama = sag.selectbox("Sırala", list(ornek_tarama.SIRALAMA), key="ut_sirala")
    df = ornek_tarama.firsatlar().sort_values(ornek_tarama.SIRALAMA[siralama], ascending=False)
    st.dataframe(
        df[["urun", "alis", "kaynak", "satis", "pazar", "marj", "kar_adet", "satilabilirlik", "tahmini_satis"]]
        .style.format({"alis": tl0, "satis": tl0, "kar_adet": tl0, "marj": lambda v: yuzde(v, 0),
                       "tahmini_satis": "~{} adet"}),
        hide_index=True, width="stretch", alt="Fırsat ürünleri tablosu (örnek veri)",
        column_config={
            "urun": st.column_config.TextColumn("Ürün", width="medium"),
            "alis": "Alış",
            "kaynak": "Kaynak",
            "satis": "Önerilen satış",
            "pazar": "En iyi pazar",
            "marj": "Net kâr",
            "kar_adet": "Kâr / adet",
            "satilabilirlik": st.column_config.ProgressColumn("Satılabilirlik", min_value=0, max_value=100,
                                                              format="%d"),
            "tahmini_satis": "30 günde tahmini",
        },
    )
    st.caption("Net kâr = Satış fiyatı − Alış − Pazar komisyonu − Kargo. Satılabilirlik; talep, rakip sayısı ve "
               "fiyat farkından hesaplanan 0–100 arası puandır.")
