""""Gece Terminali" görünümü: ortak CSS ve HTML parçaları (KPI kartı, rozet, boş durum, liste satırı…).

Renkler tasarim/README.md'deki tablodan gelir; temel tema .streamlit/config.toml'dadır. Burada yalnızca
Streamlit temasının ayarlayamadığı ayrıntılar (kart zemini, rakam yazı tipi, menü vurgusu, sayaçlar) vardır.
Kullanıcıdan gelen bütün metinler (ürün adı, açıklama…) HTML'e konmadan önce `kacis()` ile güvenli hale getirilir.
"""

from html import escape

import streamlit as st

RENK = {
    "zemin": "#0B0D12", "yan_menu": "#0F1218", "kart": "#11151C", "input": "#0E1117",
    "kenarlik": "#1F2531", "kenarlik2": "#2A3140", "ayirici": "#181D26", "aktif": "#1A2030",
    "metin": "#E7EAF0", "metin2": "#8C95A5", "soluk": "#6B7486",
    "vurgu": "#4C7DFF", "kar": "#3DD68C", "zarar": "#F26D6D", "uyari": "#F5A524",
}
MONO = "'JetBrains Mono', ui-monospace, monospace"

_CSS = f"""
<style>
/* Kartlar: anahtarı "kart_" ile başlayan kaplar */
[class*="st-key-kart_"] {{
  background: {RENK['kart']}; border-color: {RENK['kenarlik']} !important; border-radius: 12px !important;
}}
[class*="st-key-kart_vurgu"] {{ border-color: {RENK['vurgu']} !important; background: #121A2C; }}
[class*="st-key-kart_bos"] {{ border-style: dashed !important; background: #0E1117; }}

/* Rakamlar: JetBrains Mono */
.fr-mono, [data-testid="stMetricValue"] {{ font-family: {MONO}; font-weight: 500; }}

/* KPI kartları */
.fr-kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px;
  margin-bottom: 0.5rem; }}
.fr-kpi {{ padding: 18px; border: 1px solid {RENK['kenarlik']}; border-radius: 12px; background: {RENK['kart']};
  display: flex; flex-direction: column; gap: 8px; min-width: 0; }}
.fr-kpi.vurgu {{ border-color: {RENK['vurgu']}; background: #121A2C; }}
.fr-kpi-baslik {{ color: {RENK['metin2']}; font-size: 14px; }}
.fr-kpi-deger {{ font-family: {MONO}; font-size: 26px; line-height: 1.15; color: {RENK['metin']};
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.fr-kpi-alt {{ font-size: 13px; color: {RENK['metin2']}; }}
.fr-cubuk {{ height: 6px; border-radius: 3px; background: #1E2430; overflow: hidden; }}
.fr-cubuk > div {{ height: 100%; border-radius: 3px; }}

/* Rozetler */
.fr-rozet {{ display: inline-block; font-size: 12px; line-height: 1.5; padding: 1px 8px; border-radius: 10px;
  border: 1px solid transparent; white-space: nowrap; vertical-align: middle; }}
.fr-rozet.gri {{ border-color: {RENK['kenarlik2']}; color: {RENK['soluk']}; }}
.fr-rozet.mavi {{ background: #1E2A44; color: #8FB0FF; }}
.fr-rozet.yesil {{ background: #12261D; color: {RENK['kar']}; }}
.fr-rozet.kirmizi {{ background: #2A1517; color: {RENK['zarar']}; }}
.fr-rozet.sari {{ background: #2A2111; color: {RENK['uyari']}; }}
.fr-rozet.mor {{ background: #231B3A; color: #B69CFF; }}

/* Sayfa başlığı altındaki açıklama */
.fr-alt-baslik {{ color: {RENK['metin2']}; font-size: 14px; margin-top: -6px; }}

/* Liste satırları (Son satışlar vb.) */
.fr-liste-satir {{ display: flex; justify-content: space-between; align-items: center; gap: 12px;
  padding: 10px 0; border-bottom: 1px solid #1E232D; }}
.fr-liste-satir:last-child {{ border-bottom: 0; }}
.fr-liste-satir .ad {{ font-weight: 500; overflow: hidden; text-overflow: ellipsis; }}
.fr-liste-satir .alt {{ font-size: 12px; color: {RENK['soluk']}; }}

/* Yatay çubuk listesi (kanallara göre kâr, gider kategorileri) */
.fr-yatay {{ display: grid; grid-template-columns: minmax(90px, 140px) 1fr auto; align-items: center;
  gap: 8px 14px; padding-bottom: 8px; }}
.fr-yatay .tutar {{ font-family: {MONO}; text-align: right; }}
.fr-yigin {{ display: flex; height: 12px; border-radius: 4px; overflow: hidden; gap: 2px; }}
.fr-aciklama {{ display: flex; flex-wrap: wrap; gap: 10px 28px; font-size: 13px; color: {RENK['metin2']}; }}
.fr-aciklama .kare {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; }}

/* Boş durum: kesik çizgili koyu kart */
.fr-bos {{ border: 1px dashed {RENK['kenarlik2']}; border-radius: 12px; background: #0E1117; padding: 18px 20px;
  color: {RENK['metin2']}; font-size: 14px; line-height: 1.6; }}
.fr-bos b {{ color: {RENK['metin']}; }}

/* Bilgi notu (kart içindeki küçük kutu) */
.fr-not {{ border: 1px solid {RENK['kenarlik']}; border-radius: 10px; padding: 12px 14px; color: {RENK['metin2']};
  font-size: 13px; line-height: 1.55; }}
.fr-not.yesil {{ border-color: #1E3A2C; background: #0F1D17; color: {RENK['metin']}; }}

/* Tespit satırları (akıllı özet) */
.fr-tespit {{ display: flex; gap: 10px; align-items: baseline; margin: 0 0 12px; line-height: 1.55; }}
.fr-tespit .isaret {{ flex: none; font-size: 12px; }}

/* Kenar çubuğu menüsü: grup başlıkları büyük harf, seçili öğede soldan mavi çizgi */
[data-testid="stNavSectionHeader"] {{ text-transform: uppercase; font-size: 11px !important;
  letter-spacing: .8px; font-weight: 600; color: {RENK['soluk']} !important; }}
[data-testid="stSidebarNavLink"] {{ border-radius: 8px; }}
[data-testid="stSidebarNavLink"][aria-current="page"] {{ box-shadow: inset 2px 0 0 {RENK['vurgu']}; }}
[data-testid="stSidebarNavLink"][aria-current="page"] span {{ color: #fff; font-weight: 600; }}
[data-testid="stSidebarNavLink"]::after {{ margin-left: auto; font-size: 12px; padding: 0 7px; border-radius: 10px;
  background: #1E2A44; color: #8FB0FF; line-height: 1.6; }}
.fr-durum {{ display: flex; align-items: center; gap: 10px; padding: 10px; border-radius: 10px; background: #131722;
  border: 1px solid #1E232D; font-size: 12px; color: {RENK['metin2']}; }}
.fr-nokta {{ width: 8px; height: 8px; border-radius: 4px; flex: none; }}

/* Kart başlığındaki "Tümü →" bağlantıları mavi */
[class*="st-key-kart_"] [data-testid="stPageLink"] p {{ color: #8FB0FF; font-size: 14px; }}
/* İkincil düğmeler kart renginde */
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"],
[data-testid="stPopoverButton"] {{ background: {RENK['kart']}; }}
/* Açılır bölümler (Claude'a sor vb.) kart görünümünde */
[data-testid="stExpander"] details {{ border-color: {RENK['kenarlik']}; background: {RENK['kart']}; }}
/* Açılır pencere */
div[role="dialog"] {{ background: {RENK["kart"]} !important; border: 1px solid {RENK["kenarlik"]}; }}

/* ---- Küçük animasyonlar (kısa ve sakin; "hareketi azalt" ayarı olanlarda kapalı) ---- */
@keyframes fr-yuksel {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes fr-uzat {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
@keyframes fr-nabiz {{ 0%, 100% {{ box-shadow: 0 0 0 0 rgba(61,214,140,.45); }} 50% {{ box-shadow: 0 0 0 5px rgba(61,214,140,0); }} }}

/* KPI kartları sırayla yukarı kayarak belirir; üzerine gelince hafif yükselir */
.fr-kpi {{ animation: fr-yuksel .45s ease-out both; transition: transform .18s ease, border-color .18s ease; }}
.fr-kpi:nth-child(2) {{ animation-delay: .06s; }} .fr-kpi:nth-child(3) {{ animation-delay: .12s; }}
.fr-kpi:nth-child(4) {{ animation-delay: .18s; }} .fr-kpi:nth-child(5) {{ animation-delay: .24s; }}
.fr-kpi:hover {{ transform: translateY(-2px); border-color: {RENK['kenarlik2']}; }}
.fr-kpi.vurgu:hover {{ border-color: {RENK['vurgu']}; }}
/* Çubuklar soldan dolar */
.fr-cubuk > div, .fr-yigin > div {{ transform-origin: left; animation: fr-uzat .7s cubic-bezier(.2,.7,.2,1) both; }}
.fr-liste-satir {{ transition: background .15s ease; }}
.fr-liste-satir:hover {{ background: rgba(255,255,255,.025); }}
/* Düğmeler, menü ve açılır bölümler yumuşak geçer */
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"], [data-testid="stSidebarNavLink"],
[data-testid="stExpander"] details {{ transition: background .15s ease, border-color .15s ease, transform .1s ease; }}
[data-testid="stBaseButton-secondary"]:active, [data-testid="stBaseButton-primary"]:active {{ transform: scale(.97); }}
/* Durum noktası nabız gibi atar */
.fr-durum .fr-nokta {{ animation: fr-nabiz 2.4s ease-in-out infinite; }}
/* Dar ekran (telefon) */
@media (max-width: 640px) {{
  .fr-kpi-grid {{ grid-template-columns: 1fr 1fr; gap: 10px; }}
  .fr-kpi {{ padding: 14px; }} .fr-kpi-deger {{ font-size: 21px; }}
  .fr-yatay {{ grid-template-columns: minmax(70px, 100px) 1fr auto; gap: 6px 10px; font-size: 13px; }}
  .fr-aciklama {{ gap: 8px 18px; }}
  .fr-liste-satir {{ gap: 8px; }}
  [data-testid="stMainBlockContainer"] {{ padding-left: 1rem; padding-right: 1rem; }}
}}
@media (prefers-reduced-motion: reduce) {{ *, *::before, *::after {{ animation: none !important; transition: none !important; }} }}
</style>
"""


