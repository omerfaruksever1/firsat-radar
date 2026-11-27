"""Satış, stok ve gider formları ile açılır pencereler (dialog)."""

from datetime import date

import pandas as pd
import streamlit as st

import fiyat
import styles
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
        st.caption("Satış fiyatını girince satış kârı burada hesaplanır.")
        return
    net_kar, marj = db.kar_hesapla(alis, satis, kargo, komisyon, adet)
    renk = "blue" if net_kar >= 0 else "orange"
    st.markdown(f"Satış kârı: :{renk}[**{tl(net_kar)}**]  ·  Kâr marjı: :{renk}[**{yuzde(marj)}**]",
                help="(satış − alış − kargo − komisyon) × adet. Kâr marjı = satış kârı ÷ toplam satış tutarı.")


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
                                              f"Satış kârı: {_net_kar_metni(kayit)}")
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

def stok_formu(onek, kayit=None, yeni=None):
    """Elimdekiler'e ürün ekleme/düzenleme formu. Girilen değerleri döndürür. `yeni=True` ise `kayit`
    yalnızca başlangıç değerleridir (yeni ürün, adet alanı "Adet" olur)."""
    k = kayit or {}
    duzenleme = kayit is not None and not yeni
    kategoriler = secenekler(db.KATEGORILER, db.kullanilan_degerler("kategori"), k.get("kategori"))
    kaynaklar = secenekler([], db.kullanilan_degerler("kaynak"), k.get("kaynak"))

    def secim(liste, deger):
        return {"index": liste.index(deger)} if deger in liste else {"index": None}

    # Düzen: tasarim/03-elimdekiler.html — Alış fiyatı ile Adet yan yana, aralarında başka kutu yok
    urun = st.text_input("Ürün adı", key=f"{onek}_urun", value=k.get("urun_adi", ""), placeholder="Örn. Deri çanta")
    durum = st.segmented_control("Durum", db.DURUMLAR, key=f"{onek}_durum", required=True, width="stretch",
                                 default=k.get("durum") if k.get("durum") in db.DURUMLAR else db.DURUMLAR[0])
    c1, c2 = st.columns([3, 2])
    alis = c1.number_input("Alış fiyatı ₺ / adet", key=f"{onek}_alis", value=float(k.get("alis_fiyati", 0)), **PARA)
    adet = c2.number_input("Elde kalan adet" if duzenleme else "Adet", key=f"{onek}_adet",
                           min_value=0 if duzenleme else 1, step=1, value=int(k.get("kalan", 1)))
    c1, c2 = st.columns(2)
    kaynak = c1.selectbox("Nereden alındı", kaynaklar, key=f"{onek}_kaynak", accept_new_options=True,
                          placeholder="Toptancı A, ilan…", **secim(kaynaklar, k.get("kaynak")))
    kategori = c2.selectbox("Kategori", kategoriler, key=f"{onek}_kategori", accept_new_options=True,
                            placeholder="Seç veya yaz", **secim(kategoriler, k.get("kategori")))
    c1, c2 = st.columns([3, 2])
    hedef = c1.number_input("Hedef satış fiyatı ₺", key=f"{onek}_hedef",
                            value=float(k.get("hedef_fiyat", 0)), **PARA,
                            help="İsteğe bağlı. Kaça satmayı düşünüyorsan yaz; satarken fiyat kutusu bununla dolu gelir. "
                                 "Fiyat Hesapla sayfası uygun fiyatı bulmana yardım eder.")
    tarih = c2.date_input("Alış tarihi", key=f"{onek}_tarih", value=k.get("alis_tarihi", date.today()),
                          format="DD.MM.YYYY")
    notlar = st.text_input("Not", key=f"{onek}_notlar", value=k.get("notlar", ""),
                           placeholder="Örn. kutusu yok, hafif çizik")
    if hedef > 0 and alis > 0:
        brut = (hedef - alis) * adet
        renk = styles.kar_rengi(brut)
        styles.not_kutusu(f"Hedef fiyattan satılırsa kalan: <b style=\"color:{renk}\">{styles.para(brut, 2, True)}"
                          "</b> (kargo ve komisyon hariç).")
    else:
        styles.not_kutusu("Hedef fiyat girersen tahmini kâr burada görünür.")
    return {"urun_adi": urun, "durum": durum, "alis_fiyati": alis, "alis_tarihi": tarih, "adet": adet,
            "kalan": adet, "kaynak": kaynak, "kategori": kategori, "hedef_fiyat": hedef, "notlar": notlar}


