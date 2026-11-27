"""Satışların, elimdeki ürünlerin (stok), ek giderlerin, satış kanallarının ve ayarların veritabanında
saklanması; kâr hesapları.

Bilgisayarda tek dosyalık SQLite (firsat_radar.db) kullanılır. İnternette yayınlanan sitede ise
`VERITABANI_ADRESI` (PostgreSQL bağlantı adresi) verilir; aynı kod iki veritabanında da çalışır.
"""

import os
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from sqlalchemy.pool import NullPool

# FIRSATRADAR_DB ortam değişkeni yalnızca testlerde ayrı bir veritabanı dosyası kullanmak içindir.
VERITABANI_YOLU = Path(os.environ.get("FIRSATRADAR_DB") or Path(__file__).parent / "firsat_radar.db")
# İnternet veritabanının adresi (sitede Streamlit "secrets" ayarından gelir). Boşsa yerel dosya kullanılır.
VERITABANI_ADRESI = os.environ.get("FIRSATRADAR_DB_URL") or None

DURUMLAR = ["Sıfır", "İkinci el"]
KATEGORILER = ["Elektronik", "Giyim & Aksesuar", "Ev & Yaşam", "Kitap & Hobi", "Kozmetik",
               "Spor & Outdoor", "Anne & Bebek", "Oyuncak", "Diğer"]
# İlk kurulumda eklenen kanallar. Komisyon oranları Ayarlar sayfasından girilir.
VARSAYILAN_KANALLAR = ["Trendyol", "Hepsiburada", "Amazon TR", "Kendi sitem",
                       "Sahibinden", "Dolap", "Letgo", "Elden"]
GIDER_KATEGORILERI = ["Ambalaj", "İlan / öne çıkarma", "Mağaza aboneliği", "Ulaşım", "Diğer"]
# Fırsat Takibi: ürünü nerede bulduğun ve takip durumu
KAYNAK_TURLERI = ["İkinci el ilan", "Toptancı / ithalatçı", "Mağaza indirimi", "Diğer"]
TAKIPTE, ALINDI, VAZGECILDI = "Takipte", "Alındı", "Vazgeçildi"


class StokYetersiz(ValueError):
    """Stoktaki kalan adetten fazlası satılmak istendi."""


# ---------- Bağlantı ----------

_motorlar = {}


def _sqlalchemy_adresi(adres):
    """Neon/Supabase'in verdiği "postgresql://..." adresini SQLAlchemy'nin psycopg sürücüsüne çevirir."""
    for onek in ("postgres://", "postgresql://"):
        if adres.startswith(onek):
            return "postgresql+psycopg://" + adres[len(onek):]
    return adres


def adres_ayarla(adres):
    global VERITABANI_ADRESI
    VERITABANI_ADRESI = adres or None


def yerel_mi():
    """Bilgisayardaki dosya veritabanı mı kullanılıyor (internet veritabanı değil)?"""
    return not VERITABANI_ADRESI


def _motor():
    adres = _sqlalchemy_adresi(VERITABANI_ADRESI) if VERITABANI_ADRESI else f"sqlite:///{VERITABANI_YOLU}"
    if adres not in _motorlar:
        # SQLite dosyası her işlemden sonra kapatılır (yedekleme ve dosya işlemleri için)
        ayar = {"poolclass": NullPool} if adres.startswith("sqlite") else {"pool_pre_ping": True}
        _motorlar[adres] = sa.create_engine(adres, **ayar)
    return _motorlar[adres]


def _calistir(sql, **parametreler):
    with _motor().begin() as baglanti:  # hata olmazsa değişiklikleri kaydeder
        baglanti.execute(sa.text(sql), parametreler)


def _sorgula(sql, **parametreler):
    with _motor().connect() as baglanti:
        return baglanti.execute(sa.text(sql), parametreler).fetchall()


def _tablo_oku(sql, **parametreler):
    with _motor().connect() as baglanti:
        return pd.read_sql_query(sa.text(sql), baglanti, params=parametreler)


# ---------- Tablolar ----------

_sema = sa.MetaData()


