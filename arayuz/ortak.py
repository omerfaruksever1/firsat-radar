"""Bütün sayfaların kullandığı görünüm parçaları: biçimlendirme, kartlar, tablolar, grafikler."""

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import styles

PROJE = Path(__file__).resolve().parent.parent
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
PARA = dict(min_value=0.0, step=1.0, format="%.2f")


# ---------- Tema ----------

def zarar_rengi():
    """Tablolarda eksi tutarların rengi."""
    return styles.RENK["zarar"]


def kar_rengi():
    """Tablolarda artı tutarların rengi."""
    return styles.RENK["kar"]


def ana_renk():
    """Temanın ana (mavi) rengi; config.toml'daki primaryColor ile aynı."""
    return styles.RENK["vurgu"]


def tema_uygula():
    """"Gece Terminali" görünümünün ortak CSS'i (styles.py). Renklerin çoğu .streamlit/config.toml'dadır."""
    styles.inject_css()


def menu_hazirla(sayaclar=None):
    """Kenar çubuğu: logo ve menüdeki sayaçlar ({url_yolu: sayı})."""
    st.logo(str(PROJE / "varliklar" / "logo.svg"), size="large")
    styles.inject_css(sayaclar, yalnizca_sayaclar=True)


def durum_karti():
    """Kenar çubuğunun altındaki küçük durum kartı: veriler nerede, bugünün yedeği alındı mı?"""
    import veritabani as db
    if not db.yerel_mi():
        styles.durum_karti("İnternet veritabanına bağlı")
        return
    yedek = db.VERITABANI_YOLU.parent / "yedekler" / f"otomatik_{date.today().isoformat()}.db"
    if yedek.exists():
        styles.durum_karti("Bilgisayardaki dosya · bugünün yedeği alındı")
    else:
        styles.durum_karti("Bilgisayardaki dosya · bugün yedek yok", styles.RENK["uyari"])


# ---------- Biçimlendirme ----------

def tl(tutar, basamak=2):
    """1234.5 → ₺1.234,50 (basamak=0 ise ₺1.235)"""
    metin = f"{abs(tutar):,.{basamak}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'-' if tutar < 0 else ''}₺{metin}"


def yuzde(deger, basamak=1):
    """12.5 → %12,5 ; -3 → -%3,0"""
    return f"{'-' if deger < 0 else ''}%{abs(deger):.{basamak}f}".replace(".", ",")


def tr_tarih(gun):
    return gun.strftime("%d.%m.%Y")


def tablo_bicimi(df, para=(), yuzdeler=(), tarih=(), kar=(), sifir_bos=()):
    """Tabloyu Türkçe biçimde gösterir (₺1.234,50, %12,5, 26.11.2026); `kar` sütunlarında eksiler
    turuncu yazılır, `sifir_bos` sütunlarında 0 yerine "—" yazılır. Değerler sayı olarak kalır, böylece
    sütun başlığına tıklayınca doğru sıralanır. Boş (NaN) değerler de "—" gösterilir."""
    def bos_ya_da(bicimle, sifir_de_bos=False):
        return lambda v: "—" if pd.isna(v) or (sifir_de_bos and v == 0) else bicimle(v)

    def isaretli(v):
        return ("+" if v > 0 else "") + tl(v)

    bicim = {**{s: bos_ya_da(isaretli if s in kar else tl, s in sifir_bos) for s in para},
             **{s: bos_ya_da(yuzde, s in sifir_bos) for s in yuzdeler},
             **{s: bos_ya_da(tr_tarih) for s in tarih}}
    stil = df.style.format(bicim)
    if kar:
        eksi, arti = zarar_rengi(), kar_rengi()
        stil = stil.map(lambda v: "" if pd.isna(v) or v == 0 else f"color: {eksi if v < 0 else arti}",
                        subset=list(kar))
    return stil


