"""Yardım: uygulamanın sade Türkçe kullanım kılavuzu. Görünüm: tasarim/09-yardim.html — solda bölüm menüsü,
sağda seçilen bölüm, sağ üstte arama."""

import streamlit as st

import styles
import veritabani as db
import yorum
from arayuz.ortak import kart, sag_butonlar, sayfa_basligi

GUNLUK = [
    ("Ürün aldın, henüz satmadın", "Elimdekiler'de sağdaki **Ürün ekle** formuyla kaydet. Satınca seçip **Sat** de; "
                                   "alış bilgileri hazır gelir, elindeki adet kendiliğinden düşer."),
    ("Doğrudan satış yaptın", "Genel Bakış'taki **+ Satış ekle** ya da **Satışlarım → Yeni satış**."),
    ("Fiyatlar adet başına", "Fiyatı, kargoyu ve komisyonu 1 adet için yaz; uygulama adetle çarpar. Komisyon, "
                             "Ayarlar'daki orana göre kendiliğinden yazılır."),
    ("Ürüne ait olmayan masraf", "Ambalaj, ilan ücreti gibi masrafları **Giderler**'e yaz; gerçek kâr bunlar "
                                 "düşülerek hesaplanır."),
    ("Yanlış kayıt", "**Satışlarım**'da satıra tıkla, sonra **Düzenle / sil**."),
    ("Gözüne bir ürün kestirdin", "**Fırsat Takibi → Fırsat ekle**; her kanalda ne kazanacağını hesaplar."),
]

BOLUMLER = {
    "Fırsat Takibi": (
        "1. Bir ilanda, toptancıda ya da mağaza indiriminde gözüne bir ürün kestirdiğinde **Fırsat Takibi → Fırsat "
        "ekle** ile kaydet: alış fiyatı, varsa ilan linki ve kaça satabileceğini düşündüğün fiyat.\n"
        "2. Satış fiyatını bilmiyorsan ürünü seçip **Claude'a sor** metnini claude.ai'ye yapıştır; internetten "
        "güncel fiyatları araştırır (ücretsiz). Bulduğun fiyatı **Düzenle**'den gir.\n"
        "3. Uygulama her kanalda komisyon ve kargo düşülmüş satış kârını hesaplar ve ürünleri **Güçlü fırsat** "
        "(marj ≥ %25), **Değerlendirilebilir**, **Zayıf** ya da **Zararına** diye işaretler.\n"
        "4. Ürünü aldığında **Satın aldım** de; Elimdekiler'e geçer. Sattığında Genel Bakış'ta tahmin ettiğin "
        "fiyatın ne kadar tuttuğu (**tahmin isabeti**) görünür.\n\n"
        "Uygulama siteleri kendisi taramaz: Sahibinden, Trendyol gibi siteler otomatik taramayı engelliyor ve "
        "kurallarıyla yasaklıyor. Bu yüzden ürünleri sen eklersin, hesabı uygulama yapar."),
    "Terimler": (
        "- **Satış kârı** = satış − alış − komisyon − kargo (adet başına, sonra adetle çarpılır).\n"
        "- **Gerçek kâr** = satış kârı − giderler. Giderler sayfasına yazdığın ambalaj, ilan ücreti gibi masraflar "
        "burada düşülür.\n"
        "- **Kâr marjı** = kârın satış tutarına oranı. Hangi kârdan hesaplandığı her yerde yanında yazar "
        "(ör. “Satış kârı ÷ ciro”)."),
    "Kaça satmalıyım?": (
        "**Fiyat Hesapla** sayfasına alış fiyatını ve istediğin kârı (yüzde ya da tutar olarak) gir. Her satış "
        "kanalında komisyon ve kargo düşüldükten sonra bu kârı bırakan fiyatı gösterir. %15 – %30 düğmeleriyle "
        "hızlı seçebilirsin. Elindeki bir fiyatla her kanalda ne kazanacağını da hesaplayabilirsin."),
    "Raporlar ve yorumlar": (
        "- **Raporlar** sayfasında sağ üstten dönem seç (Bu ay, Geçen ay, Son 30 gün…). Her dönem, bir önceki "
        "benzer dönemle karşılaştırılır; ▲ artış, ▼ azalış demektir.\n"
        "- **Akıllı özet** verilerine bakıp önemli noktaları yazar (artış/azalış, zararlı satışlar, en kârlı "
        "kanal, giderler…). Ücretsizdir.\n"
        "- **Ürün yorumu**na geçip bir ürün seçerek o ürünün tüm satışlarının değerlendirmesini görürsün.\n"
        "- **Claude'a sor** kartındaki metni kopyalayıp claude.ai'ye yapıştırırsan Claude internette benzer "
        "ilanlara bakarak daha ayrıntılı yorum yapar. Bunu yaptığında satış bilgilerin claude.ai'ye gönderilmiş olur."),
    "Veriler güvende mi?": (
        "- Bilgisayardaki uygulamada tüm kayıtlar `firsat_radar.db` dosyasında durur. Bu dosyayı silme.\n"
        "- Uygulama her gün ilk açıldığında `yedekler` klasörüne otomatik yedek alır ve son 14 günü saklar.\n"
        "- İnternetteki sitede kayıtlar internet veritabanında durur.\n"
        "- **Ayarlar → Yedeği indir** ile istediğin zaman bir kopya alıp USB bellekte veya Google Drive'da "
        "saklayabilirsin. Satış listesi için **Satışlarım → Excel'e aktar**."),
    "Açmak ve kapatmak": (
        "- Bilgisayarda açmak için `firsat-radar` klasöründeki **baslat.bat** dosyasına çift tıkla. Tarayıcıda "
        "açılmazsa adres çubuğuna `localhost:8501` yaz.\n"
        "- Açılan siyah pencere uygulamayı çalıştırır; küçültebilirsin ama kapatırsan uygulama da kapanır."),
}
SIRA = ["İlk kurulum", "Günlük kullanım", *BOLUMLER]