def _kimlik():
    return sa.Column("id", sa.Integer, primary_key=True, autoincrement=True)


def _metin(ad, varsayilan=""):
    return sa.Column(ad, sa.Text, nullable=False, server_default=varsayilan)


def _sayi(ad, varsayilan=None, tur=sa.Float):
    return sa.Column(ad, tur, nullable=False, **({"server_default": varsayilan} if varsayilan else {}))


sa.Table("satislar", _sema, _kimlik(),
         sa.Column("urun_adi", sa.Text, nullable=False), _sayi("alis_fiyati"), _sayi("satis_fiyati"),
         sa.Column("pazar", sa.Text, nullable=False), _sayi("kargo", "0"), _sayi("komisyon", "0"),
         sa.Column("tarih", sa.Text, nullable=False), _sayi("adet", "1", sa.Integer),
         _metin("durum", "Sıfır"), _metin("kategori"), _metin("kaynak"), _metin("notlar"),
         sa.Column("stok_id", sa.Integer),  # satış "Elimdekiler"den yapıldıysa o stok kaydı
         sqlite_autoincrement=True)
sa.Table("kanallar", _sema, _kimlik(), sa.Column("ad", sa.Text, nullable=False, unique=True),
         _sayi("komisyon_orani", "0"), _sayi("sira", "0", sa.Integer), sqlite_autoincrement=True)
sa.Table("ayarlar", _sema, sa.Column("anahtar", sa.Text, primary_key=True),
         sa.Column("deger", sa.Text, nullable=False))
sa.Table("stok", _sema, _kimlik(), sa.Column("urun_adi", sa.Text, nullable=False), _metin("durum", "Sıfır"),
         _metin("kategori"), _metin("kaynak"), _sayi("alis_fiyati"), _sayi("adet", "1", sa.Integer),
         _sayi("kalan", "1", sa.Integer), sa.Column("alis_tarihi", sa.Text, nullable=False),
         _sayi("hedef_fiyat", "0"), _metin("notlar"), sqlite_autoincrement=True)
sa.Table("giderler", _sema, _kimlik(), sa.Column("tarih", sa.Text, nullable=False), _metin("kategori"),
         _metin("aciklama"), _sayi("tutar"), sqlite_autoincrement=True)
# Fırsat Takibi: almayı düşündüğün ürünler. piyasa_fiyati: tahmini satış fiyatı (0 = henüz bilinmiyor);
# kanal: satmayı düşündüğün kanal ("" = en kârlı kanal otomatik seçilir); stok_id: satın alınınca stok kaydı.
sa.Table("firsatlar", _sema, _kimlik(), sa.Column("urun_adi", sa.Text, nullable=False), _metin("durum", "Sıfır"),
         _metin("kategori"), _metin("kaynak_turu"), _metin("kaynak"), _metin("link"), _sayi("alis_fiyati"),
         _sayi("adet", "1", sa.Integer), _sayi("kargo", "0"), _sayi("piyasa_fiyati", "0"), _metin("kanal"),
         _metin("notlar"), sa.Column("eklenme_tarihi", sa.Text, nullable=False), _metin("takip", "Takipte"),
         sa.Column("stok_id", sa.Integer), sqlite_autoincrement=True)

# 1. aşamadan kalan veritabanlarında satislar tablosunda olmayan sütunlar (açılışta eklenir)
_SONRADAN_EKLENEN_SUTUNLAR = {
    "durum": "TEXT NOT NULL DEFAULT 'Sıfır'",
    "kategori": "TEXT NOT NULL DEFAULT ''",
    "kaynak": "TEXT NOT NULL DEFAULT ''",
    "notlar": "TEXT NOT NULL DEFAULT ''",
    "stok_id": "INTEGER",
}


