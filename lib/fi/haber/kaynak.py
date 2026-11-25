"""Haber kaynağı (host) kaydı ve kullanım koşulu / robots.txt uyum sınıflandırması.

Sınıflar:
  kullanilabilir  : erişilebilir, koşullar özel ve ticari olmayan okumaya izin veriyor, kimlik doğrulandı
  dogrulanmamis   : erişilebilir ve koşullar uygun, ama resmî kulüp kimliği tek işarete dayanıyor
  engelli         : koşullar otomatik erişimi yasaklıyor, robots.txt Claude/Anthropic'i engelliyor ya da sunucu
                    dürüst User-Agent'ı reddediyor (403/406/bot doğrulaması) — ASLA okunmaz, aşılmaz
  belirsiz        : koşullar okunamadı/bulunamadı, içerik yalnızca JavaScript, yanıt yok

Okuyucu yalnızca 'kullanilabilir' hostlara istek atar. İzin listesine ekleme/çıkarma bu modülün işi DEĞİLDİR;
kullanıcı onayıyla ortam ayarından yapılır.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

SINIFLAR = ("kullanilabilir", "dogrulanmamis", "engelli", "belirsiz")
TURLER = ("resmi_kulup", "resmi_lig", "resmi_federasyon", "ulusal_basin", "yerel_basin", "veri_kaynagi")
KAYIT_DOSYASI = Path(__file__).resolve().parents[3] / "veri" / "haber_kaynaklari.json"
AI_AJANLARI = {"claudebot", "claude-web", "claude-searchbot", "claude-user", "anthropic-ai", "anthropiccrawler"}
YASAK_HOSTLAR = {"cdnbulten.nesine.com", "bulten.nesine.com", "www.nesine.com", "nesine.com"}

# Kullanım koşullarında otomatik erişim yasağı (en, de, es, it). Yalnızca açık yasak ifadeleri; telif uyarısı değil.
OTOMATIK_YASAK = re.compile(
    r"(scrap(?:e|ing)|crawl(?:er|ing)|spiders?|web crawlers?|"
    r"automated (?:programmes|programs|scripts|means|tools)|bots?,? (?:or )?(?:spiders|similar)|"
    r"text and data mining|data mining|"
    r"automatisiert\w* (?:zugriff|abruf)|bots? oder ähnlich|text- und data-mining|"
    r"secuencias de comandos automatizad\w*|screen scraping|recuperar datos de forma sistem\w*|"
    r"strumenti automatic\w*|estrazione (?:automatica|di dati)|text and data mining)", re.I)
YASAK_FIIL = re.compile(r"(may not|must not|shall not|not permitted|prohibited|forbidden|reserves? the right|"
                        r"dürfen nicht|nicht gestattet|untersagt|vorbehalten|"
                        r"prohibid\w*|no (?:está|esta) permitid\w*|abstenerse|"
                        r"vietat\w*|non è consentit\w*|è esclus\w*|"
                        r"you agree not|for extracting|utilizar|it is forbidden)", re.I)


class KaynakHatasi(ValueError):
    pass


@dataclass
class HostKaydi:
    host: str
    tur: str
    sinif: str
    gerekce: str
    lig: str | None = None
    kulup: str | None = None
    yayinci_grubu: str | None = None          # aynı gruptaki siteler bağımsız teyit sayılmaz
    kimlik_isaretleri: list = field(default_factory=list)   # ör. ["wikipedia", "ana_sayfa_basligi"]
    kosul_url: str | None = None
    kosul_ozeti: str | None = None
    robots_ai_engeli: bool | None = None
    kontrol_utc: str | None = None

    def dogrula(self) -> "HostKaydi":
        if self.host.casefold() in YASAK_HOSTLAR:
            raise KaynakHatasi("Nesine / bahis hostu haber kaynağı olamaz (MK-1)")
        if self.sinif not in SINIFLAR:
            raise KaynakHatasi(f"geçersiz sınıf: {self.sinif}")
        if self.tur not in TURLER:
            raise KaynakHatasi(f"geçersiz tür: {self.tur}")
        if not self.gerekce.strip():
            raise KaynakHatasi("sınıf gerekçesi boş olamaz")
        if self.sinif == "kullanilabilir" and self.tur == "resmi_kulup" and len(set(self.kimlik_isaretleri)) < 2:
            raise KaynakHatasi(f"{self.host}: resmî kulüp sitesi iki kimlik işareti olmadan 'kullanilabilir' olamaz")
        return self


class KaynakKaydi:
    def __init__(self, kayitlar: list[HostKaydi]):
        self.kayitlar = {k.host: k.dogrula() for k in kayitlar}

    @classmethod
    def yukle(cls, yol: Path = KAYIT_DOSYASI) -> "KaynakKaydi":
        d = json.loads(Path(yol).read_text(encoding="utf-8"))
        return cls([HostKaydi(**x) for x in d["hostlar"]])

    def kaydet(self, yol: Path = KAYIT_DOSYASI, aciklama: str = "") -> None:
        Path(yol).write_text(json.dumps({"aciklama": aciklama, "hostlar": [asdict(k) for k in self.kayitlar.values()]},
                                        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def get(self, host: str) -> HostKaydi | None:
        return self.kayitlar.get((host or "").casefold())

    def okunabilir_mi(self, host: str) -> bool:
        k = self.get(host)
        return bool(k) and k.sinif == "kullanilabilir"

    def sinifa_gore(self) -> dict[str, list[str]]:
        out = {s: [] for s in SINIFLAR}
        for k in self.kayitlar.values():
            out[k.sinif].append(k.host)
        return out


def robots_ai_engeli(robots_txt: str, ajanlar=AI_AJANLARI) -> bool:
    """robots.txt'te bizi kapsayan bir yapay zekâ ajanı grubu (ya da '*') için 'Disallow: /' var mı?
    İhtiyatlı ayrıştırma: arka arkaya User-agent satırları tek grup sayılır ve boş satır, kurallardan önce geliyorsa
    grubu bitirmez (bazı sitelerde yaygın yazım hatası; niyet engellemektir)."""
    grup: list[str] = []
    kural_goruldu = False
    for ham in robots_txt.splitlines():
        satir = ham.split("#", 1)[0].strip()
        if not satir:
            continue
        m = re.match(r"(?i)user-agent\s*:\s*(.+)", satir)
        if m:
            if kural_goruldu:
                grup, kural_goruldu = [], False
            grup.append(m.group(1).strip().casefold())
            continue
        r = re.match(r"(?i)(dis)?allow\s*:\s*(.*)", satir)
        if r:
            kural_goruldu = True
            if r.group(1) and r.group(2).strip() == "/" and any(a in ajanlar for a in grup):
                return True
    return False


def kosul_otomatik_yasak(metin: str) -> list[str]:
    """Koşul metninde otomatik erişimi açıkça yasaklayan cümleler (aynı cümlede yasak fiili ve otomasyon ifadesi)."""
    out = []
    for c in re.split(r"(?<=[.;:])\s+", re.sub(r"\s+", " ", metin)):
        if OTOMATIK_YASAK.search(c) and YASAK_FIIL.search(c):
            out.append(c.strip()[:400])
    return out


def siniflandir(*, ana_http: int | None, robots_ai: bool | None, bot_isareti: bool, icerik_js: bool,
                kosul_okundu: bool, kosul_yasaklari: list[str], kimlik_isaret_sayisi: int, tur: str) -> tuple[str, str]:
    """Uyum taraması sonuçlarından sınıf + gerekçe. Sıra: engel > belirsiz > kimlik > kullanılabilir."""
    if ana_http in (401, 403, 406, 429, 451):
        return "engelli", f"sunucu dürüst User-Agent'ı reddediyor (HTTP {ana_http})"
    if bot_isareti:
        return "engelli", "bot doğrulaması / erişim engeli işareti"
    if robots_ai:
        return "engelli", "robots.txt Claude/Anthropic ajanları için Disallow: /"
    if kosul_yasaklari:
        return "engelli", "kullanım koşulları otomatik erişimi yasaklıyor: " + kosul_yasaklari[0][:200]
    if ana_http is None or ana_http >= 500:
        return "belirsiz", "yanıt yok ya da sunucu hatası"
    if icerik_js:
        return "belirsiz", "içerik yalnızca JavaScript ile oluşuyor (tarayıcı taklidi yapılmaz)"
    if not kosul_okundu:
        return "belirsiz", "kullanım koşulları okunamadı ya da bulunamadı"
    if tur == "resmi_kulup" and kimlik_isaret_sayisi < 2:
        return "dogrulanmamis", "resmî kulüp kimliği tek işarete dayanıyor"
    return "kullanilabilir", "erişilebilir; koşullarda otomatik okuma yasağı yok; kimlik doğrulandı"
