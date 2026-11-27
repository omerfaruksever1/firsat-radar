"""Satış verilerinden yorum üretimi.

- akilli_ozet / urun_yorumu: yapay zeka KULLANMAZ; verilere bakıp önceden yazılmış kurallarla
  Türkçe tespitler çıkarır. Ücretsizdir ve internetsiz çalışır.
- *_istemi: kullanıcının claude.ai'ye yapıştırması için hazır soru metni üretir (internet
  araştırması dahil). İleride doğrudan yapay zeka bağlantısı eklenirse aynı metinler kullanılabilir.

Her tespit (tur, metin) çiftidir; tur: "iyi", "uyari" veya "bilgi".
"""

import pandas as pd

AZ_VERI = 5  # bu sayıdan az satışta yorumların sınırlı olduğu belirtilir


def _tl(tutar):
    metin = f"{abs(tutar):,.0f}".replace(",", ".")
    return f"{'-' if tutar < 0 else ''}₺{metin}"


def _yuzde(deger):
    return f"{'-' if deger < 0 else ''}%{abs(deger):.1f}".replace(".", ",")


def kucuk_harf(metin):
    """Türkçe küçük harf: Python'un lower() fonksiyonu "İ" harfini bozar."""
    return metin.replace("İ", "i").replace("I", "ı").lower()


def _marj(df):
    ciro = df["ciro"].sum()
    return df["net_kar"].sum() / ciro * 100 if ciro else 0.0


def _degisim(simdi, once):
    return (simdi - once) / abs(once) * 100 if once else None


