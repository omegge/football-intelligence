"""football-data.org v4 — ücretsiz plan istemcisi ve okuyucusu.

Güvenlik:
- API anahtarı koda, dosyaya, loga YAZILMAZ ve kod tarafından GÖNDERİLMEZ. Anahtar Claude Code ortamının
  "Network secrets" kaydında durur; ağ proxy'si `api.football-data.org` isteklerine `X-Auth-Token` başlığını kendisi
  ekler. Bu modül hiçbir kimlik bilgisi başlığı kurmaz (testle denetlenir).
- Yanıttaki `X-Authenticated-Client` (hesap adı) önbelleğe, meta bilgisine ve kanıta yazılmaz.

Kapsam ve kurallar:
- Yalnızca ücretsiz plandaki 12 yarışma ve yalnızca izinli uç noktalar (maç listesi, puan durumu, yarışma bilgisi).
- Hız sınırı: `X-Requests-Available-Minute` ve `X-Requestcounter-Reset` okunur; hak biterse sıfırlanana kadar beklenir;
  ayrıca istekler arasında asgari 6 sn (dakikada 10 isteğin altında kalmak için).
- 429: `Retry-After` / `X-Requestcounter-Reset` kadar beklenir, en fazla 2 yeniden deneme. 401/403: durulur.
  5xx / zaman aşımı: bir yeniden deneme.
- Önbellek: `output/onbellek/footballdataorg/` (git dışı), SHA-256 bütünlük denetimi.
- MK-1: yanıttaki `odds` alanı (ücretsiz planda yalnızca "Activate Odds-Package…" mesajı) okunmaz ve hiçbir çıktıya
  aktarılmaz; çıktı `girdi.oransiz_mi` ile denetlenir.
Atıf (kullanım koşulları gereği): ATIF metni raporlarda gösterilir.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .. import USER_AGENT
from ..girdi import oransiz_mi
from ..kanit import Kanit

TR = ZoneInfo("Europe/Istanbul")
HOST = "api.football-data.org"
TABAN = f"https://{HOST}/v4"
ATIF = "Football data provided by the Football-Data.org API"
ONBELLEK = Path(__file__).resolve().parents[3] / "output" / "onbellek" / "footballdataorg"

# Ücretsiz plan (www.football-data.org/coverage, 23.11.2026): 12 yarışma
UCRETSIZ_YARISMALAR = {
    "PL": "Premier League", "ELC": "Championship", "BL1": "Bundesliga", "SA": "Serie A", "PD": "Primera Division",
    "FL1": "Ligue 1", "DED": "Eredivisie", "PPL": "Primeira Liga", "BSA": "Campeonato Brasileiro Série A",
    "CL": "UEFA Champions League", "EC": "European Championship", "WC": "FIFA World Cup",
}
IZINLI_UC_NOKTALAR = {
    "maclar": ("competitions/{kod}/matches", {"dateFrom", "dateTo", "status", "matchday", "season", "stage"}),
    "puan_durumu": ("competitions/{kod}/standings", {"season", "matchday", "date"}),
    "yarisma": ("competitions/{kod}", set()),
}
GECERLI_DURUM = {"SCHEDULED", "TIMED", "IN_PLAY", "PAUSED", "FINISHED", "POSTPONED", "SUSPENDED", "CANCELLED", "AWARDED"}
GIZLI_YANIT_BASLIKLARI = {"x-authenticated-client"}
KIMLIK_BASLIKLARI = {"x-auth-token", "authorization", "cookie"}


class FdorgHatasi(RuntimeError):
    def __init__(self, mesaj: str, meta: dict | None = None, dur: bool = False):
        super().__init__(mesaj)
        self.meta = meta or {}
        self.dur = dur


def _varsayilan_acici(istek, zaman_asimi):
    baglam = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or None)
    return urllib.request.urlopen(istek, timeout=zaman_asimi, context=baglam)


def adres(uc_nokta: str, kod: str, **parametre) -> str:
    """İzinli uç nokta + ücretsiz yarışma + izinli parametrelerle URL kurar; aksi halde istek atılmadan hata."""
    if kod not in UCRETSIZ_YARISMALAR:
        raise FdorgHatasi(f"'{kod}' ücretsiz planda değil; ücretli kapsam kullanılmaz", dur=True)
    if uc_nokta not in IZINLI_UC_NOKTALAR:
        raise FdorgHatasi(f"izinsiz uç nokta: {uc_nokta}", dur=True)
    yol, izinli = IZINLI_UC_NOKTALAR[uc_nokta]
    parametre = {k: v for k, v in parametre.items() if v is not None}
    fazla = set(parametre) - izinli
    if fazla:
        raise FdorgHatasi(f"izinsiz parametre: {sorted(fazla)}", dur=True)
    for k in ("dateFrom", "dateTo", "date"):
        if k in parametre and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(parametre[k])):
            raise FdorgHatasi(f"{k} YYYY-AA-GG olmalı", dur=True)
    if "status" in parametre and not set(str(parametre["status"]).split(",")) <= GECERLI_DURUM:
        raise FdorgHatasi(f"geçersiz status: {parametre['status']}", dur=True)
    q = urllib.parse.urlencode(sorted((k, str(v)) for k, v in parametre.items() if v is not None))
    return f"{TABAN}/{yol.format(kod=kod)}" + (f"?{q}" if q else "")


class FdorgIstemcisi:
    def __init__(self, onbellek: Path = ONBELLEK, acici=_varsayilan_acici, saat=time.monotonic, uyku=time.sleep,
                 simdi=lambda: datetime.now(timezone.utc), asgari_aralik: float = 6.0, maks_429: int = 2,
                 zaman_asimi: float = 30.0):
        self.onbellek = Path(onbellek)
        self.acici, self.saat, self.uyku, self.simdi = acici, saat, uyku, simdi
        self.asgari_aralik, self.maks_429, self.zaman_asimi = asgari_aralik, maks_429, zaman_asimi
        self._son = None                      # son isteğin saat() değeri
        self._kalan = None                    # X-Requests-Available-Minute
        self._sifirlanma = None               # saat() cinsinden sıfırlanma anı
        self.istek_sayisi = 0
        self.bekleme_toplam = 0.0

    # --- önbellek ---
    def _yol(self, url: str) -> Path:
        return self.onbellek / hashlib.sha256(url.encode()).hexdigest()[:32]

    def _onbellekten(self, url: str, sure: float):
        p = self._yol(url)
        b, j = p.with_suffix(".json"), p.with_suffix(".meta.json")
        if not (b.exists() and j.exists()):
            return None
        meta = json.loads(j.read_text(encoding="utf-8"))
        yas = (self.simdi() - datetime.fromisoformat(meta["erisim_utc"])).total_seconds()
        govde = b.read_bytes()
        if yas > sure or hashlib.sha256(govde).hexdigest() != meta.get("sha256"):
            return None
        return json.loads(govde), {**meta, "onbellekten": True, "onbellek_yasi_sn": int(yas)}

    def _bekle(self):
        simdi = self.saat()
        bekle = 0.0
        if self._son is not None:
            bekle = max(bekle, self.asgari_aralik - (simdi - self._son))
        if self._kalan is not None and self._kalan <= 0 and self._sifirlanma is not None:
            bekle = max(bekle, self._sifirlanma - simdi + 1.0)
        if bekle > 0:
            self.uyku(bekle)
            self.bekleme_toplam += bekle

    def _hiz_basliklarini_oku(self, basliklar):
        def al(ad):
            for k, v in (basliklar.items() if basliklar else []):
                if k.lower() == ad:
                    return v
            return None
        kalan, sifir = al("x-requests-available-minute"), al("x-requestcounter-reset")
        try:
            self._kalan = int(kalan) if kalan is not None else self._kalan
        except ValueError:
            pass
        try:
            if sifir is not None:
                self._sifirlanma = self.saat() + float(sifir)
        except ValueError:
            pass
        return {"kalan_istek_dakika": self._kalan, "sifirlanma_sn": float(sifir) if sifir else None,
                "api_surumu": al("x-api-version")}

    def getir(self, url: str, onbellek_sn: float = 900.0) -> tuple[dict, dict]:
        """(json, meta). url `adres()` ile kurulmuş olmalı. meta hesap adı ya da kimlik bilgisi içermez."""
        u = urllib.parse.urlparse(url)
        if u.scheme != "https" or u.hostname != HOST or not u.path.startswith("/v4/"):
            raise FdorgHatasi(f"izinsiz adres: {url}", dur=True)
        k = self._onbellekten(url, onbellek_sn)
        if k:
            return k
        deneme_429 = 0
        gecici = 0
        while True:
            self._bekle()
            simdi = self.simdi()
            meta = {"kaynak": "football-data.org v4 (ücretsiz plan)", "url": url,
                    "erisim_utc": simdi.isoformat(timespec="seconds"),
                    "erisim_tr": simdi.astimezone(TR).isoformat(timespec="seconds"),
                    "user_agent": USER_AGENT, "onbellekten": False, "atif": ATIF}
            istek = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            self._son = self.saat()
            self.istek_sayisi += 1
            try:
                with self.acici(istek, self.zaman_asimi) as r:
                    govde = r.read()
                    meta["http_durumu"] = getattr(r, "status", 200)
                    meta.update(self._hiz_basliklarini_oku(getattr(r, "headers", None)))
            except urllib.error.HTTPError as h:
                meta["http_durumu"] = h.code
                meta.update(self._hiz_basliklarini_oku(h.headers))
                if h.code == 429 and deneme_429 < self.maks_429:
                    deneme_429 += 1
                    ra = None
                    for kk, v in (h.headers.items() if h.headers else []):
                        if kk.lower() in ("retry-after", "x-requestcounter-reset"):
                            try:
                                ra = float(v)
                            except ValueError:
                                pass
                    bekle = min(max(ra or 60.0, 1.0), 65.0)
                    self.uyku(bekle)
                    self.bekleme_toplam += bekle
                    continue
                if h.code == 429:
                    raise FdorgHatasi(f"HTTP 429: hız sınırı {self.maks_429} yeniden denemeden sonra da aşıldı", meta, dur=True)
                if h.code in (401, 403):
                    raise FdorgHatasi(f"HTTP {h.code}: yetki yok (ücretsiz plan dışı ya da kimlik bilgisi sorunu); "
                                      "durduruldu, yeniden denenmedi", meta, dur=True)
                if h.code >= 500 and gecici == 0:
                    gecici += 1
                    self.uyku(5.0)
                    continue
                raise FdorgHatasi(f"HTTP {h.code}", meta)
            except (urllib.error.URLError, TimeoutError, OSError) as h:
                neden = str(getattr(h, "reason", h))
                if gecici == 0 and "unnel" not in neden:
                    gecici += 1
                    self.uyku(5.0)
                    continue
                raise FdorgHatasi(f"bağlantı hatası: {neden}", meta, dur="unnel" in neden)
            bas = govde[:200].lstrip().lower()
            if bas.startswith((b"<!doctype", b"<html")):
                raise FdorgHatasi("JSON yerine HTML geldi; durduruldu", meta, dur=True)
            try:
                veri = json.loads(govde)
            except ValueError as h:
                raise FdorgHatasi(f"JSON çözülemedi: {h}", meta)
            meta["bayt"] = len(govde)
            meta["sha256"] = hashlib.sha256(govde).hexdigest()
            p = self._yol(url)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.with_suffix(".json").write_bytes(govde)
            p.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            return veri, meta


# --- ayrıştırma ---
def _skor(s: dict | None):
    if not isinstance(s, dict):
        return None, None
    return s.get("home"), s.get("away")


def mac_ayristir(m: dict, yarisma_kodu: str | None = None) -> dict:
    """Tek maçı oransız, düz bir kayda çevirir. `odds` alanı hiç okunmaz."""
    sc = m.get("score") or {}
    sure = sc.get("duration")
    ms_ev, ms_dep = _skor(sc.get("fullTime"))
    iy_ev, iy_dep = _skor(sc.get("halfTime"))
    nd_ev, nd_dep = _skor(sc.get("regularTime"))
    if sure == "REGULAR":
        nd_ev, nd_dep = ms_ev, ms_dep
    utc = m.get("utcDate")
    utc_dt = datetime.fromisoformat(utc.replace("Z", "+00:00")) if utc else None
    hakem = next((r.get("name") for r in m.get("referees") or [] if r.get("type") == "REFEREE"), None)
    sezon = m.get("season") or {}
    kayit = {
        "kaynak_id": m.get("id"), "yarisma": yarisma_kodu or (m.get("competition") or {}).get("code"),
        "sezon_baslangic": sezon.get("startDate"), "hafta": m.get("matchday"), "asama": m.get("stage"),
        "grup": m.get("group"), "durum": m.get("status"),
        "utc_baslama": utc_dt.isoformat() if utc_dt else None,
        "tr_baslama": utc_dt.astimezone(TR).isoformat() if utc_dt else None,
        "ev": (m.get("homeTeam") or {}).get("name"), "ev_id": (m.get("homeTeam") or {}).get("id"),
        "ev_kisa": (m.get("homeTeam") or {}).get("shortName"),
        "dep": (m.get("awayTeam") or {}).get("name"), "dep_id": (m.get("awayTeam") or {}).get("id"),
        "dep_kisa": (m.get("awayTeam") or {}).get("shortName"),
        "ms_ev": ms_ev, "ms_dep": ms_dep, "iy_ev": iy_ev, "iy_dep": iy_dep,
        "normal_sure_ev": nd_ev, "normal_sure_dep": nd_dep, "sure_turu": sure,
        "kazanan": sc.get("winner"), "hakem": hakem, "son_guncelleme": m.get("lastUpdated"),
    }
    oransiz_mi(kayit, "fdorg_mac")
    return kayit


def maclari_ayristir(veri: dict) -> list[dict]:
    kod = (veri.get("competition") or {}).get("code")
    out = [mac_ayristir(m, kod) for m in veri.get("matches") or []]
    oransiz_mi(out, "fdorg_maclar")
    return out


def sonuc_kanitlari(maclar: list[dict], meta: dict) -> list[Kanit]:
    """Yalnızca bitmiş (FINISHED) maçlar için 'sonuc' kanıtları. Yayın tarihi = API'nin lastUpdated değeri."""
    out = []
    for m in maclar:
        if m["durum"] != "FINISHED" or m["ms_ev"] is None:
            continue
        deger = {k: m[k] for k in ("ev", "dep", "ms_ev", "ms_dep", "iy_ev", "iy_dep", "normal_sure_ev",
                                    "normal_sure_dep", "sure_turu", "hakem", "utc_baslama", "yarisma", "hafta")}
        out.append(Kanit(
            mac_id=f"fdorg:{m['kaynak_id']}", konu="sonuc",
            iddia=f"{m['ev']} {m['ms_ev']}-{m['ms_dep']} {m['dep']} (İY {m['iy_ev']}-{m['iy_dep']})",
            deger=deger, kaynak_adi="football-data.org", kaynak_url=meta["url"], erisim_zamani=meta["erisim_utc"],
            dogrulama="veri_kaynagi", yayin_tarihi=m["son_guncelleme"],
            olcum_baslangic=(m["utc_baslama"] or "")[:10] or None, olcum_bitis=(m["utc_baslama"] or "")[:10] or None,
            ham_sha256=meta.get("sha256"), notlar=ATIF))
    return out


def yarisma_maclari(istemci: FdorgIstemcisi, kod: str, date_from: str, date_to: str, status: str | None = None,
                    onbellek_sn: float | None = None) -> tuple[list[dict], dict]:
    url = adres("maclar", kod, dateFrom=date_from, dateTo=date_to, status=status)
    if onbellek_sn is None:                 # geçmiş ve bitmiş maçlar seyrek değişir
        bugun = datetime.now(timezone.utc).date()
        gecmis = datetime.fromisoformat(date_to).date() < bugun - timedelta(days=2)
        onbellek_sn = 7 * 86400 if gecmis and status == "FINISHED" else 900
    veri, meta = istemci.getir(url, onbellek_sn)
    return maclari_ayristir(veri), meta