def tablolari_olustur():
    """Eksik tabloları oluşturur, eski veritabanlarına yeni sütunları ekler, ilk kanalları yazar."""
    motor = _motor()
    _sema.create_all(motor)
    mevcut = {s["name"] for s in sa.inspect(motor).get_columns("satislar")}
    with motor.begin() as baglanti:
        for ad, tanim in _SONRADAN_EKLENEN_SUTUNLAR.items():
            if ad not in mevcut:
                baglanti.execute(sa.text(f"ALTER TABLE satislar ADD COLUMN {ad} {tanim}"))
        if baglanti.execute(sa.text("SELECT COUNT(*) FROM kanallar")).scalar() == 0:
            baglanti.execute(sa.text("INSERT INTO kanallar (ad, sira) VALUES (:ad, :sira)"),
                             [{"ad": ad, "sira": i} for i, ad in enumerate(VARSAYILAN_KANALLAR)])


def tablolari_sil():
    """Bütün tabloları siler. Yalnızca testlerde, boş bir internet veritabanıyla başlamak için."""
    _sema.drop_all(_motor())


# ---------- Kâr hesabı ----------

def kar_hesapla(alis, satis, kargo, komisyon, adet):
    """(satış − alış − kargo − komisyon) × adet ve satışa göre kâr marjı (%)."""
    net_kar = (satis - alis - kargo - komisyon) * adet
    ciro = satis * adet
    marj = net_kar / ciro * 100 if ciro else 0.0
    return net_kar, marj


# ---------- Satışlar ----------

def _degerler(kayit):
    return {
        "urun_adi": kayit["urun_adi"].strip(),
        "alis_fiyati": float(kayit["alis_fiyati"]),
        "satis_fiyati": float(kayit["satis_fiyati"]),
        "pazar": kayit["pazar"],
        "kargo": float(kayit["kargo"]),
        "komisyon": float(kayit["komisyon"]),
        "tarih": kayit["tarih"].isoformat(),
        "adet": int(kayit["adet"]),
        "durum": kayit.get("durum") or DURUMLAR[0],
        "kategori": (kayit.get("kategori") or "").strip(),
        "kaynak": (kayit.get("kaynak") or "").strip(),
        "notlar": (kayit.get("notlar") or "").strip(),
    }


def _satis_ekle(baglanti, kayit, stok_id=None):
    baglanti.execute(sa.text(
        """INSERT INTO satislar
           (urun_adi, alis_fiyati, satis_fiyati, pazar, kargo, komisyon, tarih, adet,
            durum, kategori, kaynak, notlar, stok_id)
           VALUES (:urun_adi, :alis_fiyati, :satis_fiyati, :pazar, :kargo, :komisyon, :tarih, :adet,
                   :durum, :kategori, :kaynak, :notlar, :stok_id)"""),
        {**_degerler(kayit), "stok_id": stok_id})


def satis_ekle(kayit):
    with _motor().begin() as baglanti:
        _satis_ekle(baglanti, kayit)


def _stok_kalanini_degistir(baglanti, stok_id, fark):
    """Stoğun kalan adedini `fark` kadar değiştirir (eksi: satıldı, artı: geri geldi)."""
    kalan = baglanti.execute(sa.text("SELECT kalan FROM stok WHERE id=:id"), {"id": stok_id}).scalar()
    if kalan is None:  # stok kaydı silinmiş; satış yine de geçerli
        return
    if kalan + fark < 0:
        raise StokYetersiz(f"Elinde bu üründen {kalan} adet var.")
    baglanti.execute(sa.text("UPDATE stok SET kalan = kalan + :fark WHERE id=:id"), {"fark": fark, "id": stok_id})


def stoktan_sat(stok_id, kayit):
    """Elimdekiler'deki bir ürünü satar: satış kaydı eklenir, stoğun kalan adedi düşer."""
    with _motor().begin() as baglanti:
        _stok_kalanini_degistir(baglanti, stok_id, -int(kayit["adet"]))
        _satis_ekle(baglanti, kayit, stok_id)


def satis_guncelle(kayit_id, kayit):
    """Stoktan yapılmış bir satışın adedi değişirse stoktaki kalan da buna göre düzeltilir."""
    with _motor().begin() as baglanti:
        stok_id, eski_adet = baglanti.execute(
            sa.text("SELECT stok_id, adet FROM satislar WHERE id=:id"), {"id": kayit_id}).one()
        if stok_id is not None:
            _stok_kalanini_degistir(baglanti, stok_id, eski_adet - int(kayit["adet"]))
        baglanti.execute(sa.text(
            """UPDATE satislar SET urun_adi=:urun_adi, alis_fiyati=:alis_fiyati, satis_fiyati=:satis_fiyati,
               pazar=:pazar, kargo=:kargo, komisyon=:komisyon, tarih=:tarih, adet=:adet, durum=:durum,
               kategori=:kategori, kaynak=:kaynak, notlar=:notlar WHERE id=:id"""),
            {**_degerler(kayit), "id": kayit_id})