def _stok_dogrula(kayit):
    if not kayit["urun_adi"].strip():
        return "Lütfen ürün adını yazın."
    if kayit["alis_fiyati"] < 0:
        return "Alış fiyatı eksi olamaz."
    return None


def stok_ekle_paneli():
    """Elimdekiler sayfasının sağındaki "Ürün ekle" formu (açılır pencere değil, sayfada sürekli açık)."""
    kayit = stok_formu("stok_yeni")
    if st.button("Elimdekiler'e ekle", icon=":material/add:", type="primary", width="stretch", key="stok_yeni_ekle"):
        hata = _stok_dogrula(kayit)
        if hata:
            st.error(hata, icon=":material/error:")
            return
        db.stok_ekle(kayit)
        formu_sifirla("stok_yeni")
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
                                             f"Satış kârı: {_net_kar_metni(kayit)}")
        formu_sifirla(onek)
        st.rerun()


# ---------- Fırsat Takibi ----------

OTOMATIK_KANAL = "En kârlı kanal (otomatik)"


def firsat_kar_onizleme(alis, kargo, piyasa, kanal):
    if piyasa <= 0:
        st.caption("Tahmini satış fiyatını girince satış kârı burada hesaplanır. Bilmiyorsan boş bırak; listeye "
                   "ekledikten sonra “Claude'a sor” ile öğrenebilirsin.")
        return
    sonuc = fiyat.en_iyi_kanal(alis, kargo, piyasa, db.kanallari_getir(), kanal)
    renk = "blue" if sonuc["net_kar"] >= 0 else "orange"
    st.markdown(f"{sonuc['kanal']} kanalında satarsan adet başına satış kârı: :{renk}[**{tl(sonuc['net_kar'])}**]  ·  "
                f"Kâr marjı: :{renk}[**{yuzde(sonuc['marj'])}**]  ·  {fiyat.degerlendirme(sonuc['marj'])}",
                help="Tahmini satış fiyatı − alış − kargo − kanal komisyonu. Komisyon oranları Ayarlar'dan gelir; "
                     "otomatik seçimde elden satış hesaba katılmaz.")


