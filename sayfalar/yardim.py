"""Yardım: uygulamanın sade Türkçe kullanım kılavuzu."""

import streamlit as st

from arayuz.ortak import kart, sayfa_basligi

sayfa_basligi("Yardım", "FırsatRadar'ı nasıl kullanırsın?")

with kart("yr_baslangic"):
    st.subheader("İlk kurulum (bir kez)", anchor=False)
    st.markdown(
        "1. **Ayarlar** sayfasında her satış kanalının komisyon oranını gir (örneğin pazar senden satış "
        "fiyatının %15'ini kesiyorsa 15 yaz). Elden ve kendi sitende 0 kalsın.\n"
        "2. Genelde aynı kargo ücretini ödüyorsan **varsayılan kargo ücreti**ni, istersen **aylık kâr hedefi**ni gir.\n"
        "3. Kullanmadığın kanalları silebilir, eksik olanları ekleyebilirsin.")

with kart("yr_akis"):
    st.subheader("Günlük kullanım", anchor=False)
    st.markdown(
        "- **Bir ürün aldın ama henüz satmadın mı?** **Elimdekiler** sayfasında *Ürün ekle* ile kaydet. Sattığında "
        "ürünü seçip **Sat** de; alış bilgileri hazır gelir, elindeki adet kendiliğinden düşer.\n"
        "- **Doğrudan satış mı yaptın?** **Genel Bakış**taki kısa formu (bugünün tarihiyle) ya da "
        "**Satışlarım → Yeni satış** penceresini kullan.\n"
        "- Fiyatları, kargoyu ve komisyonu **1 adet için** yaz; uygulama adetle çarpar.\n"
        "- Kanalı ve satış fiyatını seçince komisyon, Ayarlar'daki orana göre kendiliğinden yazılır. Farklıysa elle "
        "düzeltebilirsin.\n"
        "- Yanlış bir kaydı düzeltmek için **Satışlarım**'da satıra tıkla, sonra **Düzenle / sil**.\n"
        "- Ambalaj, ilan ücreti gibi ürüne bağlı olmayan masrafları **Giderler** sayfasına yaz; raporlarda "
        "**gerçek kâr** bunlar düşülerek hesaplanır.")

with kart("yr_fiyat"):
    st.subheader("Kaça satmalıyım?", anchor=False)
    st.markdown(
        "**Fiyat Hesapla** sayfasına alış fiyatını ve istediğin kârı (yüzde ya da tutar olarak) gir. Her satış "
        "kanalında komisyon ve kargo düşüldükten sonra bu kârı bırakan fiyatı gösterir. Elindeki bir fiyatla her "
        "kanalda ne kazanacağını da hesaplayabilirsin.")

with kart("yr_rapor"):
    st.subheader("Raporlar ve yorumlar", anchor=False)
    st.markdown(
        "- **Raporlar** sayfasında üstten dönem seç (Bu ay, Geçen ay, Son 30 gün…). Her dönem, bir önceki "
        "benzer dönemle karşılaştırılır.\n"
        "- **Akıllı Özet** verilerine bakıp önemli noktaları yazar (artış/azalış, zararlı satışlar, en kârlı "
        "kanal, giderler…). Ücretsizdir.\n"
        "- **Ürün yorumu** sekmesinde bir ürün seçerek o ürünün tüm satışlarının değerlendirmesini görürsün.\n"
        "- **Claude'a sor** bölümündeki metni kopyalayıp claude.ai'ye yapıştırırsan Claude internette benzer "
        "ilanlara bakarak daha ayrıntılı yorum yapar. Bunu yaptığında satış bilgilerin claude.ai'ye gönderilmiş olur.")

with kart("yr_yedek"):
    st.subheader("Verilerin güvende mi?", anchor=False)
    st.markdown(
        "- Tüm kayıtlar bilgisayarındaki `firsat_radar.db` dosyasında durur. Bu dosyayı silme.\n"
        "- Uygulama her gün ilk açıldığında `yedekler` klasörüne otomatik yedek alır ve son 14 günü saklar.\n"
        "- Ayrıca **Ayarlar → Yedeği indir** ile istediğin zaman bir kopya alıp USB bellekte veya Google Drive'da "
        "saklayabilirsin.\n"
        "- Satış listesini Excel'de görmek için **Satışlarım → Excel'e aktar** düğmesini kullan.")

with kart("yr_baslat"):
    st.subheader("Uygulamayı açmak ve kapatmak", anchor=False)
    st.markdown(
        "- Açmak için `firsat-radar` klasöründeki **baslat.bat** dosyasına çift tıkla. Tarayıcıda açılmazsa adres "
        "çubuğuna `localhost:8501` yaz.\n"
        "- Açılan siyah pencere uygulamayı çalıştırır; küçültebilirsin ama kapatırsan uygulama da kapanır.\n"
        "- Aydınlık / karanlık mod için sağ üstteki **⋮ → Settings** menüsünü kullan.")