def kacis(metin):
    """Kullanıcının yazdığı metni HTML içinde güvenle göstermek için."""
    return escape(str(metin), quote=True)


def inject_css(sayaclar=None, yalnizca_sayaclar=False):
    """Ortak CSS'i sayfaya ekler. `sayaclar`: {url_yolu: sayı} — sol menüde sayfa adının yanındaki rakamlar
    (Streamlit menüsünde sayaç olmadığı için CSS ile, bağlantının adresine göre eklenir)."""
    ek = ""
    for yol, sayi in (sayaclar or {}).items():
        if sayi:
            ek += f'[data-testid="stSidebarNavLink"][href$="/{yol}"]::after {{ content: "{int(sayi)}"; }}\n'
    icerik = ("" if yalnizca_sayaclar else _CSS) + (f"<style>{ek}</style>" if ek else "")
    if icerik:
        st.html(icerik)


def html(icerik):
    """HTML parçasını sayfaya yazar."""
    st.markdown(icerik, unsafe_allow_html=True)


# ---------- Biçim ----------

def _sayi(tutar, basamak):
    return f"{abs(tutar):,.{basamak}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def para(tutar, basamak=0, isaret=False):
    """₺1.234 ; isaret=True ise kâr "+₺184", zarar "−₺12" (gerçek eksi işaretiyle)."""
    if tutar < 0:
        return f"−₺{_sayi(tutar, basamak)}"
    return f"{'+' if isaret and tutar > 0 else ''}₺{_sayi(tutar, basamak)}"


