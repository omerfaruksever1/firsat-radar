"""Satış, stok ve gider formları ile açılır pencereler (dialog)."""

from datetime import date

import pandas as pd
import streamlit as st

import veritabani as db
from arayuz.ortak import PARA, secenekler, tl, yuzde

KAYNAK_IPUCU = "Örn. Toptancı A, bir ilan, evdeki eski eşya"


# ---------- Ortak form durumu ----------

def _durum():
    return st.session_state


def form_varsayilanlari(onek):
    return {f"{onek}_urun": "", f"{onek}_pazar": db.kanal_adlari()[0], f"{onek}_adet": 1,
            f"{onek}_alis": 0.0, f"{onek}_satis": 0.0,
            f"{onek}_kargo": float(db.ayar_getir("varsayilan_kargo", "0")),
            f"{onek}_komisyon": 0.0, f"{onek}_tarih": date.today(),
            f"{onek}_durum": db.DURUMLAR[0], f"{onek}_kategori": None,
            f"{onek}_kaynak": None, f"{onek}_notlar": ""}


def yeni_form_hazirla(onek, baslangic=None):
    """Yeni kayıt formunun alanlarına ilk değerlerini verir (`baslangic`: {alan: değer} ile doldurulmuş)."""
    s = _durum()
    ilk_kez = f"{onek}_urun" not in s
    degerler = form_varsayilanlari(onek)
    if baslangic:
        degerler.update({f"{onek}_{alan}": deger for alan, deger in baslangic.items()})
    for anahtar, deger in degerler.items():
        s.setdefault(anahtar, deger)
    if s[f"{onek}_pazar"] not in db.kanal_adlari():  # kanal Ayarlar'dan silinmiş olabilir
        s[f"{onek}_pazar"] = db.kanal_adlari()[0]
    if ilk_kez and baslangic and baslangic.get("satis"):
        komisyonu_hesapla(onek)


def formu_sifirla(onek):
    s = _durum()
    for anahtar in [a for a in s.keys() if str(a).startswith(f"{onek}_")]:
        del s[anahtar]


def komisyonu_hesapla(onek):
    """Kanal veya satış fiyatı değişince komisyonu kanalın oranından hesaplar (oran girilmişse)."""
    s = _durum()
    oran = db.komisyon_orani(s[f"{onek}_pazar"])
    if oran:
        s[f"{onek}_komisyon"] = round(s[f"{onek}_satis"] * oran / 100, 2)


def kar_onizleme(alis, satis, kargo, komisyon, adet):
    if satis <= 0:
        st.caption("Satış fiyatını girince net kâr burada hesaplanır.")
        return
    net_kar, marj = db.kar_hesapla(alis, satis, kargo, komisyon, adet)
    renk = "blue" if net_kar >= 0 else "orange"
    st.markdown(f"Net kâr: :{renk}[**{tl(net_kar)}**]  ·  Kâr marjı: :{renk}[**{yuzde(marj)}**]",
                help="(satış − alış − kargo − komisyon) × adet. Kâr marjı = net kâr ÷ toplam satış tutarı.")


def kaydi_dogrula(kayit):
    if not kayit["urun_adi"].strip():
        return "Lütfen ürün adını yazın."
    if kayit["satis_fiyati"] <= 0:
        return "Satış fiyatı 0'dan büyük olmalı."
    return None


def formdaki_satis(onek):
    s = _durum()
    return {"urun_adi": s[f"{onek}_urun"], "pazar": s[f"{onek}_pazar"],
            "tarih": s.get(f"{onek}_tarih", date.today()), "adet": s[f"{onek}_adet"],
            "alis_fiyati": s[f"{onek}_alis"], "satis_fiyati": s[f"{onek}_satis"],
            "kargo": s[f"{onek}_kargo"], "komisyon": s[f"{onek}_komisyon"],
            "durum": s[f"{onek}_durum"], "kategori": s.get(f"{onek}_kategori"),
            "kaynak": s.get(f"{onek}_kaynak"), "notlar": s.get(f"{onek}_notlar", "")}


def _net_kar_metni(kayit):
    net, _ = db.kar_hesapla(kayit["alis_fiyati"], kayit["satis_fiyati"], kayit["kargo"],
                            kayit["komisyon"], kayit["adet"])
    return tl(net)


# ---------- Satış formu ----------