def secenekler(sabit, kayitlilar, secili=None):
    """Açılır liste seçenekleri: sabit liste + daha önce girilenler (+ kaydın mevcut değeri)."""
    return list(dict.fromkeys([*sabit, *kayitlilar, *([secili] if secili else [])]))


# ---------- Yerleşim ----------

def kart(ad, **ayarlar):
    """Şablondaki beyaz, kenarlıklı kart."""
    return st.container(border=True, key=f"kart_{ad}", **ayarlar)


def sayfa_basligi(baslik, aciklama, rozet=None, oran=(3, 2)):
    """Sol tarafta başlık + açıklama (güvenli HTML olabilir); sağdaki sütunu (butonlar vb. için) döndürür."""
    sol, sag = st.columns(list(oran), vertical_alignment="center")
    with sol:
        styles.baslik(baslik, aciklama, rozet)
    return sag


def sag_butonlar(sutun):
    """Başlığın sağındaki sütunda sağa yaslı, yan yana düğmeler için kap."""
    return sutun.container(horizontal=True, horizontal_alignment="right")


def ozet_kartlari(kartlar, ad=None):
    """Üstteki KPI kartları. Her kart (başlık, değer, alt yazı) ya da styles.kpi_card() ayarları sözlüğüdür."""
    styles.kpi_satiri([styles.kpi_card(**k) if isinstance(k, dict) else styles.kpi_card(*k) for k in kartlar])


def mesaji_goster(anahtar):
    mesaj = st.session_state.pop(anahtar, None)
    if mesaj:
        tur, metin = mesaj
        if tur == "ok":
            st.success(metin, icon=":material/check_circle:")
        else:
            st.error(metin, icon=":material/error:")


def bos_durum(metin, ikon=None):
    """Boş durum: kesik çizgili koyu kart. Metindeki **kalın** yazılar korunur."""
    parcalar = styles.kacis(metin).split("**")
    guvenli = "".join(f"<b>{p}</b>" if i % 2 else p for i, p in enumerate(parcalar)).replace("\n", "<br>")
    styles.bos_kart(guvenli)


def tespitleri_goster(tespitler):
    """Akıllı özet maddeleri: iyi ▲ yeşil, uyarı ▼ kırmızı, bilgi ● mavi."""
    styles.tespitler_html(tespitler)


def claude_a_sor(metin, baslik="Claude'a sor: internetten fiyat araştırmasıyla ayrıntılı yorum"):
    """Verileri ve hazır soruyu kopyalanabilir gösterir; kullanıcı claude.ai'ye yapıştırır (ek ücret yok)."""
    with st.expander(baslik, icon=":material/travel_explore:"):
        st.markdown("1. Aşağıdaki kutunun sağ üstündeki **kopyala** simgesine tıkla.\n"
                    "2. **claude.ai'yi aç** düğmesine bas, metni yapıştırıp gönder.\n\n"
                    "Ek ücret yoktur; mevcut Claude hesabınla çalışır. Cevap claude.ai'de görünür.")
        st.code(metin, language=None, wrap_lines=True, height=220)
        st.link_button("claude.ai'yi aç", "https://claude.ai/new", icon=":material/open_in_new:")


def secimli_tablo(stil, kimlikler, anahtar, secim_anahtari, **ayarlar):
    """Satırına tıklanabilen tablo. Tıklanan satırın kimliği `secim_anahtari` seçim kutusuna aktarılır,
    böylece kayıt hem tablodan hem de seçim kutusundan seçilebilir."""
    kimlikler = list(kimlikler)

    def aktar():
        satirlar = st.session_state[anahtar].selection.rows
        if satirlar:
            st.session_state[secim_anahtari] = kimlikler[satirlar[0]]

    st.dataframe(stil, key=anahtar, on_select=aktar, selection_mode="single-row", hide_index=True,
                 width="stretch", **ayarlar)