def akilli_ozet(df, onceki=None, gider=0.0):
    """Seçilen dönemin satışları (df), isteğe bağlı olarak karşılaştırılacak önceki dönem ve bu dönemin
    ürüne bağlı olmayan ek giderleri (₺)."""
    tespitler = []
    if df.empty:
        return [("bilgi", "Bu dönemde satış yok.")]

    ciro, kar, marj = df["ciro"].sum(), df["net_kar"].sum(), _marj(df)

    # Önceki dönemle karşılaştırma
    if onceki is not None and not onceki.empty:
        ciro_d = _degisim(ciro, onceki["ciro"].sum())
        kar_d = _degisim(kar, onceki["net_kar"].sum())
        onceki_marj = _marj(onceki)
        if ciro_d is not None:
            yon = "arttı" if ciro_d >= 0 else "azaldı"
            metin = f"Ciron önceki döneme göre {_yuzde(abs(ciro_d))} {yon} ({_tl(ciro)})."
            if kar_d is not None:
                kar_yon = "arttı" if kar_d >= 0 else "azaldı"
                metin += f" Net kârın {_yuzde(abs(kar_d))} {kar_yon} ({_tl(kar)})."
            tespitler.append(("iyi" if kar >= onceki["net_kar"].sum() else "uyari", metin))
        if abs(marj - onceki_marj) >= 3:
            if marj < onceki_marj:
                tespitler.append(("uyari", f"Kâr marjın düştü ({_yuzde(onceki_marj)} → {_yuzde(marj)}): "
                                           "aynı ciroda daha az kazanıyorsun. Alış, kargo ve komisyonlara bak."))
            else:
                tespitler.append(("iyi", f"Kâr marjın yükseldi ({_yuzde(onceki_marj)} → {_yuzde(marj)})."))
    elif onceki is not None:
        tespitler.append(("bilgi", "Önceki dönemde satış olmadığı için karşılaştırma yapılamadı."))

    # Genel kârlılık
    if kar < 0:
        tespitler.append(("uyari", f"Bu dönemde toplamda zarardasın ({_tl(kar)})."))
    elif marj < 10:
        tespitler.append(("uyari", f"Kâr marjın düşük ({_yuzde(marj)}). Her ₺100'lük satıştan "
                                   f"yaklaşık {_tl(marj)} kazanıyorsun."))
    elif marj >= 25:
        tespitler.append(("iyi", f"Kâr marjın sağlıklı ({_yuzde(marj)}): her ₺100'lük satıştan "
                                 f"yaklaşık {_tl(marj)} kazanıyorsun."))

    # Ürünler
    urunler = df.groupby("urun_adi").agg(adet=("adet", "sum"), net_kar=("net_kar", "sum"),
                                         ciro=("ciro", "sum"))
    en_karli = urunler["net_kar"].idxmax()
    if urunler.loc[en_karli, "net_kar"] > 0:
        pay = urunler.loc[en_karli, "net_kar"] / kar * 100 if kar > 0 else None
        metin = f"En çok kazandıran ürünün “{en_karli}” ({_tl(urunler.loc[en_karli, 'net_kar'])})"
        metin += f"; toplam kârın içindeki payı {_yuzde(pay)}." if pay and len(urunler) > 1 else "."
        tespitler.append(("iyi", metin))
    zararli = urunler[urunler["net_kar"] < 0].sort_values("net_kar")
    if not zararli.empty:
        adlar = ", ".join(f"“{u}” ({_tl(k)})" for u, k in zararli["net_kar"].head(3).items())
        tespitler.append(("uyari", f"Zarar ettiren ürün{'ler' if len(zararli) > 1 else ''}: {adlar}. "
                                   "Satış fiyatı, alış + kargo + komisyon toplamını karşılamıyor."))
    # Toplamda kârlı görünse de tek tek zararına yapılmış satışlar
    zararli_satis = df[(df["net_kar"] < 0) & ~df["urun_adi"].isin(zararli.index)]
    if not zararli_satis.empty:
        ornekler = ", ".join(f"{r.urun_adi} ({r.pazar}, {_tl(r.net_kar)})"
                             for r in zararli_satis.sort_values("net_kar").head(3).itertuples())
        tespitler.append(("uyari", f"{len(zararli_satis)} satışı zararına yapmışsın: {ornekler}. "
                                   "Bu ürünler başka satışlarda kâr ettirdiği için toplamda kârlı görünüyor."))

    # Kanallar
    kanallar = df.groupby("pazar").agg(adet=("adet", "sum"), ciro=("ciro", "sum"),
                                       net_kar=("net_kar", "sum"))
    kanallar = kanallar[kanallar["ciro"] > 0]
    if len(kanallar) > 1:
        kanallar["marj"] = kanallar["net_kar"] / kanallar["ciro"] * 100
        iyi, kotu = kanallar["marj"].idxmax(), kanallar["marj"].idxmin()
        if kanallar.loc[iyi, "marj"] - kanallar.loc[kotu, "marj"] >= 5:
            tespitler.append(("bilgi", f"En kârlı kanalın {iyi} (marj {_yuzde(kanallar.loc[iyi, 'marj'])}); "
                                       f"en düşük {kotu} (marj {_yuzde(kanallar.loc[kotu, 'marj'])})."))

    # Masraflar
    komisyon = (df["komisyon"] * df["adet"]).sum()
    kargo = (df["kargo"] * df["adet"]).sum()
    if ciro and komisyon / ciro >= 0.10:
        tespitler.append(("bilgi", f"Komisyonlara {_tl(komisyon)} ödedin; bu, cironun {_yuzde(komisyon / ciro * 100)} kadarı. "
                                   "Komisyonsuz kanallar (elden, kendi siten) bu payı düşürebilir."))
    if ciro and kargo / ciro >= 0.10:
        tespitler.append(("bilgi", f"Kargoya {_tl(kargo)} ödedin; bu, cironun {_yuzde(kargo / ciro * 100)} kadarı. "
                                   "Düşük fiyatlı ürünlerde kargo kârı eritebilir."))

    # Sıfır / ikinci el
    durumlar = df.groupby("durum").agg(ciro=("ciro", "sum"), net_kar=("net_kar", "sum"))
    if {"Sıfır", "İkinci el"} <= set(durumlar.index):
        m = durumlar["net_kar"] / durumlar["ciro"] * 100
        tespitler.append(("bilgi", f"İkinci el ürünlerde marjın {_yuzde(m['İkinci el'])}, "
                                   f"sıfır ürünlerde {_yuzde(m['Sıfır'])}."))

    # Kategoriler
    kategoriler = df[df["kategori"] != ""].groupby("kategori")["net_kar"].sum()
    if len(kategoriler) > 1 and kategoriler.max() > 0:
        tespitler.append(("bilgi", f"En çok kazandıran kategori: {kategoriler.idxmax()} ({_tl(kategoriler.max())})."))

    # Ek giderler
    if gider > 0:
        gercek = kar - gider
        tespitler.append(("uyari" if gercek < 0 else "bilgi",
                          f"Bu dönemde {_tl(gider)} ek giderin var (ambalaj, ilan vb.). Satış kârından "
                          f"düşünce gerçek kârın {_tl(gercek)}."))

    # Stoktan satılanların satış süresi
    sureler = df["satis_suresi"].dropna() if "satis_suresi" in df else pd.Series(dtype=float)
    if len(sureler) >= 2:
        tespitler.append(("bilgi", f"Elimdekiler'den sattığın ürünler ortalama {sureler.mean():.0f} günde satılmış."))

    if len(df) < AZ_VERI:
        tespitler.append(("bilgi", f"Bu dönemde sadece {len(df)} satış var; kayıt arttıkça yorumlar daha anlamlı olur."))
    return tespitler