def satis_sil(kayit_id):
    """Stoktan yapılmış bir satış silinirse ürün(ler) Elimdekiler'e geri döner."""
    with _motor().begin() as baglanti:
        satir = baglanti.execute(sa.text("SELECT stok_id, adet FROM satislar WHERE id=:id"),
                                 {"id": kayit_id}).first()
        if satir and satir.stok_id is not None:
            _stok_kalanini_degistir(baglanti, satir.stok_id, satir.adet)
        baglanti.execute(sa.text("DELETE FROM satislar WHERE id=:id"), {"id": kayit_id})


def satislari_getir(baslangic: date | None = None, bitis: date | None = None):
    """Satışları hesaplanmış ciro, maliyet, net kâr ve marj sütunlarıyla döndürür."""
    # tahmini_fiyat: ürün Fırsat Takibi'nden alındıysa orada tahmin edilen satış fiyatı (tahmin isabeti için)
    sql = ("SELECT s.*, st.alis_tarihi AS stok_alis_tarihi, f.piyasa_fiyati AS tahmini_fiyat FROM satislar s "
           "LEFT JOIN stok st ON st.id = s.stok_id "
           "LEFT JOIN firsatlar f ON f.stok_id = s.stok_id AND s.stok_id IS NOT NULL WHERE 1=1")
    parametreler = {}
    if baslangic:
        sql += " AND s.tarih >= :bas"
        parametreler["bas"] = baslangic.isoformat()
    if bitis:
        sql += " AND s.tarih <= :bit"
        parametreler["bit"] = bitis.isoformat()
    df = _tablo_oku(sql + " ORDER BY s.tarih DESC, s.id DESC", **parametreler)

    df["tarih"] = pd.to_datetime(df["tarih"])
    # Stoktan satılan ürünlerde alıştan satışa geçen gün sayısı (diğerlerinde boş)
    df["satis_suresi"] = (df["tarih"] - pd.to_datetime(df["stok_alis_tarihi"])).dt.days
    df["ciro"] = df["satis_fiyati"] * df["adet"]
    df["maliyet"] = (df["alis_fiyati"] + df["kargo"] + df["komisyon"]) * df["adet"]
    df["net_kar"] = df["ciro"] - df["maliyet"]
    df["marj"] = (df["net_kar"] / df["ciro"].where(df["ciro"] != 0) * 100).fillna(0.0)
    return df


def kullanilan_degerler(sutun):
    """Satışlarda, stokta ve fırsat listesinde daha önce girilmiş farklı değerler (form önerileri için)."""
    assert sutun in ("kategori", "kaynak")
    return [s[0] for s in _sorgula(
        f"SELECT {sutun} FROM satislar WHERE {sutun} != '' UNION "
        f"SELECT {sutun} FROM stok WHERE {sutun} != '' UNION "
        f"SELECT {sutun} FROM firsatlar WHERE {sutun} != '' ORDER BY 1")]


# ---------- Elimdekiler (stok) ----------

def _stok_degerleri(kayit):
    return {
        "urun_adi": kayit["urun_adi"].strip(),
        "durum": kayit.get("durum") or DURUMLAR[0],
        "kategori": (kayit.get("kategori") or "").strip(),
        "kaynak": (kayit.get("kaynak") or "").strip(),
        "alis_fiyati": float(kayit["alis_fiyati"]),
        "alis_tarihi": kayit["alis_tarihi"].isoformat(),
        "hedef_fiyat": float(kayit.get("hedef_fiyat") or 0),
        "notlar": (kayit.get("notlar") or "").strip(),
    }


