"""Raporlar: dönem seçimi, önceki dönemle karşılaştırmalı KPI kartları, kâr grafiği, akıllı özet / ürün yorumu,
kanallara göre kâr ve "Claude'a sor". Görünüm: tasarim/06-raporlar.html."""

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

import donemler
import styles
import veritabani as db
import yorum
from arayuz.ortak import (AYLAR, bos_durum, claude_a_sor, kart, ozet_kartlari, sag_butonlar,
                          tablo_bicimi, tespitleri_goster, tr_tarih, yuzde)

ONCEKI_RENK = "#2E3A55"


def degisim_metni(simdi, once, ters=False):
    """("▲ %12", renk). `ters`: artışın kötü olduğu değerler (giderler) için renkler tersine döner."""
    if once is None or not once:
        return "", None
    oran = (simdi - once) / abs(once) * 100
    iyi = (oran >= 0) != ters
    return f"{'▲' if oran >= 0 else '▼'} {yuzde(abs(oran), 0)}", styles.RENK["kar"] if iyi else styles.RENK["zarar"]


def karsilastirma_grafigi(df, onceki, bas, bit, o_bas):
    """Bu dönem (mavi) ve önceki dönem (koyu) satış kârını yan yana: kısa dönemde haftalık, uzun dönemde aylık."""
    aylik = (bit - bas).days > 62

    def dilim(veri, baslangic):
        if veri is None or veri.empty:
            return pd.Series(dtype=float)
        if aylik:
            anahtar = (veri["tarih"].dt.year - baslangic.year) * 12 + veri["tarih"].dt.month - baslangic.month
        else:
            anahtar = (veri["tarih"].dt.date.map(lambda g: (g - baslangic).days // 7))
        return veri.groupby(anahtar)["net_kar"].sum()

    adet = ((bit.year - bas.year) * 12 + bit.month - bas.month + 1) if aylik else (bit - bas).days // 7 + 1
    etiketler = [AYLAR[(bas.month - 1 + i) % 12][:3] if aylik else f"{i + 1}. hafta" for i in range(adet)]
    simdi = dilim(df, bas).reindex(range(adet), fill_value=0.0)
    satirlar = [{"dilim": e, "donem": "Bu dönem", "net_kar": v} for e, v in zip(etiketler, simdi.values)]
    if o_bas is not None:
        once = dilim(onceki, o_bas).reindex(range(adet), fill_value=0.0)
        satirlar += [{"dilim": e, "donem": "Önceki dönem", "net_kar": v} for e, v in zip(etiketler, once.values)]
    veri = pd.DataFrame(satirlar)
    veri["tutar"] = veri["net_kar"].map(styles.para)
    grafik = alt.Chart(veri).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("dilim:N", sort=etiketler, title=None,
                axis=alt.Axis(labelAngle=0, ticks=False, labelColor=styles.RENK["soluk"], domainColor="#232937")),
        xOffset=alt.XOffset("donem:N", sort=["Önceki dönem", "Bu dönem"]),
        y=alt.Y("net_kar:Q", title=None, axis=alt.Axis(labelExpr="'₺' + replace(format(datum.value, ',.0f'), "
                                                                 "regexp(',', 'g'), '.')", gridColor="#181D26",
                                                       domain=False, ticks=False, labelColor=styles.RENK["soluk"])),
        color=alt.Color("donem:N", scale=alt.Scale(domain=["Bu dönem", "Önceki dönem"],
                                                   range=[styles.RENK["vurgu"], ONCEKI_RENK]), legend=None),
        tooltip=[alt.Tooltip("dilim:N", title="Dilim"), alt.Tooltip("donem:N", title="Dönem"),
                 alt.Tooltip("tutar:N", title="Satış kârı")],
    ).properties(height=320, background="transparent").configure_view(stroke=None)
    st.altair_chart(grafik, width="stretch", alt="Bu dönem ve önceki dönemin satış kârını çubuk grafiği")


tum = db.satislari_getir()
bugun = date.today()
baslik_sol, sag = st.columns([2, 3], vertical_alignment="center")
if tum.empty:
    with baslik_sol:
        styles.baslik("Raporlar", "Dönem seç; rakamlar, yorumlar ve grafikler o döneme göre hesaplanır.")
    with kart("bos_rp"):
        bos_durum("Rapor oluşturmak için önce satış eklemelisin. **Satışlarım → Yeni satış** ile başlayabilirsin.")
    st.stop()

with sag_butonlar(sag):
    secim = st.segmented_control("Dönem", donemler.DONEMLER, default="Bu ay", key="rp_donem", required=True,
                                 wrap=True, label_visibility="collapsed")
ozel = None
if secim == "Özel":
    ozel = st.date_input("Tarih aralığı", value=(bugun.replace(day=1), bugun), format="DD.MM.YYYY", key="rp_ozel")
    if len(ozel) != 2:
        st.info("Lütfen takvimden bitiş tarihini de seç.")
        st.stop()
bas, bit, o_bas, o_bit = donemler.aralik(secim, bugun, tum["tarih"].min().date(), ozel)
df = donemler.filtrele(tum, bas, bit)
onceki = donemler.filtrele(tum, o_bas, o_bit) if o_bas else None
gider = db.giderleri_getir(bas, bit)["tutar"].sum()
onceki_gider = db.giderleri_getir(o_bas, o_bit)["tutar"].sum() if o_bas else None

karsilastirma = f" · {tr_tarih(o_bas)} – {tr_tarih(o_bit)} ile karşılaştırılıyor" if o_bas else ""
with baslik_sol:
    styles.baslik("Raporlar", f"{tr_tarih(bas)} – {tr_tarih(bit)}{karsilastirma}")
if df.empty:
    with kart("bos_rp_donem"):
        bos_durum("Bu dönemde satış yok. Yukarıdan başka bir dönem seç.")
    st.stop()

# ---------- KPI kartları ----------
ciro, kar = df["ciro"].sum(), df["net_kar"].sum()
marj = kar / ciro * 100 if ciro else 0.0
o_ciro = onceki["ciro"].sum() if onceki is not None else None
o_kar = onceki["net_kar"].sum() if onceki is not None else None
o_marj = (o_kar / o_ciro * 100) if o_ciro else None
gercek = kar - gider
hedef = float(db.ayar_getir("aylik_hedef", "0"))

ciro_alt, kar_alt, gider_alt = degisim_metni(ciro, o_ciro), degisim_metni(kar, o_kar), degisim_metni(
    gider, onceki_gider, ters=True)
if o_marj is not None:
    fark = marj - o_marj
    marj_alt = (f"{'▲' if fark >= 0 else '▼'} {abs(fark):.1f} puan".replace(".", ","),
                styles.RENK["kar"] if fark >= 0 else styles.RENK["zarar"])
else:
    marj_alt = ("Satış kârı ÷ ciro", None)
if hedef > 0 and secim in ("Bu ay", "Geçen ay"):
    gercek_alt = (f"Hedef {styles.para(hedef)} · {yuzde(gercek / hedef * 100, 0)}", None)
else:
    gercek_alt = ("Satış kârı − giderler", None)

ozet_kartlari([
    dict(baslik="Ciro", deger=styles.para(ciro), alt=ciro_alt[0] or f"{len(df)} satış · {int(df['adet'].sum())} adet",
         alt_rengi=ciro_alt[1]),
    dict(baslik="Satış kârı", deger=styles.para(kar), deger_rengi=styles.kar_rengi(kar),
         alt=kar_alt[0] or "Komisyon + kargo düşülmüş", alt_rengi=kar_alt[1]),
    dict(baslik="Giderler", deger=styles.para(-gider) if gider else styles.para(0),
         alt=gider_alt[0] or ("Ek giderler" if gider else "Bu dönemde ek gider yok"), alt_rengi=gider_alt[1]),
    dict(baslik="Gerçek kâr", deger=styles.para(gercek), deger_rengi=styles.kar_rengi(gercek), alt=gercek_alt[0],
         vurgulu=True),
    dict(baslik="Kâr marjı", deger=yuzde(marj), alt=marj_alt[0], alt_rengi=marj_alt[1]),
])

# ---------- Grafik + yorumlar ----------
sol, sag = st.columns([1.6, 1], gap="small")
with sol, kart("rp_grafik", height="stretch"):
    ust = st.columns([3, 2], vertical_alignment="center")
    ust[0].subheader("Satış kârı " + ("(aylık)" if (bit - bas).days > 62 else "(haftalık)"), anchor=False)
    if o_bas:
        ust[1].html(f'<div style="text-align:right;font-size:13px;color:{styles.RENK["metin2"]}">'
                    f'<span class="kare" style="display:inline-block;width:10px;height:10px;border-radius:2px;'
                    f'background:{styles.RENK["vurgu"]};margin-right:6px"></span>Bu dönem &nbsp; '
                    f'<span style="display:inline-block;width:10px;height:10px;border-radius:2px;'
                    f'background:{ONCEKI_RENK};margin-right:6px"></span>Önceki</div>')
    karsilastirma_grafigi(df, onceki, bas, bit, o_bas)

with sag, kart("rp_yorum", height="stretch"):
    sekme = st.segmented_control("Yorum", ["Akıllı özet", "Ürün yorumu"], default="Akıllı özet", key="rp_sekme",
                                 required=True, label_visibility="collapsed")
    if sekme == "Akıllı özet":
        urunler = df.groupby("urun_adi")["net_kar"].sum().sort_values(ascending=False)
        tespitler = yorum.akilli_ozet(df, onceki, gider)
        tespitler.append(("bilgi", f"En kârlı ürün: {urunler.index[0]}, {styles.para(urunler.iloc[0], isaret=True)}."))
        tespitleri_goster(tespitler)
    else:
        tum_urunler = tum.groupby("urun_adi")["net_kar"].sum().sort_values(ascending=False).index
        urun = st.selectbox("Ürün", list(tum_urunler), key="rp_urun_sec",
                            help="Seçilen ürünün tüm zamanlardaki satışlarına bakılarak yorumlanır.")
        tespitleri_goster(yorum.urun_yorumu(tum, urun))

sol, sag = st.columns([1.6, 1], gap="small")
with sol, kart("rp_kanal", height="stretch"):
    st.subheader("Kanallara göre satış kârı", anchor=False)
    kanallar = df.groupby("pazar")["net_kar"].sum().sort_values(ascending=False)
    styles.html(styles.yatay_cubuklar(list(kanallar.items())))

with sag, kart("rp_claude", height="stretch"):
    st.subheader("Claude'a sor", anchor=False)
    st.caption("Hazır metni kopyalayıp claude.ai'ye yapıştır; satış bilgileri oraya gönderilmiş olur.")
    if sekme == "Ürün yorumu":
        claude_a_sor(yorum.urun_istemi(tum, urun), "Metni göster: bu ürün için")
    else:
        claude_a_sor(yorum.donem_istemi(df, bas, bit), "Metni göster: bu dönem için")

# ---------- Kategoriler + son 6 ay ----------
sol, sag = st.columns([1, 1.6], gap="small")
with sol, kart("rp_kategori", height="stretch"):
    st.subheader("Kategoriye göre satış kârı", anchor=False)
    kategorili = df[df["kategori"] != ""]
    if kategorili.empty:
        styles.bos_kart("Satışlara kategori yazarsan hangi ürün türünün daha çok kazandırdığını burada görürsün.")
    else:
        styles.html(styles.yatay_cubuklar(list(
            kategorili.groupby("kategori")["net_kar"].sum().sort_values(ascending=False).items())))

with sag, kart("rp_6ay", height="stretch"):
    st.subheader("Son 6 ay: satış kârı ve gerçek kâr", anchor=False)
    ay_basi = [(bugun.replace(day=1) - pd.DateOffset(months=i)).date() for i in range(5, -1, -1)]
    tum_gider = db.giderleri_getir()
    satirlar = []
    for ay in ay_basi:
        ay_sonu = (pd.Timestamp(ay) + pd.offsets.MonthEnd(0)).date()
        satis_kari = donemler.filtrele(tum, ay, ay_sonu)["net_kar"].sum()
        ay_gideri = donemler.filtrele(tum_gider, ay, ay_sonu)["tutar"].sum() if not tum_gider.empty else 0.0
        satirlar.append({"ay": AYLAR[ay.month - 1][:3], "tur": "Satış kârı", "tutar_sayi": satis_kari})
        satirlar.append({"ay": AYLAR[ay.month - 1][:3], "tur": "Gerçek kâr", "tutar_sayi": satis_kari - ay_gideri})
    veri = pd.DataFrame(satirlar)
    veri["tutar"] = veri["tutar_sayi"].map(styles.para)
    etiketler = list(dict.fromkeys(veri["ay"]))
    st.altair_chart(
        alt.Chart(veri).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X("ay:N", sort=etiketler, title=None,
                    axis=alt.Axis(labelAngle=0, ticks=False, labelColor=styles.RENK["soluk"], domainColor="#232937")),
            xOffset=alt.XOffset("tur:N", sort=["Satış kârı", "Gerçek kâr"]),
            y=alt.Y("tutar_sayi:Q", title=None, axis=alt.Axis(
                labelExpr="'₺' + replace(format(datum.value, ',.0f'), regexp(',', 'g'), '.')",
                gridColor="#181D26", domain=False, ticks=False, labelColor=styles.RENK["soluk"])),
            color=alt.Color("tur:N", scale=alt.Scale(domain=["Satış kârı", "Gerçek kâr"],
                                                     range=[ONCEKI_RENK, styles.RENK["kar"]]),
                            legend=alt.Legend(title=None, orient="top", labelColor=styles.RENK["metin2"])),
            tooltip=[alt.Tooltip("ay:N", title="Ay"), alt.Tooltip("tur:N", title="Tür"),
                     alt.Tooltip("tutar:N", title="Tutar")],
        ).properties(height=260, background="transparent").configure_view(stroke=None),
        width="stretch", alt="Son 6 ayın satış kârı ve gerçek kârı çubuk grafiği")

# ---------- Ayrıntılı tablolar ----------
with st.expander("Ayrıntılı tablolar: ürünler, sıfır / ikinci el, kategoriler", icon=":material/table_chart:"):
    def grup_tablosu(alan, baslik):
        grup = (df.assign(**{alan: df[alan].replace("", "Belirtilmemiş")})
                  .groupby(alan).agg(adet=("adet", "sum"), ciro=("ciro", "sum"), net_kar=("net_kar", "sum"))
                  .sort_values("net_kar", ascending=False))
        st.dataframe(
            tablo_bicimi(pd.DataFrame({baslik: grup.index, "Adet": grup["adet"].values, "Ciro": grup["ciro"].values,
                                       "Satış kârı": grup["net_kar"].values,
                                       "Marj": (grup["net_kar"] / grup["ciro"] * 100).values}),
                         para=["Ciro", "Satış kârı"], yuzdeler=["Marj"], kar=["Satış kârı", "Marj"]),
            hide_index=True, width="stretch", alt=f"{baslik} satış ve kâr tablosu")

    grup_tablosu("urun_adi", "Ürün")
    c1, c2 = st.columns(2)
    with c1:
        grup_tablosu("durum", "Durum")
    with c2:
        grup_tablosu("kategori", "Kategori")