def satis_formu(onek, kayit=None, en_fazla_adet=None):
    """Tam satış formu. `kayit` verilirse o satış düzenlenir; verilmezse yeni satış (alan değerleri
    oturumda tutulur, kanal/fiyat değişince komisyon otomatik hesaplanır). Girilen değerleri döndürür."""
    k = kayit or {}
    yeni = kayit is None

    def ayar(varsayilan):
        return {} if yeni else {"value": varsayilan}

    def secim(liste, deger, bos_olabilir=False):
        if yeni:
            return {}
        if bos_olabilir and not deger:
            return {"index": None}
        return {"index": liste.index(deger) if deger in liste else 0}

    komisyon_takibi = {"on_change": komisyonu_hesapla, "args": (onek,)} if yeni else {}
    kanallar = secenekler(db.kanal_adlari(), [], k.get("pazar"))
    kategoriler = secenekler(db.KATEGORILER, db.kullanilan_degerler("kategori"), k.get("kategori"))
    kaynaklar = secenekler([], db.kullanilan_degerler("kaynak"), k.get("kaynak"))

    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    urun = c1.text_input("Ürün adı", key=f"{onek}_urun", placeholder="Örn. Laptop standı",
                         **ayar(k.get("urun_adi", "")))
    durum = c2.radio("Durum", db.DURUMLAR, key=f"{onek}_durum", horizontal=True,
                     **secim(db.DURUMLAR, k.get("durum")))

    c1, c2, c3 = st.columns([2, 2, 1])
    pazar = c1.selectbox("Satış kanalı", kanallar, key=f"{onek}_pazar",
                         **secim(kanallar, k.get("pazar")), **komisyon_takibi)
    tarih = c2.date_input("Satış tarihi", key=f"{onek}_tarih", format="DD.MM.YYYY",
                          **ayar(k.get("tarih")))
    adet = c3.number_input("Adet", min_value=1, step=1, key=f"{onek}_adet",
                           **({"max_value": en_fazla_adet} if en_fazla_adet else {}),
                           **ayar(int(k.get("adet", 1))))

    c1, c2 = st.columns(2)
    alis = c1.number_input("Geliş (alış) fiyatı ₺ / adet", key=f"{onek}_alis", **PARA,
                           **ayar(float(k.get("alis_fiyati", 0))))
    satis = c2.number_input("Gidiş (satış) fiyatı ₺ / adet", key=f"{onek}_satis", **PARA,
                            **ayar(float(k.get("satis_fiyati", 0))), **komisyon_takibi)
    c1, c2 = st.columns(2)
    kargo = c1.number_input("Kargo ücreti ₺ / adet", key=f"{onek}_kargo", **PARA,
                            **ayar(float(k.get("kargo", 0))))
    komisyon = c2.number_input("Komisyon ücreti ₺ / adet", key=f"{onek}_komisyon", **PARA,
                               **ayar(float(k.get("komisyon", 0))),
                               help="Kanalın komisyon oranı Ayarlar'da girilmişse otomatik hesaplanır; "
                                    "istersen elle değiştirebilirsin.")

    ek_dolu = bool(k.get("kategori") or k.get("kaynak") or k.get("notlar"))
    with st.expander("Ek bilgiler: kategori, nereden alındı, not", expanded=ek_dolu):
        c1, c2 = st.columns(2)
        kategori = c1.selectbox("Kategori", kategoriler, key=f"{onek}_kategori", accept_new_options=True,
                                placeholder="Seç veya yaz",
                                **secim(kategoriler, k.get("kategori"), bos_olabilir=True))
        kaynak = c2.selectbox("Nereden alındı", kaynaklar, key=f"{onek}_kaynak", accept_new_options=True,
                              placeholder=KAYNAK_IPUCU, **secim(kaynaklar, k.get("kaynak"), bos_olabilir=True))
        notlar = st.text_input("Not", key=f"{onek}_notlar", placeholder="Örn. Kutusu yok, hafif çizik",
                               **ayar(k.get("notlar", "")))

    kar_onizleme(alis, satis, kargo, komisyon, adet)
    return {"urun_adi": urun, "pazar": pazar, "tarih": tarih, "adet": adet,
            "alis_fiyati": alis, "satis_fiyati": satis, "kargo": kargo, "komisyon": komisyon,
            "durum": durum, "kategori": kategori, "kaynak": kaynak, "notlar": notlar}