def _stok_ekle(baglanti, kayit):
    """Yeni stok kaydını ekler ve kimliğini (id) döndürür."""
    adet = int(kayit["adet"])
    sonuc = baglanti.execute(_sema.tables["stok"].insert().values(**_stok_degerleri(kayit), adet=adet, kalan=adet))
    return sonuc.inserted_primary_key[0]


def stok_ekle(kayit):
    with _motor().begin() as baglanti:
        return _stok_ekle(baglanti, kayit)


def stok_guncelle(stok_id, kayit):
    """`kayit["kalan"]` elde kalan adettir; toplam alınan adet, satılanlar korunarak yeniden hesaplanır."""
    with _motor().begin() as baglanti:
        adet, kalan = baglanti.execute(sa.text("SELECT adet, kalan FROM stok WHERE id=:id"), {"id": stok_id}).one()
        yeni_kalan = int(kayit["kalan"])
        baglanti.execute(sa.text(
            """UPDATE stok SET urun_adi=:urun_adi, durum=:durum, kategori=:kategori, kaynak=:kaynak,
               alis_fiyati=:alis_fiyati, alis_tarihi=:alis_tarihi, hedef_fiyat=:hedef_fiyat, notlar=:notlar,
               kalan=:kalan, adet=:adet WHERE id=:id"""),
            {**_stok_degerleri(kayit), "kalan": yeni_kalan, "adet": adet - kalan + yeni_kalan, "id": stok_id})


def stok_sil(stok_id):
    """Stok kaydını siler. Bu üründen daha önce yapılmış satışlar silinmez."""
    _calistir("DELETE FROM stok WHERE id=:id", id=stok_id)


def stoklari_getir(sadece_eldekiler=True, bugun=None):
    """Elimdeki ürünler: bekleme süresi (gün) ve bağlı sermaye (alış × kalan) sütunlarıyla."""
    df = _tablo_oku("SELECT * FROM stok" + (" WHERE kalan > 0" if sadece_eldekiler else "")
                    + " ORDER BY alis_tarihi, id")
    df["alis_tarihi"] = pd.to_datetime(df["alis_tarihi"])
    df["bekleme_gun"] = (pd.Timestamp(bugun or date.today()) - df["alis_tarihi"]).dt.days
    df["sermaye"] = df["alis_fiyati"] * df["kalan"]
    return df


# ---------- Fırsat Takibi (almayı düşündüğün ürünler) ----------

def _link(adres):
    adres = (adres or "").strip()
    if adres and not adres.lower().startswith(("http://", "https://")):
        adres = "https://" + adres
    return adres


def _firsat_degerleri(kayit):
    return {
        "urun_adi": kayit["urun_adi"].strip(),
        "durum": kayit.get("durum") or DURUMLAR[0],
        "kategori": (kayit.get("kategori") or "").strip(),
        "kaynak_turu": kayit.get("kaynak_turu") or "",
        "kaynak": (kayit.get("kaynak") or "").strip(),
        "link": _link(kayit.get("link")),
        "alis_fiyati": float(kayit["alis_fiyati"]),
        "adet": int(kayit.get("adet") or 1),
        "kargo": float(kayit.get("kargo") or 0),
        "piyasa_fiyati": float(kayit.get("piyasa_fiyati") or 0),
        "kanal": kayit.get("kanal") or "",
        "notlar": (kayit.get("notlar") or "").strip(),
    }


def firsat_ekle(kayit):
    with _motor().begin() as baglanti:
        sonuc = baglanti.execute(_sema.tables["firsatlar"].insert().values(
            **_firsat_degerleri(kayit), eklenme_tarihi=(kayit.get("eklenme_tarihi") or date.today()).isoformat(),
            takip=TAKIPTE))
        return sonuc.inserted_primary_key[0]


def firsat_guncelle(firsat_id, kayit):
    """Bilgileri günceller. `kayit["takip"]` verilirse takip durumu da değişir (Takipte / Vazgeçildi)."""
    degerler = _firsat_degerleri(kayit)
    takip = kayit.get("takip")
    _calistir(
        "UPDATE firsatlar SET " + ", ".join(f"{ad}=:{ad}" for ad in degerler)
        + (", takip=:takip" if takip else "") + " WHERE id=:id",
        **degerler, **({"takip": takip} if takip else {}), id=firsat_id)


