"""Ekran testleri için ortak araçlar: uygulamayı geçici bir veritabanıyla gerçek bir Streamlit sunucusunda
başlatır ve Streamlit'in "agent API"si ile tarayıcısız gezer (sayfa değiştirme, form doldurma, düğmeler)."""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager

import pytest

from conftest import PROJE


class Uygulama:
    def __init__(self, port, db_yolu):
        self.adres = f"http://127.0.0.1:{port}/_stcore/agent/interact"
        self.db_yolu = db_yolu

    def istek(self, govde):
        r = urllib.request.Request(self.adres, data=json.dumps(govde).encode(),
                                   headers={"Content-Type": "application/json"})
        try:
            return Ekran(json.load(urllib.request.urlopen(r, timeout=60)), self)
        except urllib.error.HTTPError as hata:
            raise AssertionError(hata.read().decode()) from hata

    def sayfa(self, ad=""):
        return self.istek({"page": ad} if ad else {})


class Ekran:
    def __init__(self, cevap, uygulama):
        self.cevap, self.uygulama = cevap, uygulama
        self.ogeler = []
        self._gez(cevap["tree"])
        assert not self.hatalar, json.dumps(self.hatalar, ensure_ascii=False)[:1500]

    def _gez(self, dugum):
        self.ogeler.append(dugum)
        for cocuk in dugum.get("children") or []:
            self._gez(cocuk)

    @property
    def hatalar(self):
        return [o for o in self.ogeler if o.get("type") == "exception"]

    def tur(self, tur):
        return [o for o in self.ogeler if o.get("type") == tur]

    def metinler(self, tur):
        return [o["props"].get("body") or o["props"].get("value") or "" for o in self.tur(tur)]

    def deger(self, anahtar):
        return next(o.get("value") for o in self.ogeler if o.get("key") == anahtar)

    def oge(self, anahtar):
        return next(o for o in self.ogeler if o.get("key") == anahtar)

    def doldur(self, **degerler):
        return self.uygulama.istek({"session_id": self.cevap["session_id"], "widget_state": degerler})

    def sec(self, anahtar, parca):
        """Seçim kutusunda, görünen yazısı `parca`yı içeren seçeneği seçer."""
        secenek = next(o for o in self.oge(anahtar)["props"]["options"] if parca in o)
        return self.doldur(**{anahtar: secenek})

    def eylem(self, etiket, tur=None):
        return next(a["key"] for a in self.cevap["actions"]
                    if a.get("label") == etiket and (tur is None or a.get("type") == tur))

    def tikla(self, etiket):
        return self.uygulama.istek({"session_id": self.cevap["session_id"],
                                    "trigger": {"key": self.eylem(etiket)}})

    def dugme_etiketleri(self):
        return [a.get("label") for a in self.cevap["actions"]]


@contextmanager
def sunucu(db_yolu, gizli_ayarlar=""):
    """Uygulamayı ayrı bir süreçte başlatır. `gizli_ayarlar`: Streamlit "secrets" dosyasının içeriği
    (TOML); projedeki ya da kullanıcı klasöründeki secrets dosyaları kullanılmaz."""
    secrets = db_yolu.parent / "secrets.toml"
    secrets.write_text(gizli_ayarlar, encoding="utf-8")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    ortam = {**os.environ, "FIRSATRADAR_DB": str(db_yolu)}
    ortam.pop("FIRSATRADAR_DB_URL", None)
    surec = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true",
         "--server.address=127.0.0.1", f"--server.port={port}", "--server.enableAgentApi=true",
         f"--secrets.files={secrets}"],
        cwd=PROJE, env=ortam, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(80):
            try:
                if urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2).read() == b"ok":
                    break
            except OSError:
                time.sleep(0.5)
        else:
            pytest.fail("Test sunucusu başlamadı")
        yield Uygulama(port, db_yolu)
    finally:
        surec.kill()
        surec.wait()
