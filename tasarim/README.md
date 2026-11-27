# Gece Terminali — FırsatRadar tasarım şablonları

Bu klasördeki HTML dosyaları uygulamanın **hedef görünümüdür**. Kod değil, referanstır:
tarayıcıda açıp bakılır, Streamlit'te aynısı kurulur. Rakamlar örnektir.

| Dosya | Sayfa |
|---|---|
| 00-giris.html | Şifre ekranı |
| 01-genel-bakis.html | Genel Bakış |
| 02-urun-taramalari.html | Ürün Taramaları |
| 03-elimdekiler.html | Elimdekiler (sağdaki panel = "Ürün ekle" formu) |
| 04-satislarim.html | Satışlarım |
| 05-giderler.html | Giderler (sağdaki kart = "Gider ekle" formu) |
| 06-raporlar.html | Raporlar |
| 07-fiyat-hesapla.html | Fiyat Hesapla |
| 08-ayarlar.html | Ayarlar |
| 09-yardim.html | Yardım |

## Renkler
| Ad | Değer | Nerede |
|---|---|---|
| zemin | #0B0D12 | sayfa arka planı |
| yan menü | #0F1218 | sidebar |
| kart | #11151C | tüm kartlar/bölümler |
| input | #0E1117 | input, select zemini |
| kenarlık | #1F2531 | kart kenarı |
| kenarlık-2 | #2A3140 | input, ikincil buton |
| ayırıcı | #181D26 | tablo satırları arası |
| aktif menü | #1A2030 | seçili menü öğesi zemini |
| metin | #E7EAF0 | ana metin |
| metin-2 | #8C95A5 | açıklamalar |
| soluk | #6B7486 | tablo başlıkları, grup başlıkları |
| vurgu | #4C7DFF | ana butonlar, seçili durumlar |
| kâr | #3DD68C | pozitif kâr, başarılı |
| zarar | #F26D6D | negatif kâr |
| uyarı | #F5A524 | bekleyen ürün, eksik ayar |

## Kurallar
- Yazı tipi: Inter. Para, yüzde, adet gibi tüm rakamlar: JetBrains Mono.
- Köşe: kart 12px, input/buton 9px, rozet 10px.
- Kâr yeşil "+₺", zarar kırmızı "−₺"; rakam sütunları sağa hizalı.
- Tablo başlıkları 12px, büyük harf, soluk renk.
- Boş durumlar: mavi info kutusu yerine kesik çizgili koyu kart + ilgili buton.
- Veritabanı, hesaplamalar ve kayıt mantığı değişmez; sadece görünüm.