def firsat_sil(firsat_id):
    """Fırsat kaydını siler. Satın alındıysa Elimdekiler'deki ürün ve satışları silinmez."""
    _calistir("DELETE FROM firsatlar WHERE id=:id", id=firsat_id)


def firsati_satin_al(firsat_id, stok_kaydi):
    """Fırsatı satın alındı olarak işaretler ve ürünü Elimdekiler'e ekler (tek işlemde). Stok kimliğini döndürür."""
    with _motor().begin() as baglanti:
        stok_id = _stok_ekle(baglanti, stok_kaydi)
        baglanti.execute(sa.text("UPDATE firsatlar SET takip=:takip, stok_id=:stok_id WHERE id=:id"),
                         {"takip": ALINDI, "stok_id": stok_id, "id": firsat_id})
        return stok_id


def firsatlari_getir(takip=None, bugun=None):
    """Fırsat listesi; `takip` verilirse yalnızca o durumdakiler. Listede bekleme süresi (gün) eklenir."""
    df = _tablo_oku("SELECT * FROM firsatlar" + (" WHERE takip=:takip" if takip else "")
                    + " ORDER BY eklenme_tarihi DESC, id DESC", **({"takip": takip} if takip else {}))
    df["eklenme_tarihi"] = pd.to_datetime(df["eklenme_tarihi"])
    df["bekleme_gun"] = (pd.Timestamp(bugun or date.today()) - df["eklenme_tarihi"]).dt.days
    return df


# ---------- Ek giderler (ürüne bağlı olmayan masraflar) ----------

def gider_ekle(kayit):
    _calistir("INSERT INTO giderler (tarih, kategori, aciklama, tutar) VALUES (:tarih, :kategori, :aciklama, :tutar)",
              tarih=kayit["tarih"].isoformat(), kategori=(kayit.get("kategori") or "").strip(),
              aciklama=(kayit.get("aciklama") or "").strip(), tutar=float(kayit["tutar"]))


def gider_sil(gider_id):
    _calistir("DELETE FROM giderler WHERE id=:id", id=gider_id)


def giderleri_getir(baslangic: date | None = None, bitis: date | None = None):
    sql, parametreler = "SELECT * FROM giderler WHERE 1=1", {}
    if baslangic:
        sql += " AND tarih >= :bas"
        parametreler["bas"] = baslangic.isoformat()
    if bitis:
        sql += " AND tarih <= :bit"
        parametreler["bit"] = bitis.isoformat()
    df = _tablo_oku(sql + " ORDER BY tarih DESC, id DESC", **parametreler)
    df["tarih"] = pd.to_datetime(df["tarih"])
    return df


def gider_kategorileri():
    kayitli = [s[0] for s in _sorgula("SELECT DISTINCT kategori FROM giderler WHERE kategori != ''")]
    return list(dict.fromkeys([*GIDER_KATEGORILERI, *kayitli]))


# ---------- Satış kanalları ----------

def kanallari_getir():
    """Kanallar sırasıyla: DataFrame (id, ad, komisyon_orani)."""
    return _tablo_oku("SELECT id, ad, komisyon_orani FROM kanallar ORDER BY sira, id")


def kanal_adlari():
    return [s[0] for s in _sorgula("SELECT ad FROM kanallar ORDER BY sira, id")]


def komisyon_orani(kanal):
    satir = _sorgula("SELECT komisyon_orani FROM kanallar WHERE ad=:ad", ad=kanal)
    return satir[0][0] if satir else 0.0


