"""Resmî kulüp sitesi keşfi ve iki işaretle kimlik doğrulama.

İşaret W: Wikipedia kulüp maddesinin bilgi kutusu `website` alanı ya da {{Official website}} şablonu. Wikipedia
          tek başına güvenilir kabul EDİLMEZ; {{Official URL}} Wikidata'dan çektiği için çözülmeden 'wikidata' döner.
İşaret S: sitenin kendi ana sayfa başlığı kulübün adını taşır.
Durum: dogrulandi (W ve S aynı kayıtlı alan adını gösterir) | tek_isaret | dogrulanamadi.
Ağ işlemi yoktur: metinler çağıran tarafından (kaynak kaydındaki okunabilir hostlardan / Wikipedia'dan) verilir.
"""

from __future__ import annotations

import re
import unicodedata
import urllib.parse

GENEL_SOZCUKLER = {"fc", "cf", "afc", "sc", "ac", "as", "ss", "us", "ssc", "cd", "ca", "club", "calcio", "football",
                   "fussball", "futbol", "the", "of", "and", "de", "del", "1899", "1909", "1919", "1910", "04", "98",
                   "1907", "1913", "e", "v", "s", "a", "f", "c", "tsg", "vfl", "rcd", "sv", "fk", "ud", "real"}


def _sade(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9 ]", " ", s.replace("&", " and "))


def kayitli_alan(host_ya_da_url: str) -> str:
    """'https://www.fcbarcelona.com/en/' → 'fcbarcelona.com' (basit eTLD+1; .co.uk gibi iki parçalı sonekler dahil)."""
    h = urllib.parse.urlparse(host_ya_da_url if "//" in host_ya_da_url else "//" + host_ya_da_url).hostname or ""
    p = h.casefold().split(".")
    if len(p) >= 3 and p[-2] in {"co", "com", "org", "net", "ac"} and len(p[-1]) == 2:
        return ".".join(p[-3:])
    return ".".join(p[-2:])


def wikipedia_websitesi(wikitext: str) -> str | None:
    """Bilgi kutusu website alanı / {{Official website}} → alan adı; {{Official URL}} → 'wikidata'; yoksa None."""
    bas = wikitext[: wikitext.find("\n}}") + 3] if "\n}}" in wikitext else wikitext[:10000]
    m = re.search(r"^\|\s*website\s*=\s*(.+)$", bas, re.M)
    adaylar = []
    if m:
        v = m.group(1)
        if re.search(r"\{\{\s*official url\s*\}\}", v, re.I):
            return "wikidata"
        adaylar += re.findall(r"https?://[^\s|\]}]+", v)
        adaylar += [x.strip() for x in re.findall(r"\{\{\s*URL\s*\|\s*([^|}]+)", v, re.I)]
    if not adaylar:
        for x in re.findall(r"\{\{\s*[Oo]fficial website\s*\|\s*(?:url\s*=\s*)?([^}|]+)", wikitext):
            if "." in x and "store." not in x and "shop." not in x:
                adaylar.append(x.strip())
    for a in adaylar:
        a = a.strip()
        if "." in a:
            return kayitli_alan(a)
    return None


def baslik_kulubu_adlandiriyor_mu(baslik: str | None, kulup_adi: str) -> bool:
    """Başlıkta kulübün ayırt edici sözcüklerinden en az biri (genel sözcükler hariç) geçiyor mu?"""
    if not baslik:
        return False
    b = set(_sade(baslik).split())
    ayirt = [w for w in _sade(kulup_adi).split() if w not in GENEL_SOZCUKLER and len(w) > 2]
    return bool(ayirt) and any(w in b for w in ayirt)


def alan_adi_durumu(host: str, wikipedia_alan: str | None, ana_sayfa_basligi: str | None, kulup_adi: str) -> dict:
    isaretler = []
    if wikipedia_alan and wikipedia_alan != "wikidata" and wikipedia_alan == kayitli_alan(host):
        isaretler.append("wikipedia")
    celiski = bool(wikipedia_alan and wikipedia_alan != "wikidata" and wikipedia_alan != kayitli_alan(host))
    if baslik_kulubu_adlandiriyor_mu(ana_sayfa_basligi, kulup_adi):
        isaretler.append("ana_sayfa_basligi")
    if celiski:
        durum = "dogrulanamadi"
    elif len(isaretler) == 2:
        durum = "dogrulandi"
    elif len(isaretler) == 1:
        durum = "tek_isaret"
    else:
        durum = "dogrulanamadi"
    return {"host": host, "durum": durum, "isaretler": isaretler, "wikipedia": wikipedia_alan, "celiski": celiski}
