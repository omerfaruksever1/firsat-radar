# FırsatRadar

Bireysel ve kurumsal satıcılar için e-ticaret takip uygulaması: satış kaydı, elimdeki ürünler (stok),
ek giderler, fiyat hesaplama, raporlar ve ücretsiz "akıllı özet" yorumları. Sıfır ve ikinci el ürünler;
Trendyol, Hepsiburada, Amazon TR, Sahibinden, Dolap, Letgo, elden satış ve kendi siten.

Python + Streamlit ile yazılmıştır. Bilgisayarda tek dosyalık SQLite, internette PostgreSQL veritabanı kullanır.

## Bilgisayarda çalıştırma

`baslat.bat` dosyasına çift tıkla. İlk kurulum için:

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

Veriler `firsat_radar.db` dosyasında durur; her gün `yedekler/` klasörüne otomatik yedek alınır.
Bu dosyalar GitHub'a yüklenmez (`.gitignore`).

## İnternette yayınlama (Streamlit Community Cloud)

1. Ücretsiz bir PostgreSQL veritabanı aç (ör. [Neon](https://neon.tech)) ve bağlantı adresini kopyala.
2. [share.streamlit.io](https://share.streamlit.io) adresinde GitHub hesabınla giriş yap, **Create app** de,
   bu depoyu ve `app.py` dosyasını seç. Gelişmiş ayarlardan Python 3.12'yi seç.
3. **Advanced settings → Secrets** bölümüne `.streamlit/secrets.toml.example` dosyasındaki gibi
   `site_sifresi` ve `veritabani_adresi` değerlerini yapıştır.

Şifre ayarlıysa siteyi açan herkesten şifre istenir. Bilgisayardaki uygulama şifre sormaz.

## Testler

```
.venv\Scripts\python -m pip install -r requirements-test.txt
.venv\Scripts\python -m pytest tests -q
```

Veritabanı testlerini boş bir test PostgreSQL veritabanında çalıştırmak için `FIRSATRADAR_TEST_PG_URL`
ortam değişkenine o veritabanının adresini ver (gerçek verilerin olduğu veritabanını değil).

## Proje yapısı

| Dosya / klasör | Ne işe yarar |
|---|---|
| `app.py` | Giriş noktası: tema, şifre, sol menü |
| `sayfalar/` | Her sayfa ayrı dosyada |
| `arayuz/` | Ortak görünüm parçaları, formlar ve açılır pencereler, şifre ekranı |
| `veritabani.py` | Bütün veri işlemleri (SQLite ve PostgreSQL) |
| `yorum.py` | Akıllı özet kuralları ve "Claude'a sor" metinleri |
| `donemler.py`, `fiyat.py` | Rapor dönemleri ve fiyat hesaplayıcı |
| `ornek_tarama.py` | Ürün Taramaları için örnek veri (gerçek tarama sonraki aşamada) |
| `tests/` | Otomatik testler |