BEKLEME_UYARI_GUN = 60


def stok_ozeti(stok):
    """Elimdeki ürünler hakkında tespitler (stok: veritabani.stoklari_getir() çıktısı)."""
    if stok.empty:
        return [("bilgi", "Elinde bekleyen ürün yok.")]
    tespitler = [("bilgi", f"Elinde {int(stok['kalan'].sum())} adet ürün var; bunlara {_tl(stok['sermaye'].sum())} "
                           "bağlı. Bu para, ürünler satılınca geri döner.")]
    eski = stok[stok["bekleme_gun"] >= BEKLEME_UYARI_GUN].sort_values("bekleme_gun", ascending=False)
    if not eski.empty:
        adlar = ", ".join(f"{r.urun_adi} ({r.bekleme_gun} gün)" for r in eski.head(3).itertuples())
        tespitler.append(("uyari", f"{len(eski)} ürün {BEKLEME_UYARI_GUN} günden uzun süredir satılmadı: {adlar}. "
                                   "Fiyatı gözden geçirmeyi ya da başka bir kanalda denemeyi düşün."))
    zararli = stok[(stok["hedef_fiyat"] > 0) & (stok["hedef_fiyat"] <= stok["alis_fiyati"])]
    if not zararli.empty:
        adlar = ", ".join(f"{r.urun_adi} (alış {_tl(r.alis_fiyati)}, hedef {_tl(r.hedef_fiyat)})"
                          for r in zararli.head(3).itertuples())
        tespitler.append(("uyari", f"Hedef satış fiyatı alış fiyatının altında veya eşit: {adlar}. "
                                   "Kargo ve komisyonla birlikte zarar edersin."))
    hedefli = stok[stok["hedef_fiyat"] > 0]
    if not hedefli.empty:
        beklenen = ((hedefli["hedef_fiyat"] - hedefli["alis_fiyati"]) * hedefli["kalan"]).sum()
        tespitler.append(("bilgi", f"Hedef fiyat girdiğin ürünler bu fiyatlardan satılırsa, kargo ve komisyon "
                                   f"hariç yaklaşık {_tl(beklenen)} brüt kazanç bırakır."))
    return tespitler