def ilk_kurulum():
    kanallar = db.kanallari_getir()
    adimlar = [
        ((kanallar["komisyon_orani"] > 0).any(),
         "**Ayarlar**'da her kanalın komisyon oranını gir (pazar %15 kesiyorsa 15 yaz). Elden ve kendi sitende 0 "
         "kalsın."),
        (float(db.ayar_getir("varsayilan_kargo", "0")) > 0,
         "Genelde aynı kargo ücretini ödüyorsan **varsayılan kargo ücretini**, istersen **aylık kâr hedefini** gir."),
        (db.kanal_adlari() != db.VARSAYILAN_KANALLAR,
         "Kullanmadığın kanalları silebilir, eksik olanları ekleyebilirsin."),
    ]
    tamam = sum(1 for bitti, _ in adimlar if bitti)
    ust_sol, ust_sag = st.columns([3, 2], vertical_alignment="center")
    ust_sol.html(f'<span style="font-size:18px;font-weight:600">İlk kurulum</span>'
                 f'<span style="color:{styles.RENK["soluk"]}"> · bir kez</span>')
    ust_sag.html(f'<div style="text-align:right;font-size:12px;color:{styles.RENK["metin2"]}">'
                 f"{tamam} / {len(adimlar)} tamamlandı</div>")
    for i, (bitti, metin) in enumerate(adimlar, 1):
        isaret = (f'<span style="display:inline-flex;width:26px;height:26px;border-radius:13px;flex:none;'
                  f'align-items:center;justify-content:center;font-size:13px;'
                  + (f'background:#12261D;color:{styles.RENK["kar"]}">✓' if bitti else
                     f'border:1px solid {styles.RENK["kenarlik2"]};color:{styles.RENK["metin2"]}">{i}') + "</span>")
        parcalar = styles.kacis(metin).split("**")
        guvenli = "".join(f"<b>{p}</b>" if j % 2 else p for j, p in enumerate(parcalar))
        styles.html(f'<div style="display:flex;gap:12px;align-items:center;margin:4px 0">{isaret}<span>{guvenli}</span>'
                    "</div>")
    st.page_link("sayfalar/ayarlar.py", label="Ayarlar'a git →")