def kar_rengi(tutar):
    return RENK["kar"] if tutar > 0 else RENK["zarar"] if tutar < 0 else RENK["metin2"]


def mono(metin, renk=None):
    stil = f' style="color:{renk}"' if renk else ""
    return f'<span class="fr-mono"{stil}>{metin}</span>'


def kar_metni(tutar, basamak=0):
    """Renkli, işaretli kâr: <span>+₺184</span>"""
    return mono(para(tutar, basamak, isaret=True), kar_rengi(tutar))


# ---------- Parçalar ----------

def badge(metin, tur="gri"):
    """Rozet. tur: gri, mavi, yesil, kirmizi, sari, mor."""
    return f'<span class="fr-rozet {tur}">{kacis(metin)}</span>'


def ilerleme(oran, renk=None):
    oran = max(0.0, min(float(oran), 1.0))
    return (f'<div class="fr-cubuk"><div style="width:{oran * 100:.1f}%;background:{renk or RENK["vurgu"]}">'
            "</div></div>")


def kpi_card(baslik, deger, alt="", deger_rengi=None, alt_rengi=None, cubuk=None, vurgulu=False):
    """Tek KPI kartının HTML'i. `cubuk`: (oran 0–1, renk) ise altta ilerleme çubuğu çizilir."""
    deger_stil = f' style="color:{deger_rengi}"' if deger_rengi else ""
    alt_stil = f' style="color:{alt_rengi}"' if alt_rengi else ""
    parcalar = [f'<div class="fr-kpi-baslik">{kacis(baslik)}</div>',
                f'<div class="fr-kpi-deger"{deger_stil}>{kacis(deger)}</div>']
    if cubuk is not None:
        parcalar.append(ilerleme(*cubuk) if isinstance(cubuk, tuple) else ilerleme(cubuk))
    if alt:
        parcalar.append(f'<div class="fr-kpi-alt"{alt_stil}>{kacis(alt)}</div>')
    return f'<div class="fr-kpi{" vurgu" if vurgulu else ""}">{"".join(parcalar)}</div>'


