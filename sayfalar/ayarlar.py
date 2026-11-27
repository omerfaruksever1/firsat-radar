"""Ayarlar: satış kanalları ve komisyon oranları, varsayılanlar (kargo, aylık hedef), yedekleme.
Görünüm: tasarim/08-ayarlar.html — solda kanal tablosu, sağda varsayılanlar ve yedekleme."""

from datetime import date

import streamlit as st

import styles
import veritabani as db
import yorum
from arayuz.ortak import PARA, kart, mesaji_goster, sayfa_basligi

sayfa_basligi("Ayarlar", "Satış kanalları, komisyon oranları, varsayılanlar ve yedekleme")
mesaji_goster("ayar_mesaj")

sol, sag = st.columns([1.4, 1], gap="small")
with sol, kart("ay_kanallar", height="stretch"):
    kanallar = db.kanallari_getir()
    girilmemis = int((kanallar["komisyon_orani"] == 0).sum())
    ust_sol, ust_sag = st.columns([3, 2])
    ust_sol.subheader("Satış kanalları ve komisyon", anchor=False)
    ust_sol.caption("Satış fiyatının yüzde kaçı kesiliyor? Yeni satışta ve Fiyat Hesapla'da bu oran kullanılır.")
    if girilmemis:
        ust_sag.html(f'<div style="text-align:right">{styles.badge(f"{girilmemis} kanalın oranı girilmemiş", "sari")}'
                     "</div>")
    tablo = st.data_editor(
        kanallar, key="ay_kanal_tablosu", num_rows="dynamic", hide_index=True,
        column_order=["ad", "komisyon_orani"], width="stretch", alt="Satış kanalları tablosu",
        column_config={
            "ad": st.column_config.TextColumn("Kanal", required=True),
            "komisyon_orani": st.column_config.NumberColumn("Komisyon %", min_value=0.0, max_value=100.0,
                                                            step=0.5, format="%.1f", default=0.0),
        },
    )
    alt_sol, alt_sag = st.columns([3, 2], vertical_alignment="center")
    alt_sol.caption("Kanal eklemek için tablonun altındaki boş satıra yaz; silmek için satırı seçip çöp kutusuna "
                    "bas. Adını değiştirdiğin kanalın eski satışları da yeni adla görünür; silmek eski satışları "
                    "silmez. Elden ve kendi sitende oran 0 kalabilir.")
    with alt_sag.container(horizontal=True, horizontal_alignment="right"):
        kaydet = st.button("Kanalları kaydet", type="primary")
    if kaydet:
        adlar = tablo["ad"].fillna("").astype(str).str.strip()
        if tablo.empty:
            st.error("En az bir satış kanalı olmalı.", icon=":material/error:")
        elif (adlar == "").any():
            st.error("Kanal adı boş bırakılamaz.", icon=":material/error:")
        elif adlar.map(yorum.kucuk_harf).duplicated().any():
            st.error("Aynı adla iki kanal olamaz.", icon=":material/error:")
        else:
            db.kanallari_kaydet(tablo.assign(ad=adlar))
            st.session_state.ayar_mesaj = ("ok", "Satış kanalları kaydedildi.")
            st.rerun()

with sag:
    with kart("ay_varsayilan"):
        st.subheader("Varsayılanlar", anchor=False)
        kargo = st.number_input("Varsayılan kargo ücreti ₺ / adet", key="ay_kargo",
                                value=float(db.ayar_getir("varsayilan_kargo", "0")), **PARA)
        st.caption("Yeni satış formunda ve Fiyat Hesapla'da otomatik dolar")
        hedef = st.number_input("Aylık kâr hedefi ₺", key="ay_hedef", value=float(db.ayar_getir("aylik_hedef", "0")),
                                **PARA)
        st.caption("Genel Bakış ve Raporlar'da ilerleme olarak görünür; 0 bırakırsan gösterilmez")
        if st.button("Kaydet", key="ay_varsayilan_kaydet"):
            db.ayar_kaydet("varsayilan_kargo", kargo)
            db.ayar_kaydet("aylik_hedef", hedef)
            st.session_state.ayar_mesaj = ("ok", "Varsayılanlar kaydedildi.")
            st.rerun()

    with kart("ay_yedek"):
        st.subheader("Yedekleme", anchor=False)
        if db.yerel_mi():
            yedek = db.VERITABANI_YOLU.parent / "yedekler" / f"otomatik_{date.today().isoformat()}.db"
            if yedek.exists():
                styles.not_kutusu('<span class="fr-nokta" style="display:inline-block;margin-right:10px;'
                                  f'background:{styles.RENK["kar"]}"></span><b>Bugün otomatik yedek alındı</b><br>'
                                  '<span style="margin-left:18px">Son 14 gün saklanıyor</span>', "yesil")
            else:
                styles.not_kutusu("Bugünün otomatik yedeği henüz alınmadı; uygulama bir sonraki açılışta alır.")
        else:
            styles.not_kutusu("Veriler internet veritabanında; yedeğini veritabanı hizmeti tutar.", "yesil")
        st.caption("İstediğin zaman bir kopya indirip USB bellekte veya Google Drive'da saklayabilirsin.")
        st.download_button("Yedeği indir", data=db.yedek_dosyasi(), type="primary", width="stretch",
                           file_name=f"firsatradar_yedek_{date.today():%Y-%m-%d}.db",
                           mime="application/octet-stream")

    with kart("ay_yapay_zeka"):
        st.subheader("Yapay zeka yorumları", anchor=False)
        st.caption("Şu an ücretsiz yöntemler kullanılıyor: verilerinden otomatik çıkarılan **Akıllı özet** ve "
                   "claude.ai'ye yapıştırılan **Claude'a sor** metinleri. İleride yorumların doğrudan uygulamada "
                   "çıkması istenirse bağlantı anahtarı buraya girilecek.")