def kanallari_kaydet(tablo):
    """Ayarlar'daki kanal tablosunu kaydeder. Yeniden adlandırılan kanalların eski satışları da
    yeni ada taşınır; silinen bir kanalın eski satışları olduğu gibi kalır."""
    with _motor().begin() as baglanti:
        calistir = lambda sql, **p: baglanti.execute(sa.text(sql), p)  # noqa: E731
        eski = dict(calistir("SELECT id, ad FROM kanallar").fetchall())
        kalanlar = {int(r.id) for r in tablo.itertuples(index=False) if pd.notna(r.id) and int(r.id) in eski}
        for kanal_id in set(eski) - kalanlar:
            calistir("DELETE FROM kanallar WHERE id=:id", id=kanal_id)
        # Adlar yer değiştirse bile "aynı ad" kısıtına takılmamak için önce geçici adlar verilir
        for kanal_id in kalanlar:
            calistir("UPDATE kanallar SET ad=:ad WHERE id=:id", ad=f"__gecici_{kanal_id}", id=kanal_id)
        for sira, satir in enumerate(tablo.itertuples(index=False)):
            ad, oran = str(satir.ad).strip(), float(satir.komisyon_orani or 0)
            kanal_id = int(satir.id) if pd.notna(satir.id) and int(satir.id) in kalanlar else None
            if kanal_id is None:
                calistir("INSERT INTO kanallar (ad, komisyon_orani, sira) VALUES (:ad, :oran, :sira)",
                         ad=ad, oran=oran, sira=sira)
                continue
            if eski[kanal_id] != ad:
                calistir("UPDATE satislar SET pazar=:yeni WHERE pazar=:eski", yeni=ad, eski=eski[kanal_id])
            calistir("UPDATE kanallar SET ad=:ad, komisyon_orani=:oran, sira=:sira WHERE id=:id",
                     ad=ad, oran=oran, sira=sira, id=kanal_id)


# ---------- Ayarlar ----------

def ayar_getir(anahtar, varsayilan=""):
    satir = _sorgula("SELECT deger FROM ayarlar WHERE anahtar=:a", a=anahtar)
    return satir[0][0] if satir else varsayilan


def ayar_kaydet(anahtar, deger):
    with _motor().begin() as baglanti:
        guncellenen = baglanti.execute(sa.text("UPDATE ayarlar SET deger=:d WHERE anahtar=:a"),
                                       {"a": anahtar, "d": str(deger)}).rowcount
        if not guncellenen:
            baglanti.execute(sa.text("INSERT INTO ayarlar (anahtar, deger) VALUES (:a, :d)"),
                             {"a": anahtar, "d": str(deger)})


# ---------- Yedekleme ----------

def gunluk_yedek_al(saklanacak_gun=14):
    """Günde bir kez veritabanı dosyasının kopyasını yedekler/otomatik_YYYY-MM-DD.db olarak alır ve en yeni
    `saklanacak_gun` otomatik yedeği tutar. Elle alınmış diğer yedeklere dokunmaz. İnternet veritabanında
    çalışmaz (onun yedeğini veritabanı hizmeti tutar; Ayarlar'dan da indirilebilir)."""
    if not yerel_mi() or not VERITABANI_YOLU.exists():
        return
    klasor = VERITABANI_YOLU.parent / "yedekler"
    klasor.mkdir(exist_ok=True)
    hedef_yol = klasor / f"otomatik_{date.today().isoformat()}.db"
    if not hedef_yol.exists():
        kaynak, hedef = sqlite3.connect(VERITABANI_YOLU), sqlite3.connect(hedef_yol)
        try:
            kaynak.backup(hedef)
        finally:
            kaynak.close()
            hedef.close()
    for eski in sorted(klasor.glob("otomatik_*.db"))[:-saklanacak_gun]:
        eski.unlink()


def yedek_dosyasi():
    """Bütün verilerin tek dosyalık SQLite kopyası (bayt olarak), yedek indirmek için. İnternet
    veritabanında da aynı biçimde bir dosya üretilir; bu dosya bilgisayardaki uygulamada açılabilir."""
    hedef = sqlite3.connect(":memory:")
    try:
        if yerel_mi():
            kaynak = sqlite3.connect(VERITABANI_YOLU)
            try:
                kaynak.backup(hedef)
            finally:
                kaynak.close()
        else:
            for tablo in _sema.sorted_tables:
                _tablo_oku(f"SELECT * FROM {tablo.name}").to_sql(tablo.name, hedef, index=False)
        return hedef.serialize()
    finally:
        hedef.close()