def firsat_formu(onek, kayit=None):
    """Fırsat ekleme/düzenleme formu. Girilen değerleri döndürür."""
    k = kayit or {}
    kategoriler = secenekler(db.KATEGORILER, db.kullanilan_degerler("kategori"), k.get("kategori"))
    kaynaklar = secenekler(["Sahibinden", "Dolap", "Letgo"], db.kullanilan_degerler("kaynak"), k.get("kaynak"))
    kanallar = ["", *secenekler(db.kanal_adlari(), [], k.get("kanal") or None)]

    def secim(liste, deger):
        return {"index": liste.index(deger)} if deger in liste else {"index": None}

    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    urun = c1.text_input("Ürün adı", key=f"{onek}_urun", value=k.get("urun_adi", ""),
                         placeholder="Örn. iPhone 13 128 GB")
    durum = c2.radio("Durum", db.DURUMLAR, key=f"{onek}_durum", horizontal=True,
                     index=db.DURUMLAR.index(k.get("durum", db.DURUMLAR[0])))
    c1, c2 = st.columns(2)
    kaynak_turu = c1.selectbox("Nerede buldun", db.KAYNAK_TURLERI, key=f"{onek}_kaynak_turu",
                               **secim(db.KAYNAK_TURLERI, k.get("kaynak_turu") or db.KAYNAK_TURLERI[0]))
    kaynak = c2.selectbox("Site / satıcı / mağaza", kaynaklar, key=f"{onek}_kaynak", accept_new_options=True,
                          placeholder="Örn. Sahibinden, Toptancı A, Teknosa", **secim(kaynaklar, k.get("kaynak")))
    link = st.text_input("İlan / ürün linki (isteğe bağlı)", key=f"{onek}_link", value=k.get("link", ""),
                         placeholder="https://…")
    c1, c2, c3 = st.columns([2, 1, 2])
    alis = c1.number_input("Alış fiyatı ₺ / adet", key=f"{onek}_alis", value=float(k.get("alis_fiyati", 0)), **PARA,
                           help="İlandaki ya da toptancının istediği fiyat. Pazarlık edersen sonra güncelleyebilirsin.")
    adet = c2.number_input("Adet", key=f"{onek}_adet", min_value=1, step=1, value=int(k.get("adet", 1)))
    kargo = c3.number_input("Satarken kargo ₺ / adet", key=f"{onek}_kargo", **PARA,
                            value=float(k.get("kargo", db.ayar_getir("varsayilan_kargo", "0"))))
    c1, c2 = st.columns(2)
    piyasa = c1.number_input("Tahmini satış fiyatı ₺ / adet", key=f"{onek}_piyasa", **PARA,
                             value=float(k.get("piyasa_fiyati", 0)),
                             help="Bu ürünü kaça satabileceğini düşünüyorsun? Bilmiyorsan 0 bırak.")
    kanal = c2.selectbox("Satış kanalı", kanallar, key=f"{onek}_kanal", format_func=lambda a: a or OTOMATIK_KANAL,
                         index=kanallar.index(k.get("kanal") or ""))
    with st.expander("Ek bilgiler: kategori, not", expanded=bool(k.get("kategori") or k.get("notlar"))):
        c1, c2 = st.columns(2)
        kategori = c1.selectbox("Kategori", kategoriler, key=f"{onek}_kategori", accept_new_options=True,
                                placeholder="Seç veya yaz", **secim(kategoriler, k.get("kategori")))
        notlar = c2.text_input("Not", key=f"{onek}_notlar", value=k.get("notlar", ""),
                               placeholder="Örn. Pil sağlığı %85, kutulu")
    firsat_kar_onizleme(alis, kargo, piyasa, kanal)
    return {"urun_adi": urun, "durum": durum, "kaynak_turu": kaynak_turu, "kaynak": kaynak, "link": link,
            "alis_fiyati": alis, "adet": adet, "kargo": kargo, "piyasa_fiyati": piyasa, "kanal": kanal,
            "kategori": kategori, "notlar": notlar}


def _firsat_dogrula(kayit):
    if not kayit["urun_adi"].strip():
        return "Lütfen ürün adını yazın."
    if kayit["alis_fiyati"] <= 0:
        return "Alış fiyatı 0'dan büyük olmalı."
    return None


@st.dialog("Fırsat ekle", width="large")
def firsat_ekle_penceresi():
    st.caption("Gözüne kestirdiğin bir ürünü takip listene ekle. Uygulama her kanaldaki satış kârını hesaplar.")
    kayit = firsat_formu("firsat_yeni")
    if st.button("Listeye ekle", icon=":material/add:", type="primary"):
        hata = _firsat_dogrula(kayit)
        if hata:
            st.error(hata, icon=":material/error:")
            return
        st.session_state.ft_secili = db.firsat_ekle(kayit)
        formu_sifirla("firsat_yeni")
        st.session_state.firsat_mesaj = ("ok", f"“{kayit['urun_adi'].strip()}” takip listesine eklendi.")
        st.rerun()


def _firsat_kaydi(firsat_id):
    df = db.firsatlari_getir()
    r = df[df["id"] == firsat_id].iloc[0]
    return {**{a: r[a] for a in ["urun_adi", "durum", "kategori", "kaynak_turu", "kaynak", "link", "kanal",
                                 "notlar", "takip"]},
            "alis_fiyati": float(r.alis_fiyati), "adet": int(r.adet), "kargo": float(r.kargo),
            "piyasa_fiyati": float(r.piyasa_fiyati)}