def hizli_satis_formu(onek):
    """Genel Bakış'taki kısa form (şablon düzeni); tarih bugün olarak kaydedilir."""
    yeni_form_hazirla(onek)
    st.text_input("Ürün", key=f"{onek}_urun", placeholder="Örn. Laptop standı")
    st.radio("Durum", db.DURUMLAR, key=f"{onek}_durum", horizontal=True)
    # Her satır ayrı sütun çifti: telefonda alanlar doğru sırayla alt alta dizilir
    c1, c2 = st.columns(2)
    alis = c1.number_input("Geliş (alış) fiyatı ₺", key=f"{onek}_alis", **PARA)
    satis = c2.number_input("Gidiş (satış) fiyatı ₺", key=f"{onek}_satis", **PARA,
                            on_change=komisyonu_hesapla, args=(onek,))
    c1, c2 = st.columns(2)
    c1.selectbox("Satış kanalı", db.kanal_adlari(), key=f"{onek}_pazar",
                 on_change=komisyonu_hesapla, args=(onek,))
    adet = c2.number_input("Adet", min_value=1, step=1, key=f"{onek}_adet")
    c1, c2 = st.columns(2)
    kargo = c1.number_input("Kargo ₺ / adet", key=f"{onek}_kargo", **PARA)
    komisyon = c2.number_input("Komisyon ₺ / adet", key=f"{onek}_komisyon", **PARA)
    st.selectbox("Nereden alındı", secenekler([], db.kullanilan_degerler("kaynak")),
                 key=f"{onek}_kaynak", accept_new_options=True, placeholder=KAYNAK_IPUCU)
    kar_onizleme(alis, satis, kargo, komisyon, adet)


def hizli_satisi_kaydet(onek):
    """Hızlı formun Kaydet düğmesi (callback)."""
    s = _durum()
    kayit = formdaki_satis(onek)
    hata = kaydi_dogrula(kayit)
    if hata:
        s[f"{onek}_mesaj"] = ("hata", hata)
        return
    db.satis_ekle(kayit)
    s[f"{onek}_mesaj"] = ("ok", f"“{kayit['urun_adi'].strip()}” kaydedildi. Net kâr: {_net_kar_metni(kayit)}")
    for anahtar, deger in form_varsayilanlari(onek).items():
        s[anahtar] = deger


# ---------- Satış pencereleri ----------

@st.dialog("Yeni satış", width="large")
def yeni_satis_penceresi():
    yeni_form_hazirla("yeni")
    kayit = satis_formu("yeni")
    if st.button("Satışı kaydet", icon=":material/save:", type="primary"):
        hata = kaydi_dogrula(kayit)
        if hata:
            st.error(hata, icon=":material/error:")
            return
        db.satis_ekle(kayit)
        st.session_state.satis_mesaj = ("ok", f"“{kayit['urun_adi'].strip()}” kaydedildi. "
                                              f"Net kâr: {_net_kar_metni(kayit)}")
        formu_sifirla("yeni")
        st.rerun()


def _satis_kaydi(kayit_id):
    df = db.satislari_getir()
    r = df[df["id"] == kayit_id].iloc[0]
    return {"urun_adi": r.urun_adi, "pazar": r.pazar, "tarih": r.tarih.date(), "adet": int(r.adet),
            "alis_fiyati": r.alis_fiyati, "satis_fiyati": r.satis_fiyati, "kargo": r.kargo,
            "komisyon": r.komisyon, "durum": r.durum, "kategori": r.kategori, "kaynak": r.kaynak,
            "notlar": r.notlar, "stoktan": pd.notna(r.stok_id)}


@st.dialog("Satışı düzenle", width="large")
def satis_duzenle_penceresi(kayit_id):
    mevcut = _satis_kaydi(kayit_id)
    if mevcut["stoktan"]:
        st.caption(":material/inventory_2: Bu satış Elimdekiler'den yapıldı; adedi değişirse stoktaki kalan "
                   "da düzeltilir, silinirse ürün Elimdekiler'e geri döner.")
    kayit = satis_formu(f"duzenle_{kayit_id}", mevcut)
    onay = f"sil_onay_{kayit_id}"
    if st.session_state.get(onay):
        st.warning(f"**{mevcut['urun_adi']}** satışını silmek istediğine emin misin? Bu işlem geri alınamaz.",
                   icon=":material/warning:")
        with st.container(horizontal=True):
            if st.button("Evet, sil", type="primary"):
                db.satis_sil(kayit_id)
                st.session_state.pop(onay, None)
                st.session_state.satis_mesaj = ("ok", "Kayıt silindi.")
                st.rerun()
            if st.button("Vazgeç"):
                st.session_state.pop(onay, None)
                st.rerun(scope="fragment")
        return
    with st.container(horizontal=True):
        if st.button("Değişiklikleri kaydet", icon=":material/save:", type="primary"):
            hata = kaydi_dogrula(kayit)
            if hata:
                st.error(hata, icon=":material/error:")
                return
            try:
                db.satis_guncelle(kayit_id, kayit)
            except db.StokYetersiz as e:
                st.error(str(e), icon=":material/error:")
                return
            st.session_state.satis_mesaj = ("ok", f"No {kayit_id} güncellendi.")
            st.rerun()
        if st.button("Sil", icon=":material/delete:"):
            st.session_state[onay] = True
            st.rerun(scope="fragment")