def kayit_secimi(etiket, kimlikler, etiketle, anahtar):
    """Tablonun altındaki kayıt seçim kutusu. Seçili kayıt artık yoksa (silindiyse) seçim temizlenir."""
    kimlikler = list(kimlikler)
    if st.session_state.get(anahtar) not in kimlikler:
        st.session_state[anahtar] = None
    return st.selectbox(etiket, kimlikler, format_func=etiketle, key=anahtar,
                        placeholder="Tablodan bir satıra tıkla veya buradan seç")


# ---------- Grafikler ----------

# Eksen etiketlerini Türkçe para biçiminde yazar: 12345 → ₺12.345
TL_EKSEN = "'₺' + replace(format(datum.value, ',.0f'), regexp(',', 'g'), '.')"


def kar_grafigi(veri, kategori, kategori_basligi, yatay=False, yukseklik=320, aciklama=""):
    """Satış kârıa göre çubuk grafik. Kâr ana renkte, zarar uyarı renginde (renkler temadan gelir)."""
    veri = veri.assign(
        durum=["Kâr" if v >= 0 else "Zarar" for v in veri["net_kar"]],
        tutar=veri["net_kar"].map(tl),
    )
    kat = dict(field=kategori, type="nominal", sort=None, title=kategori_basligi)
    deger = dict(field="net_kar", type="quantitative", title="Satış kârı",
                 axis=alt.Axis(labelExpr=TL_EKSEN))
    grafik = alt.Chart(veri).mark_bar(cornerRadius=3).encode(
        **({"y": alt.Y(**kat), "x": alt.X(**deger)} if yatay
           else {"x": alt.X(**kat, axis=alt.Axis(labelAngle=0)), "y": alt.Y(**deger)}),
        color=alt.Color("durum:N", scale=alt.Scale(domain=["Kâr", "Zarar"]), legend=None),
        tooltip=[alt.Tooltip(f"{kategori}:N", title=kategori_basligi),
                 alt.Tooltip("tutar:N", title="Satış kârı")],
    ).properties(height=yukseklik, background="transparent")
    st.altair_chart(grafik, width="stretch", alt=aciklama)


def haftalik_kar_grafigi(df, baslangic, bitis, yukseklik=320, eksen_basligi="Hafta başlangıcı (Pazartesi)"):
    """Her hafta (pazartesiden başlayarak) toplam satış kârını çubuk grafik olarak çizer."""
    veri = df.copy()
    veri["hafta"] = veri["tarih"] - pd.to_timedelta(veri["tarih"].dt.day_of_week, unit="D")
    haftalik = veri.groupby("hafta")["net_kar"].sum()
    ilk_hafta = pd.Timestamp(baslangic - timedelta(days=baslangic.weekday()))
    tum_haftalar = pd.date_range(ilk_hafta, pd.Timestamp(bitis), freq="7D")
    haftalik = haftalik.reindex(tum_haftalar, fill_value=0.0)

    kar_grafigi(
        pd.DataFrame({"hafta": [tr_tarih(h) for h in haftalik.index], "net_kar": haftalik.values}),
        "hafta", eksen_basligi, yukseklik=yukseklik,
        aciklama="Haftalara göre satış kârı çubuk grafiği",
    )