def urun_yorumu(df, urun):
    """Bir ürünün tüm satışlarına bakarak tespitler."""
    u = df[df["urun_adi"] == urun].sort_values("tarih")
    if u.empty:
        return [("bilgi", "Bu ürün için satış yok.")]
    tespitler = []
    adet, kar, marj = int(u["adet"].sum()), u["net_kar"].sum(), _marj(u)
    tespitler.append(("iyi" if kar >= 0 else "uyari",
                      f"{len(u)} kayıtta toplam {adet} adet sattın; net kâr {_tl(kar)}, marj {_yuzde(marj)}. "
                      f"Adet başına ortalama {_tl(kar / adet)} kazanç."))

    zararlilar = u[u["net_kar"] < 0]
    if not zararlilar.empty:
        en_kotu = zararlilar.loc[zararlilar["net_kar"].idxmin()]
        maliyet = en_kotu["alis_fiyati"] + en_kotu["kargo"] + en_kotu["komisyon"]
        tespitler.append(("uyari", f"{len(zararlilar)} satışta zarar etmişsin. Örneğin {en_kotu['pazar']} satışında "
                                   f"adet başına maliyet {_tl(maliyet)} (alış + kargo + komisyon), satış fiyatı ise "
                                   f"{_tl(en_kotu['satis_fiyati'])}. Bu kanalda fiyatı maliyetin üstünde tutmalısın."))

    if len(u) > 1:
        ilk, son = u["satis_fiyati"].iloc[0], u["satis_fiyati"].iloc[-1]
        if abs(son - ilk) / ilk >= 0.05:
            yon = "yükselttin" if son > ilk else "düşürdün"
            tespitler.append(("bilgi", f"Satış fiyatını {yon} (ilk satış {_tl(ilk)} → son satış {_tl(son)})."))

    kanallar = u.groupby("pazar").agg(adet=("adet", "sum"), net_kar=("net_kar", "sum"))
    if len(kanallar) > 1:
        kanallar["birim"] = kanallar["net_kar"] / kanallar["adet"]
        iyi = kanallar["birim"].idxmax()
        tespitler.append(("bilgi", f"Adet başına en çok {iyi} kanalında kazanmışsın ({_tl(kanallar.loc[iyi, 'birim'])}). "
                                   + ", ".join(f"{k}: {_tl(v)}" for k, v in kanallar["birim"].items() if k != iyi)))
    if "İkinci el" in set(u["durum"]):
        tespitler.append(("bilgi", "İkinci el ürünlerde fiyat, ürünün durumuna çok bağlıdır. Benzer ilanlarla "
                                   "karşılaştırmak için aşağıdaki “Claude'a sor” metnini kullanabilirsin."))
    return tespitler


ESKI_FIRSAT_GUN = 14


def tahmin_isabeti(df):
    """Fırsat Takibi'nden alınıp satılan ürünlerde tahmini satış fiyatı gerçek satış fiyatını ne kadar tuttu?
    %100 = tam isabet. Bu tür satış yoksa None. Adet ağırlıklı: 100 − ortalama sapma (%)."""
    t = df[df["tahmini_fiyat"].fillna(0) > 0]
    if t.empty:
        return None
    sapma = (t["satis_fiyati"] - t["tahmini_fiyat"]).abs() / t["tahmini_fiyat"] * 100
    return max(0.0, 100 - (sapma * t["adet"]).sum() / t["adet"].sum())


