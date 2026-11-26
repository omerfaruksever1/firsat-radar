"""İnternette yayınlanan site için tek şifreli giriş ekranı. Bilgisayarda (şifre ayarlı değilse) sorulmaz."""

import hmac

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


def gizli_ayar(anahtar):
    """Sitede Streamlit "secrets" ayarındaki değer; bilgisayarda (ayar dosyası yoksa) None."""
    try:
        return st.secrets.get(anahtar)
    except StreamlitSecretNotFoundError:
        return None


def sifre_kontrolu(sifre):
    """Doğru şifre girilene kadar giriş ekranını gösterir ve sayfanın geri kalanını durdurur."""
    if st.session_state.get("giris_yapildi"):
        return
    _, orta, _ = st.columns([1, 2, 1])
    with orta, st.container(border=True, key="kart_giris"):
        st.title("FırsatRadar", anchor=False)
        st.caption("Devam etmek için site şifresini gir.")
        with st.form("giris_formu", border=False):
            girilen = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş", type="primary", width="stretch"):
                if hmac.compare_digest(girilen.encode(), str(sifre).encode()):
                    st.session_state.giris_yapildi = True
                    st.rerun()
                st.error("Şifre yanlış.", icon=":material/error:")
    st.stop()