@st.dialog("Fırsatı düzenle", width="large")
def firsat_duzenle_penceresi(firsat_id):
    mevcut = _firsat_kaydi(firsat_id)
    onek = f"firsat_duzenle_{firsat_id}"
    kayit = firsat_formu(onek, mevcut)
    if mevcut["takip"] == db.ALINDI:
        st.caption(":material/inventory_2: Bu ürünü satın aldın; Elimdekiler'de duruyor.")
    else:
        secenek = [db.TAKIPTE, db.VAZGECILDI]
        kayit["takip"] = st.radio("Takip durumu", secenek, key=f"{onek}_takip", horizontal=True,
                                  index=secenek.index(mevcut["takip"]),
                                  help="Vazgeçtiğin ürünler listeden kalkar ama silinmez; istersen geri alırsın.")
    onay = f"firsat_sil_onay_{firsat_id}"
    if st.session_state.get(onay):
        st.warning(f"**{mevcut['urun_adi']}** takip listesinden silinsin mi? Satın aldıysan Elimdekiler'deki ürün "
                   "silinmez.", icon=":material/warning:")
        with st.container(horizontal=True):
            if st.button("Evet, sil", type="primary"):
                db.firsat_sil(firsat_id)
                st.session_state.pop(onay, None)
                st.session_state.firsat_mesaj = ("ok", "Fırsat silindi.")
                st.rerun()
            if st.button("Vazgeç"):
                st.session_state.pop(onay, None)
                st.rerun(scope="fragment")
        return
    with st.container(horizontal=True):
        if st.button("Değişiklikleri kaydet", icon=":material/save:", type="primary"):
            hata = _firsat_dogrula(kayit)
            if hata:
                st.error(hata, icon=":material/error:")
                return
            db.firsat_guncelle(firsat_id, kayit)
            st.session_state.firsat_mesaj = ("ok", f"“{kayit['urun_adi'].strip()}” güncellendi.")
            st.rerun()
        if st.button("Sil", icon=":material/delete:"):
            st.session_state[onay] = True
            st.rerun(scope="fragment")


@st.dialog("Satın aldım", width="large")
def firsat_satin_al_penceresi(firsat_id):
    f = _firsat_kaydi(firsat_id)
    st.caption("Ürün Elimdekiler'e eklenir; tahmini satış fiyatı hedef fiyat olarak yazılır. Pazarlıkla daha "
               "ucuza aldıysan alış fiyatını düzelt.")
    stok = stok_formu(f"firsat_al_{firsat_id}", {
        "urun_adi": f["urun_adi"], "durum": f["durum"], "kategori": f["kategori"], "kaynak": f["kaynak"],
        "alis_fiyati": f["alis_fiyati"], "alis_tarihi": date.today(), "kalan": f["adet"],
        "hedef_fiyat": f["piyasa_fiyati"], "notlar": f["notlar"]}, yeni=True)
    if st.button("Elimdekiler'e ekle", icon=":material/inventory_2:", type="primary"):
        hata = _stok_dogrula(stok)
        if hata:
            st.error(hata, icon=":material/error:")
            return
        db.firsati_satin_al(firsat_id, stok)
        st.session_state.firsat_mesaj = ("ok", f"“{stok['urun_adi'].strip()}” Elimdekiler'e eklendi. "
                                               "Satınca orada tek tıkla satışa dönüştürebilirsin.")
        st.rerun()


# ---------- Ek giderler ----------

YENI_KATEGORI = "+ Yeni"


def gider_ekle_paneli():
    """Giderler sayfasının sağındaki "Gider ekle" formu (sayfada sürekli açık). Görünüm: tasarim/05-giderler.html."""
    tarih = st.date_input("Tarih", value=date.today(), format="DD.MM.YYYY", key="gider_tarih")
    kategori = st.pills("Kategori", [*db.gider_kategorileri(), YENI_KATEGORI], key="gider_kategori",
                        default=db.GIDER_KATEGORILERI[0])
    if kategori == YENI_KATEGORI:
        kategori = st.text_input("Yeni kategori adı", key="gider_yeni_kategori", placeholder="Örn. Etiket yazıcı")
    aciklama = st.text_input("Açıklama (isteğe bağlı)", key="gider_aciklama", placeholder="Örn. 100'lü kargo poşeti")
    tutar = st.number_input("Tutar ₺", key="gider_tutar", **PARA)
    if st.button("Kaydet", type="primary", width="stretch", key="gider_kaydet"):
        if tutar <= 0:
            st.error("Tutar 0'dan büyük olmalı.", icon=":material/error:")
            return
        if not (kategori or "").strip():
            st.error("Bir kategori seç.", icon=":material/error:")
            return
        db.gider_ekle({"tarih": tarih, "kategori": kategori, "aciklama": aciklama, "tutar": tutar})
        formu_sifirla("gider")
        st.session_state.gider_mesaj = ("ok", f"{tl(tutar)} gider kaydedildi.")
        st.rerun()
