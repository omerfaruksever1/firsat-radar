"""Ayarlar: satış kanalları ve komisyon oranları, varsayılanlar (kargo, aylık hedef), yedekleme."""

from datetime import date

import streamlit as st

import veritabani as db
import yorum
from arayuz.ortak import PARA, kart, mesaji_goster, sayfa_basligi

sayfa_basligi("Ayarlar", "Satış kanalları, komisyon oranları, varsayılanlar ve yedekleme.")
mesaji_goster("ayar_mesaj")

with kart("ay_kanallar"):
    st.subheader("Satış Kanalları ve Komisyon Oranları", anchor=False)
    st.caption("Komisyon oranı, satış fiyatının yüzde kaçının kesildiğidir. Oranı girdiğin kanalda yeni satış "
               "eklerken komisyon otomatik hesaplanır; Fiyat Hesapla sayfası da bu oranları kullanır. Pazarların "
               "oranları kategoriye göre değişebilir; kendi hesabındaki oranı gir.")
    tablo = st.data_editor(
        db.kanallari_getir(), key="ay_kanal_tablosu", num_rows="dynamic", hide_index=True,
        column_order=["ad", "komisyon_orani"], width="stretch", alt="Satış kanalları tablosu",
        column_config={
            "ad": st.column_config.TextColumn("Kanal adı", required=True),
            "komisyon_orani": st.column_config.NumberColumn("Komisyon oranı (%)", min_value=0.0, max_value=100.0,
                                                            step=0.5, format="%.1f", default=0.0),
        },
    )
    if st.button("Kanalları kaydet", icon=":material/save:", type="primary"):
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
    st.caption("Satır eklemek için tablonun altındaki boş satıra yaz; silmek için satırı seçip çöp kutusuna bas. "
               "Bir kanalın adını değiştirirsen eski satışları da yeni adla görünür. Bir kanalı silmek eski "
               "satışları silmez.")

sol, sag = st.columns(2)
with sol, kart("ay_varsayilan", height="stretch"):
    st.subheader("Varsayılanlar", anchor=False)
    kargo = st.number_input("Varsayılan kargo ücreti ₺ / adet", key="ay_kargo",
                            value=float(db.ayar_getir("varsayilan_kargo", "0")), **PARA,
                            help="Yeni satış ve fiyat hesaplama formlarında hazır gelir.")
    hedef = st.number_input("Aylık kâr hedefi ₺", key="ay_hedef", value=float(db.ayar_getir("aylik_hedef", "0")),
                            **PARA, help="Genel Bakış'ta bu ay hedefin ne kadarına ulaştığın gösterilir. "
                                         "0 bırakırsan hedef gösterilmez.")
    if st.button("Kaydet", icon=":material/save:", key="ay_varsayilan_kaydet"):
        db.ayar_kaydet("varsayilan_kargo", kargo)
        db.ayar_kaydet("aylik_hedef", hedef)
        st.session_state.ayar_mesaj = ("ok", "Varsayılanlar kaydedildi.")
        st.rerun()

with sag, kart("ay_yedek", height="stretch"):
    st.subheader("Yedekleme", anchor=False)
    st.caption("Uygulama her gün ilk açılışta `yedekler` klasörüne otomatik yedek alır (son 14 gün saklanır). "
               "Ayrıca istediğin zaman bir kopya indirip USB bellekte veya Google Drive'da saklayabilirsin.")
    st.download_button("Yedeği indir", icon=":material/download:", data=db.yedek_dosyasi(),
                       file_name=f"firsatradar_yedek_{date.today():%Y-%m-%d}.db", mime="application/octet-stream")

with kart("ay_yapay_zeka"):
    st.subheader("Yapay Zeka Yorumları", anchor=False)
    st.markdown(
        "Şu an ücretsiz yöntemler kullanılıyor:\n"
        "- **Akıllı özet:** Raporlar ve Elimdekiler sayfalarında, verilerinden otomatik çıkarılan tespitler.\n"
        "- **Claude'a sor:** Verilerin ve hazır bir soru kopyalanır; claude.ai'ye yapıştırınca Claude internette "
        "fiyat araştırması da yaparak yorumlar.\n\n"
        "İleride yorumların doğrudan uygulamada çıkması istenirse, bağlantı anahtarı buraya girilecek.")
