"""İnternette yayınlanan site için tek şifreli giriş ekranı. Bilgisayarda (şifre ayarlı değilse) sorulmaz.
Görünüm: tasarim/00-giris.html — solda tanıtım paneli, sağda şifre formu."""

import hmac
import time

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

import styles

MAKS_DENEME, KILIT_SANIYE = 5, 30

_GIRIS_CSS = f"""
<style>
.st-key-giris_sol {{
  background: {styles.RENK['yan_menu']}; border: 1px solid #1E232D; border-radius: 16px;
  padding: 48px 56px; min-height: 78vh; justify-content: space-between;
}}
.st-key-giris_sag {{ padding: 0 8px; max-width: 420px; margin: 0 auto; }}
.fr-giris-logo {{ font-size: 22px; font-weight: 700; letter-spacing: -0.3px; }}
.fr-giris-logo span {{ color: {styles.RENK['vurgu']}; }}
.fr-giris-h1 {{ margin: 0; font-size: 44px; line-height: 1.1; font-weight: 700; letter-spacing: -1px; }}
.fr-giris-p {{ margin: 0; font-size: 17px; line-height: 1.6; color: #9AA3B2; max-width: 520px; }}
.fr-giris-ornek {{ display: flex; flex-direction: column; gap: 12px; padding: 20px; max-width: 520px;
  border: 1px solid #232937; border-radius: 14px; background: #131722; }}
.fr-giris-h2 {{ margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px; color: {styles.RENK['metin']}; }}
.fr-giris-h1 {{ color: {styles.RENK['metin']}; }}
.st-key-giris_sag [data-testid="stTextInputRootElement"] {{ height: 50px; border-radius: 10px; background: {styles.RENK['kart']}; }}
.st-key-giris_sag input {{ font-size: 16px; }}
.st-key-giris_sag button[kind="primaryFormSubmit"], .st-key-giris_sag [data-testid="stBaseButton-primaryFormSubmit"] {{
  min-height: 50px; border-radius: 10px; font-size: 16px; font-weight: 600; }}
.st-key-giris_sag button p {{ font-size: 16px; font-weight: 600; }}
.st-key-giris_sag label p {{ font-size: 14px; font-weight: 500; color: #C9CFDA; }}
@media (max-width: 640px) {{
  .st-key-giris_sol {{ min-height: 0; padding: 24px; }}
  .fr-giris-h1 {{ font-size: 30px; }}
  .fr-giris-ornek, .fr-giris-alt {{ display: none !important; }}
}}
</style>
"""


def gizli_ayar(anahtar):
    """Sitede Streamlit "secrets" ayarındaki değer; bilgisayarda (ayar dosyası yoksa) None."""
    try:
        return st.secrets.get(anahtar)
    except StreamlitSecretNotFoundError:
        return None


def _tanitim_paneli():
    with st.container(key="giris_sol", gap="large"):
        styles.html('<div class="fr-giris-logo">Fırsat<span>Radar</span></div>')
        styles.html(
            '<div style="display:flex;flex-direction:column;gap:28px">'
            '<div class="fr-giris-h1">Al, sat, kârını<br>tek ekranda gör.</div>'
            '<div class="fr-giris-p">Fırsat takibi, elindeki stok ve her satıştan kalan satış kârı — komisyon ve kargo '
            "düşülmüş hâliyle.</div>"
            '<div class="fr-giris-ornek">'
            '<div style="display:flex;justify-content:space-between;font-size:13px;color:#8C95A5">'
            f'<span>Son satış · Trendyol</span>{styles.mono("örnek")}</div>'
            '<div style="display:flex;justify-content:space-between;align-items:baseline">'
            '<span style="font-size:16px;font-weight:600">Laptop standı ×2</span>'
            f'<span class="fr-mono" style="font-size:20px;color:{styles.RENK["kar"]}">+₺184,50</span></div>'
            f'{styles.ilerleme(0.62, styles.RENK["kar"])}'
            '<div style="font-size:13px;color:#8C95A5">Kâr marjı %22,4</div>'
            "</div></div>")
        styles.html(f'<div class="fr-giris-alt" style="font-size:13px;color:{styles.RENK["soluk"]}">'
                    "Kişisel alım-satım paneli</div>")


def sifre_kontrolu(sifre):
    """Doğru şifre girilene kadar giriş ekranını gösterir ve sayfanın geri kalanını durdurur."""
    if st.session_state.get("giris_yapildi"):
        return
    st.html(_GIRIS_CSS)
    sol, sag = st.columns([1.6, 1], vertical_alignment="center", gap="large")
    with sol:
        _tanitim_paneli()
    with sag, st.container(key="giris_sag", gap="medium"):
        styles.html('<div class="fr-giris-h2">Tekrar hoş geldin</div>'
                    '<div style="margin:8px 0 6px;font-size:15px;color:#9AA3B2">Devam etmek için site şifreni gir.</div>')
        with st.form("giris_formu", border=False):
            girilen = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş yap", type="primary", width="stretch"):
                kalan = st.session_state.get("giris_kilit", 0) - time.time()
                if kalan > 0:
                    st.error(f"Çok fazla yanlış deneme. {int(kalan) + 1} saniye sonra tekrar dene.",
                             icon=":material/lock_clock:")
                elif hmac.compare_digest(girilen.encode(), str(sifre).encode()):
                    st.session_state.giris_yapildi = True
                    st.session_state.pop("giris_hata", None)
                    st.rerun()
                else:
                    hata = st.session_state.get("giris_hata", 0) + 1
                    st.session_state.giris_hata = hata
                    if hata >= MAKS_DENEME:  # her 5 yanlışta 30 saniye bekletilir
                        st.session_state.giris_kilit = time.time() + KILIT_SANIYE
                        st.session_state.giris_hata = 0
                    st.error("Şifre yanlış.", icon=":material/error:")
        styles.html(f'<div style="display:flex;align-items:center;gap:8px;font-size:13px;color:{styles.RENK["soluk"]}">'
                    '<span>🔒</span>Bağlantı şifreli · şifre yalnızca bu oturum için hatırlanır</div>')
    st.stop()
