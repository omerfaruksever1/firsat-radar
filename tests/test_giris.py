"""Sitedeki şifre ekranı: şifre ayarlıysa doğru şifre girilmeden hiçbir sayfa ve veri görünmez."""

from arayuz_yardimci import sunucu


def test_sifre_ekrani(tmp_path):
    with sunucu(tmp_path / "test.db", 'site_sifresi = "gizli-123"\n') as uygulama:
        ekran = uygulama.sayfa()
        assert ekran.icerir("Tekrar hoş geldin")
        assert ekran.kpi_sayisi() == 0  # veriler görünmüyor
        assert [s["url_path"] for s in ekran.cevap["pages"]] == [""]  # menü (diğer sayfalar) yok
        oturum = ekran.cevap["session_id"]
        sifre, giris = ekran.eylem("Şifre", "text_input"), ekran.eylem("Giriş yap")

        yanlis = uygulama.istek({"session_id": oturum, "widget_state": {sifre: "yanlis"},
                                 "trigger": {"key": giris}})
        assert "Şifre yanlış." in yanlis.metinler("error")
        assert yanlis.kpi_sayisi() == 0

        dogru = uygulama.istek({"session_id": oturum, "widget_state": {sifre: "gizli-123"},
                                "trigger": {"key": giris}})
        assert dogru.kpi_sayisi() == 5  # Genel Bakış açıldı
        assert len(dogru.cevap["pages"]) == 9
        assert uygulama.istek({"session_id": oturum, "page": "giderler"}).tur("title")[0]["props"]["body"] == "Giderler"

        # Yeni bir ziyaretçi (yeni oturum) yine şifre ekranını görür; sayfa adresini bilse bile giremez
        yeni_ziyaretci = uygulama.sayfa()
        assert yeni_ziyaretci.kpi_sayisi() == 0 and len(yeni_ziyaretci.cevap["pages"]) == 1


def test_sifre_yoksa_sorulmaz(tmp_path):
    with sunucu(tmp_path / "test.db") as uygulama:
        assert uygulama.sayfa().kpi_sayisi() == 5


def test_yanlis_sifrede_gecici_bekletme(tmp_path):
    with sunucu(tmp_path / "test.db", 'site_sifresi = "gizli-123"\n') as uygulama:
        ekran = uygulama.sayfa()
        oturum = ekran.cevap["session_id"]
        sifre, giris = ekran.eylem("Şifre", "text_input"), ekran.eylem("Giriş yap")
        for _ in range(5):
            uygulama.istek({"session_id": oturum, "widget_state": {sifre: "yanlis"}, "trigger": {"key": giris}})
        kilitli = uygulama.istek({"session_id": oturum, "widget_state": {sifre: "gizli-123"},
                                  "trigger": {"key": giris}})
        assert any("Çok fazla yanlış deneme" in m for m in kilitli.metinler("error"))
        assert kilitli.kpi_sayisi() == 0  # doğru şifre bile bekleme bitene kadar girmez