def son_haftalar_grafigi(df, bugun, hafta_sayisi=4, yukseklik=210):
    """Son haftaların (pazartesiden başlayan) satış kârı: bu hafta ana renkte, öncekiler koyu; tutarlar
    çubukların üstünde. Görünüm: tasarim/01-genel-bakis.html."""
    bu_hafta = pd.Timestamp(bugun - timedelta(days=bugun.weekday()))
    haftalar = [bu_hafta - pd.Timedelta(weeks=i) for i in range(hafta_sayisi - 1, -1, -1)]
    veri = df.assign(hafta=df["tarih"] - pd.to_timedelta(df["tarih"].dt.day_of_week, unit="D"))
    toplam = veri.groupby("hafta")["net_kar"].sum().reindex(haftalar, fill_value=0.0)
    tablo = pd.DataFrame({
        "hafta": [f"{h.day} {AYLAR[h.month - 1][:3]}" for h in toplam.index],
        "net_kar": toplam.values,
        "etiket": [styles.para(v) for v in toplam.values],
        "renk": [styles.RENK["vurgu"] if h == bu_hafta else "#24335A" for h in toplam.index],
    })
    x = alt.X("hafta:N", sort=None, title=None, axis=alt.Axis(labelAngle=0, domain=True, ticks=False,
                                                              labelColor=styles.RENK["soluk"], labelFontSize=12,
                                                              domainColor="#232937"))
    taban = alt.Chart(tablo).encode(x=x)
    cubuk = taban.mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
        y=alt.Y("net_kar:Q", title=None, axis=None), color=alt.Color("renk:N", scale=None),
        tooltip=[alt.Tooltip("hafta:N", title="Hafta başı"), alt.Tooltip("etiket:N", title="Satış kârı")])
    yazi = taban.mark_text(dy=-8, font="JetBrains Mono", fontSize=12, color=styles.RENK["metin2"]).encode(
        y=alt.Y("net_kar:Q"), text="etiket:N")
    grafik = (cubuk + yazi).properties(height=yukseklik, background="transparent").configure_view(stroke=None)
    st.altair_chart(grafik, width="stretch", alt="Son haftaların satış kârını çubuk grafiği")


# ---------- Excel ----------

def excel_dosyasi(df):
    tablo = pd.DataFrame({
        "No": df["id"],
        "Tarih": df["tarih"].dt.date,
        "Ürün": df["urun_adi"],
        "Durum": df["durum"],
        "Kategori": df["kategori"],
        "Satış kanalı": df["pazar"],
        "Nereden alındı": df["kaynak"],
        "Adet": df["adet"],
        "Alış fiyatı (₺)": df["alis_fiyati"],
        "Satış fiyatı (₺)": df["satis_fiyati"],
        "Kargo (₺/adet)": df["kargo"],
        "Komisyon (₺/adet)": df["komisyon"],
        "Ciro (₺)": df["ciro"],
        "Maliyet (₺)": df["maliyet"],
        "Satış kârı (₺)": df["net_kar"],
        "Kâr marjı (%)": df["marj"].round(2),
        "Not": df["notlar"],
    })
    tampon = BytesIO()
    with pd.ExcelWriter(tampon, engine="openpyxl") as yazici:
        tablo.to_excel(yazici, index=False, sheet_name="Satışlar")
        sayfa = yazici.sheets["Satışlar"]
        for sutun in sayfa.columns:
            en_uzun = max(len(str(h.value or "")) for h in sutun)
            sayfa.column_dimensions[sutun[0].column_letter].width = min(en_uzun + 3, 40)
        for satir in sayfa.iter_rows(min_row=2, min_col=2, max_col=2):
            satir[0].number_format = "DD.MM.YYYY"
        sayfa.freeze_panes = "A2"
    return tampon.getvalue()


def gider_excel_dosyasi(df):
    tablo = pd.DataFrame({"Tarih": df["tarih"].dt.date, "Kategori": df["kategori"],
                          "Açıklama": df["aciklama"], "Tutar (₺)": df["tutar"]})
    tampon = BytesIO()
    with pd.ExcelWriter(tampon, engine="openpyxl") as yazici:
        tablo.to_excel(yazici, index=False, sheet_name="Giderler")
        sayfa = yazici.sheets["Giderler"]
        for sutun in sayfa.columns:
            en_uzun = max(len(str(h.value or "")) for h in sutun)
            sayfa.column_dimensions[sutun[0].column_letter].width = min(en_uzun + 3, 40)
        for satir in sayfa.iter_rows(min_row=2, min_col=1, max_col=1):
            satir[0].number_format = "DD.MM.YYYY"
        sayfa.freeze_panes = "A2"
    return tampon.getvalue()