def gunluk_kullanim():
    st.subheader("Günlük kullanım", anchor=False)
    kutular = []
    for baslik, metin in GUNLUK:
        parcalar = styles.kacis(metin).split("**")
        guvenli = "".join(f'<b style="color:{styles.RENK["metin"]}">{p}</b>' if j % 2 else p
                          for j, p in enumerate(parcalar))
        kutular.append(f'<div style="padding:14px;border:1px solid {styles.RENK["kenarlik"]};border-radius:10px;'
                       f'background:#0E1117"><div style="font-weight:600;margin-bottom:6px">{styles.kacis(baslik)}'
                       f'</div><div style="color:{styles.RENK["metin2"]};line-height:1.55">{guvenli}</div></div>')
    styles.html('<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;'
                f'margin-bottom:6px">{"".join(kutular)}</div>')


def bolum_goster(ad):
    with kart(f"yr_{SIRA.index(ad)}"):
        if ad == "İlk kurulum":
            ilk_kurulum()
        elif ad == "Günlük kullanım":
            gunluk_kullanim()
        else:
            st.subheader(ad, anchor=False)
            st.markdown(BOLUMLER[ad])


def bolum_metni(ad):
    if ad == "İlk kurulum":
        return "ilk kurulum ayarlar komisyon oranı kargo hedef kanal"
    if ad == "Günlük kullanım":
        return " ".join(f"{b} {m}" for b, m in GUNLUK)
    return f"{ad} {BOLUMLER[ad]}"


sag = sayfa_basligi("Yardım", "FırsatRadar'ı nasıl kullanırsın?")
with sag_butonlar(sag):
    arama = st.text_input("Yardımda ara", placeholder="Yardımda ara…", key="yr_ara", label_visibility="collapsed")

st.session_state.setdefault("yr_bolum", SIRA[0])
menu, icerik = st.columns([1, 3.3], gap="medium")
with menu:
    secili = st.session_state.yr_bolum
    st.html("<style>[class*='st-key-yr_nav_'] button { justify-content: flex-start; border: 0; "
            "background: transparent; min-height: 36px; padding: 0 12px; } "
            "[class*='st-key-yr_nav_'] button > div { justify-content: flex-start; width: 100%; } "
            "[class*='st-key-yr_nav_'] button p { color: #AEB6C4; font-size: 14px; } "
            f".st-key-yr_nav_{SIRA.index(secili)} button {{ background: {styles.RENK['aktif']}; "
            f"box-shadow: inset 2px 0 0 {styles.RENK['vurgu']}; }} "
            f".st-key-yr_nav_{SIRA.index(secili)} button p {{ color: #fff; font-weight: 600; }}</style>")
    with st.container(gap=None):
        for i, ad in enumerate(SIRA):
            st.button(ad, key=f"yr_nav_{i}", width="stretch", on_click=st.session_state.__setitem__,
                      args=("yr_bolum", ad))

with icerik:
    if arama.strip():
        aranan = yorum.kucuk_harf(arama.strip())
        bulunan = [ad for ad in SIRA if aranan in yorum.kucuk_harf(bolum_metni(ad))]
        if not bulunan:
            styles.bos_kart(f"“{styles.kacis(arama)}” için sonuç yok. Başka bir kelime dene.")
        for ad in bulunan:
            bolum_goster(ad)
    else:
        bolum_goster(secili)
        if secili == "İlk kurulum":
            bolum_goster("Günlük kullanım")
    with kart("yr_dosya"):
        if db.yerel_mi():
            styles.html(f'<code>firsat_radar.db</code> &nbsp; Tüm kayıtlar bu dosyada durur; her gün otomatik '
                        "yedeklenir. Silme.")
        else:
            styles.html("Tüm kayıtlar internet veritabanında durur. Ara sıra <b>Ayarlar → Yedeği indir</b> ile "
                        "kopya al.")