def firsat_ozeti(df):
    """Takipteki fırsatlar hakkında tespitler (df: fiyat.firsatlari_degerlendir() çıktısı)."""
    if df.empty:
        return [("bilgi", "Takip listende ürün yok.")]
    tespitler = []
    fiyatli = df[df["marj"].notna()]
    if not fiyatli.empty:
        en_iyi = fiyatli.iloc[0]
        tur = "iyi" if en_iyi["net_kar"] > 0 else "uyari"
        tespitler.append((tur, f"En iyi görünen: {en_iyi['urun_adi']}. {_tl(en_iyi['alis_fiyati'])} alıp "
                               f"{en_iyi['satis_kanali']} kanalında {_tl(en_iyi['piyasa_fiyati'])} fiyatla satarsan, "
                               f"adet başına {_tl(en_iyi['net_kar'])} net kâr kalır (marj {_yuzde(en_iyi['marj'])})."))
    zararli = fiyatli[fiyatli["net_kar"] < 0]
    if not zararli.empty:
        adlar = ", ".join(zararli["urun_adi"].head(3))
        tespitler.append(("uyari", f"Bu fiyatlarla zarar ettiren {len(zararli)} ürün var: {adlar}. Pazarlık yapmayı "
                                   "ya da listeden çıkarmayı düşün."))
    fiyatsiz = df[df["marj"].isna()]
    if not fiyatsiz.empty:
        tespitler.append(("bilgi", f"{len(fiyatsiz)} ürünün tahmini satış fiyatı girilmemiş, bu yüzden kârı "
                                   "hesaplanamadı. “Claude'a sor” ile piyasa fiyatını öğrenip ekleyebilirsin."))
    eski = df[df["bekleme_gun"] >= ESKI_FIRSAT_GUN]
    if not eski.empty:
        tespitler.append(("bilgi", f"{len(eski)} ürün {ESKI_FIRSAT_GUN} günden uzun süredir listede. İlan "
                                   "satılmış ya da fiyat değişmiş olabilir; kontrol et."))
    return tespitler


# ---------- claude.ai için hazır soru metinleri ----------

def _satis_tablosu(df, en_fazla=60):
    satirlar = ["Tarih | Ürün | Durum | Kategori | Kanal | Adet | Alış | Satış | Kargo | Komisyon | Net kâr"]
    for r in df.head(en_fazla).itertuples():
        satirlar.append(" | ".join(str(x) for x in [
            r.tarih.strftime("%d.%m.%Y"), r.urun_adi, r.durum, r.kategori or "-", r.pazar, r.adet,
            _tl(r.alis_fiyati), _tl(r.satis_fiyati), _tl(r.kargo), _tl(r.komisyon), _tl(r.net_kar)]))
    if len(df) > en_fazla:
        satirlar.append(f"(… ve {len(df) - en_fazla} satış daha; tabloda en yeni {en_fazla} satış var)")
    return "\n".join(satirlar)


def donem_istemi(df, baslangic, bitis):
    ciro, kar = df["ciro"].sum(), df["net_kar"].sum()
    return f"""Türkiye'de bireysel olarak online ve elden satış yapıyorum (sıfır ve ikinci el ürünler). \
{baslangic:%d.%m.%Y} – {bitis:%d.%m.%Y} arasındaki satışlarım aşağıda. Kargo ve komisyon tutarları adet başınadır.

Özet: {len(df)} satış, {int(df['adet'].sum())} adet, ciro {_tl(ciro)}, net kâr {_tl(kar)}, kâr marjı {_yuzde(_marj(df))}.

{_satis_tablosu(df)}

Lütfen:
1. Kâr, zarar ve ciro açısından bu dönemi kısaca değerlendir.
2. İnternette bu ürünlerin Türkiye'deki güncel fiyatlarına bak (Trendyol, Hepsiburada, Sahibinden, Dolap, Letgo vb.) \
ve benim satış fiyatlarımın piyasaya göre düşük mü yüksek mi olduğunu söyle.
3. Kârımı artırmak için somut 3-5 öneri ver (fiyat, kanal seçimi, masraflar, hangi ürünlere ağırlık vermeli).
Cevabı sade Türkçe ile, kısa maddeler halinde yaz."""