# ---------- Elimdekiler (stok) ----------

def stok_formu(onek, kayit=None):
    """Elimdekiler'e ürün ekleme/düzenleme formu. Girilen değerleri döndürür."""
    k = kayit or {}
    kategoriler = secenekler(db.KATEGORILER, db.kullanilan_degerler("kategori"), k.get("kategori"))
    kaynaklar = secenekler([], db.kullanilan_degerler("kaynak"), k.get("kaynak"))

    def secim(liste, deger):
        return {"index": liste.index(deger)} if deger in liste else {"index": None}

    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    urun = c1.text_input("Ürün adı", key=f"{onek}_urun", value=k.get("urun_adi", ""),
                         placeholder="Örn. Deri çanta")
    durum = c2.radio("Durum", db.DURUMLAR, key=f"{onek}_durum", horizontal=True,
                     index=db.DURUMLAR.index(k.get("durum", db.DURUMLAR[0])))
    c1, c2, c3 = st.columns([2, 2, 1])
    alis = c1.number_input("Alış fiyatı ₺ / adet", key=f"{onek}_alis", value=float(k.get("alis_fiyati", 0)), **PARA)
    tarih = c2.date_input("Alış tarihi", key=f"{onek}_tarih", value=k.get("alis_tarihi", date.today()),
                          format="DD.MM.YYYY")
    adet = c3.number_input("Elde kalan adet" if kayit else "Adet", key=f"{onek}_adet", min_value=0 if kayit else 1,
                           step=1, value=int(k.get("kalan", 1)))
    c1, c2 = st.columns(2)
    kaynak = c1.selectbox("Nereden alındı", kaynaklar, key=f"{onek}_kaynak", accept_new_options=True,
                          placeholder=KAYNAK_IPUCU, **secim(kaynaklar, k.get("kaynak")))
    kategori = c2.selectbox("Kategori", kategoriler, key=f"{onek}_kategori", accept_new_options=True,
                            placeholder="Seç veya yaz", **secim(kategoriler, k.get("kategori")))
    c1, c2 = st.columns(2)
    hedef = c1.number_input("Hedef satış fiyatı ₺ (isteğe bağlı)", key=f"{onek}_hedef",
                            value=float(k.get("hedef_fiyat", 0)), **PARA,
                            help="Kaça satmayı düşünüyorsan yaz; satarken fiyat kutusu bununla dolu gelir. "
                                 "Fiyat Hesapla sayfası uygun fiyatı bulmana yardım eder.")
    notlar = c2.text_input("Not", key=f"{onek}_notlar", value=k.get("notlar", ""),
                           placeholder="Örn. Kutusu yok, hafif çizik")
    return {"urun_adi": urun, "durum": durum, "alis_fiyati": alis, "alis_tarihi": tarih, "adet": adet,
            "kalan": adet, "kaynak": kaynak, "kategori": kategori, "hedef_fiyat": hedef, "notlar": notlar}


def _stok_dogrula(kayit):
    if not kayit["urun_adi"].strip():
        return "Lütfen ürün adını yazın."
    if kayit["alis_fiyati"] < 0:
        return "Alış fiyatı eksi olamaz."
    return None


@st.dialog("Elimdekiler'e ürün ekle", width="large")
def stok_ekle_penceresi():
    st.caption("Aldığın ama henüz satmadığın ürünü kaydet. Satınca Elimdekiler sayfasından tek tıkla satışa "
               "dönüştürebilirsin.")
    kayit = stok_formu("stok_yeni")
    if st.button("Ekle", icon=":material/add:", type="primary"):
        hata = _stok_dogrula(kayit)
        if hata:
            st.error(hata, icon=":material/error:")
            return
        db.stok_ekle(kayit)
        st.session_state.stok_mesaj = ("ok", f"“{kayit['urun_adi'].strip()}” Elimdekiler'e eklendi.")
        st.rerun()