def kpi_satiri(kartlar):
    """KPI kartlarını yan yana (telefonda alt alta) dizer. kartlar: kpi_card() çıktıları."""
    html(f'<div class="fr-kpi-grid">{"".join(kartlar)}</div>')


def baslik(metin, aciklama=None, rozet=None):
    """Sayfa başlığı + açıklama satırı (isteğe bağlı rozetle)."""
    st.title(metin, anchor=False)
    if aciklama or rozet:
        html(f'<div class="fr-alt-baslik">{aciklama or ""}{" " + rozet if rozet else ""}</div>')


def bos_kart(metin):
    """Boş durum: kesik çizgili koyu kart. `metin` güvenli HTML olmalı (kalın yazı için <b>)."""
    html(f'<div class="fr-bos">{metin}</div>')


def not_kutusu(metin, tur=""):
    html(f'<div class="fr-not {tur}">{metin}</div>')


def liste_satiri(ad, alt, sag):
    """Ad + alt yazı solda, `sag` (HTML) sağda olan satır."""
    return (f'<div class="fr-liste-satir"><div style="min-width:0"><div class="ad">{kacis(ad)}</div>'
            f'<div class="alt">{kacis(alt)}</div></div>{sag}</div>')


def yatay_cubuklar(satirlar):
    """[(etiket, değer)] → etiket | oransal çubuk | tutar. Eksi değerler kırmızı."""
    en_buyuk = max((abs(d) for _, d in satirlar), default=0) or 1
    parcalar = []
    for etiket, deger in satirlar:
        renk = RENK["zarar"] if deger < 0 else RENK["vurgu"]
        oran = max(abs(deger) / en_buyuk, 0.02)
        parcalar.append(f"<div>{kacis(etiket)}</div>{ilerleme(oran, renk)}"
                        f'<div class="tutar" style="color:{RENK["zarar"] if deger < 0 else RENK["metin"]}">'
                        f"{para(deger)}</div>")
    return f'<div class="fr-yatay">{"".join(parcalar)}</div>'


YIGIN_RENKLERI = ["#4C7DFF", "#A78BFA", "#F5A524", "#3DD68C", "#F26D6D", "#5B6475"]


def yigin_cubuk(satirlar, renkler=None):
    """[(etiket, değer)] → tek yatay yığılmış çubuk + altında renkli açıklama."""
    toplam = sum(d for _, d in satirlar) or 1
    renkler = renkler or [YIGIN_RENKLERI[i % len(YIGIN_RENKLERI)] for i in range(len(satirlar))]
    cubuk = "".join(f'<div style="flex:{d / toplam:.4f};background:{r}"></div>' for (_, d), r in zip(satirlar, renkler))
    aciklama = "".join(f'<div><span class="kare" style="background:{r}"></span>{kacis(e)}<br>'
                       f'<span class="fr-mono" style="color:{RENK["metin"]}">{para(d)}</span></div>'
                       for (e, d), r in zip(satirlar, renkler))
    return f'<div class="fr-yigin">{cubuk}</div><div class="fr-aciklama" style="margin-top:12px">{aciklama}</div>'


TESPIT_ISARETI = {"iyi": ("▲", RENK["kar"]), "uyari": ("▼", RENK["zarar"]), "bilgi": ("●", RENK["vurgu"])}


def tespitler_html(tespitler):
    """Akıllı özet maddeleri: iyi ▲ yeşil, uyarı ▼ kırmızı, bilgi ● mavi."""
    satirlar = []
    for tur, metin in tespitler:
        isaret, renk = TESPIT_ISARETI.get(tur, TESPIT_ISARETI["bilgi"])
        satirlar.append(f'<div class="fr-tespit"><span class="isaret" style="color:{renk}">{isaret}</span>'
                        f"<span>{kacis(metin)}</span></div>")
    html("".join(satirlar))


def durum_karti(metin, renk=None):
    """Kenar çubuğunun altındaki küçük durum kartı (yeşil nokta + yazı)."""
    st.sidebar.markdown(f'<div class="fr-durum"><span class="fr-nokta" style="background:{renk or RENK["kar"]}">'
                        f"</span><span>{kacis(metin)}</span></div>", unsafe_allow_html=True)