def urun_istemi(df, urun):
    u = df[df["urun_adi"] == urun].sort_values("tarih", ascending=False)
    durum = ", ".join(sorted(set(u["durum"])))
    return f"""Türkiye'de bireysel satıcıyım. “{urun}” ürününü ({durum}) sattım; satışlarım aşağıda. \
Kargo ve komisyon tutarları adet başınadır.

{_satis_tablosu(u)}

Lütfen:
1. İnternette bu ürünün Türkiye'deki güncel {kucuk_harf(durum)} fiyatlarına bak (Sahibinden, Dolap, Letgo, Trendyol, \
Hepsiburada vb.) ve benim satış fiyatımı piyasayla karşılaştır.
2. Bu ürünü en kârlı hangi kanalda ve hangi fiyat aralığında satabileceğimi öner.
3. Bu ürünü tekrar alıp satmaya değer mi? Talep, rekabet ve riskler hakkında kısa yorum yap.
Cevabı sade Türkçe ile, kısa maddeler halinde yaz."""


def _firsat_satiri(r):
    parcalar = [f"“{r.urun_adi}” ({kucuk_harf(r.durum)}", f"alış fiyatı {_tl(r.alis_fiyati)}"]
    if r.kaynak or r.kaynak_turu:
        parcalar.append("bulduğum yer: " + " / ".join(x for x in [r.kaynak_turu, r.kaynak] if x))
    if r.notlar:
        parcalar.append(f"not: {r.notlar}")
    metin = ", ".join(parcalar) + ")"
    if r.link:
        metin += f"\n  Link: {r.link}"
    return metin


def firsat_istemi(r):
    """Tek bir fırsat ürünü için piyasa fiyatı araştırması (r: fırsat satırı)."""
    return f"""Türkiye'de bireysel olarak alım-satım yapıyorum. Şu ürünü almayı düşünüyorum:
{_firsat_satiri(r)}

Lütfen:
1. İnternette bu ürünün Türkiye'deki güncel {kucuk_harf(r.durum)} satış fiyatlarına bak (Sahibinden, Dolap, Letgo, Trendyol, Hepsiburada, Amazon TR vb.) ve gerçekçi bir satış fiyatı aralığı ver.
2. Bu ürünü en kolay ve en kârlı hangi kanalda satabileceğimi, ne kadar sürede satılabileceğini tahmin et.
3. Bu fiyattan almaya değer mi? Dikkat etmem gereken riskler (sahte ürün, kusur, düşük talep) neler?
Cevabın EN BAŞINA tek satır olarak tahmini satış fiyatını yaz, örneğin: TAHMİNİ SATIŞ FİYATI: 1.250 TL
Sonra sade Türkçe ile kısa maddeler halinde açıkla."""


def firsat_listesi_istemi(df, en_fazla=20):
    """Birden çok fırsat ürünü için toplu piyasa fiyatı araştırması."""
    satirlar = [f"{i}. {_firsat_satiri(r)}" for i, r in enumerate(df.head(en_fazla).itertuples(), 1)]
    if len(df) > en_fazla:
        satirlar.append(f"(… ve {len(df) - en_fazla} ürün daha; önce bunlara bakalım)")
    liste = "\n".join(satirlar)
    return f"""Türkiye'de bireysel olarak alım-satım yapıyorum. Aşağıdaki ürünleri almayı düşünüyorum:

{liste}

Lütfen her ürün için:
1. İnternette Türkiye'deki güncel satış fiyatlarına bak (Sahibinden, Dolap, Letgo, Trendyol, Hepsiburada, Amazon TR vb.) ve gerçekçi bir tahmini satış fiyatı ver.
2. En uygun satış kanalını ve talebin yüksek mi düşük mü olduğunu söyle.
3. Bu alış fiyatından almaya değer mi, kısaca yorumla.
Sonucu önce şu sütunlarla bir tablo olarak ver: Ürün | Tahmini satış fiyatı (TL) | Önerilen kanal | Almaya değer mi. Sonra sade Türkçe ile kısa açıklama yaz."""