def _stok_kaydi(stok_id):
    df = db.stoklari_getir(sadece_eldekiler=False)
    r = df[df["id"] == stok_id].iloc[0]
    return {"urun_adi": r.urun_adi, "durum": r.durum, "kategori": r.kategori, "kaynak": r.kaynak,
            "alis_fiyati": r.alis_fiyati, "alis_tarihi": r.alis_tarihi.date(), "kalan": int(r.kalan),
            "adet": int(r.adet), "hedef_fiyat": r.hedef_fiyat, "notlar": r.notlar}


@st.dialog("Ürünü düzenle", width="large")
def stok_duzenle_penceresi(stok_id):
    mevcut = _stok_kaydi(stok_id)
    kayit = stok_formu(f"stok_duzenle_{stok_id}", mevcut)
    onay = f"stok_sil_onay_{stok_id}"
    if st.session_state.get(onay):
        st.warning(f"**{mevcut['urun_adi']}** Elimdekiler'den silinsin mi? Bu üründen yapılmış satışlar "
                   "silinmez.", icon=":material/warning:")
        with st.container(horizontal=True):
            if st.button("Evet, sil", type="primary"):
                db.stok_sil(stok_id)
                st.session_state.pop(onay, None)
                st.session_state.stok_mesaj = ("ok", "Ürün Elimdekiler'den silindi.")
                st.rerun()
            if st.button("Vazgeç"):
                st.session_state.pop(onay, None)
                st.rerun(scope="fragment")
        return
    with st.container(horizontal=True):
        if st.button("Değişiklikleri kaydet", icon=":material/save:", type="primary"):
            hata = _stok_dogrula(kayit)
            if hata:
                st.error(hata, icon=":material/error:")
                return
            db.stok_guncelle(stok_id, kayit)
            st.session_state.stok_mesaj = ("ok", f"“{kayit['urun_adi'].strip()}” güncellendi.")
            st.rerun()
        if st.button("Sil", icon=":material/delete:"):
            st.session_state[onay] = True
            st.rerun(scope="fragment")


@st.dialog("Ürünü sat", width="large")
def stoktan_sat_penceresi(stok_id):
    stok = _stok_kaydi(stok_id)
    onek = f"stok_sat_{stok_id}"
    st.caption(f"Elinde {stok['kalan']} adet var. Satış kaydedilince Elimdekiler'deki adet düşer.")
    yeni_form_hazirla(onek, {"urun": stok["urun_adi"], "durum": stok["durum"], "alis": float(stok["alis_fiyati"]),
                             "satis": float(stok["hedef_fiyat"]), "kategori": stok["kategori"] or None,
                             "kaynak": stok["kaynak"] or None, "notlar": stok["notlar"]})
    kayit = satis_formu(onek, en_fazla_adet=stok["kalan"])
    if st.button("Satışı kaydet", icon=":material/sell:", type="primary"):
        hata = kaydi_dogrula(kayit)
        if hata:
            st.error(hata, icon=":material/error:")
            return
        try:
            db.stoktan_sat(stok_id, kayit)
        except db.StokYetersiz as e:
            st.error(str(e), icon=":material/error:")
            return
        st.session_state.stok_mesaj = ("ok", f"“{kayit['urun_adi'].strip()}” satıldı. "
                                             f"Net kâr: {_net_kar_metni(kayit)}")
        formu_sifirla(onek)
        st.rerun()


# ---------- Ek giderler ----------

@st.dialog("Gider ekle")
def gider_ekle_penceresi():
    st.caption("Belirli bir ürüne ait olmayan masraflar: ambalaj malzemesi, ilan öne çıkarma, mağaza aboneliği…")
    tarih = st.date_input("Tarih", value=date.today(), format="DD.MM.YYYY", key="gider_tarih")
    kategori = st.selectbox("Kategori", db.gider_kategorileri(), key="gider_kategori", accept_new_options=True)
    aciklama = st.text_input("Açıklama (isteğe bağlı)", key="gider_aciklama", placeholder="Örn. 100'lü kargo poşeti")
    tutar = st.number_input("Tutar ₺", key="gider_tutar", **PARA)
    if st.button("Kaydet", icon=":material/save:", type="primary"):
        if tutar <= 0:
            st.error("Tutar 0'dan büyük olmalı.", icon=":material/error:")
            return
        db.gider_ekle({"tarih": tarih, "kategori": kategori, "aciklama": aciklama, "tutar": tutar})
        formu_sifirla("gider")
        st.session_state.gider_mesaj = ("ok", f"{tl(tutar)} gider kaydedildi.")
        st.rerun()
