"""HTML'den yayın zamanı adayları, başlık ve gövde metni — tamamen ağsız, saf fonksiyonlar.

Kenar çubuğu / "ilgili haberler" bölümü ilk işaretçide kesilir: pilotta 2026 tarihli bir yan haberin 2023 maçına
karıştığı görüldü. Görünür tarihler yalnızca kesilmiş gövdenin başından alınır.
"""

from __future__ import annotations

import html
import re

KENAR = re.compile(r"Zurück zur Übersicht|Ähnliche Artikel|Mehr News|Related Articles|Related articles|More news|"
                   r"More from|Read more|You may also like|RELATED:|Noticias relacionadas|También te puede interesar|"
                   r"Más noticias|Leggi anche|Articoli correlati|Potrebbe interessarti|Altre notizie")
META_ANAHTARLARI = ("article:published_time", "og:article:published_time", "datePublished", "pubdate", "publishdate",
                    "article:modified_time", "dateModified")
AY = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11,
      "dec": 12, "ene": 1, "abr": 4, "ago": 8, "dic": 12, "gen": 1, "mag": 5, "giu": 6, "lug": 7, "set": 9, "ott": 10,
      "dez": 12, "mär": 3, "okt": 10, "mai": 5}


def _meta(s: str, anahtar: str) -> str | None:
    k = re.escape(anahtar)
    m = re.search(r'<meta[^>]+(?:property|name|itemprop)\s*=\s*"%s"[^>]*content\s*=\s*"([^"]+)"' % k, s, re.I) or \
        re.search(r'<meta[^>]+content\s*=\s*"([^"]+)"[^>]+(?:property|name|itemprop)\s*=\s*"%s"' % k, s, re.I)
    return m.group(1) if m else None


def zaman_adaylari(s: str) -> dict:
    """{'yayin': [(kaynak, değer)], 'guncelleme': [(kaynak, değer)]} — öncelik sırasıyla."""
    yayin, guncel = [], []
    for k in re.findall(r'"datePublished"\s*:\s*"([^"]+)"', s)[:1]:
        yayin.append(("jsonld", k))
    for a in ("article:published_time", "og:article:published_time", "datePublished", "pubdate", "publishdate"):
        v = _meta(s, a)
        if v:
            yayin.append(("meta", v))
    t = re.search(r'<time[^>]+datetime\s*=\s*"([^"]+)"', s, re.I)
    if t:
        yayin.append(("time_etiketi", t.group(1)))
    for k in re.findall(r'"dateModified"\s*:\s*"([^"]+)"', s)[:1]:
        guncel.append(("jsonld", k))
    for a in ("article:modified_time", "dateModified"):
        v = _meta(s, a)
        if v:
            guncel.append(("meta", v))
    return {"yayin": yayin, "guncelleme": guncel}


def baslik(s: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", s, re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(m.group(1))).strip() if m else None


def govde_metni(s: str) -> tuple[str, bool]:
    """(kenar çubuğu kesilmiş düz metin, kesildi_mi)."""
    g = re.sub(r"<script.*?</script>|<style.*?</style>|<nav.*?</nav>|<footer.*?</footer>|<aside.*?</aside>", " ", s,
               flags=re.S | re.I)
    metin = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", g))).strip()
    k = KENAR.search(metin)
    if k and k.start() > 200:
        return metin[:k.start()].strip(), True
    return metin, False


def _tarihleri_bul(bas: str) -> list[str]:
    out = []
    for g, a, y in re.findall(r"\b(\d{1,2})[./](\d{1,2})[./](20\d\d)\b", bas):
        out.append(f"{y}-{int(a):02d}-{int(g):02d}")
    for g, ay, y in re.findall(r"\b(\d{1,2})\.?\s+(?:de\s+)?([A-Za-zäÄ]{3,10})\.?\s+(?:de\s+)?(20\d\d)\b", bas):
        n = AY.get(ay[:3].casefold())
        if n:
            out.append(f"{y}-{n:02d}-{int(g):02d}")
    return list(dict.fromkeys(out))


def gorunur_tarihler(metin: str, ilk: int = 3000) -> list[str]:
    """Gövdenin başındaki görünür tarihler (geri uyumluluk). Yeni kod makale_tarihleri() kullanır."""
    return _tarihleri_bul(metin[:ilk])


def makale_basligi(s: str) -> str | None:
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S | re.I)
    if h1:
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h1.group(1)))).strip()
        if len(t) >= 8:
            return t
    b = baslik(s)
    if b:
        return re.split(r"\s+[|–—-]\s+", b)[0].strip().strip('"“”') or None
    return None


def makale_tarihleri(s: str, metin: str, once: int = 150, sonra: int = 700) -> tuple[list[str], str]:
    """Makaleye ait görünür tarihler ve bunların nereden alındığı.
    Sıra: (1) <article> etiketinin metni, (2) makale başlığının gövdedeki geçişlerinin çevresi (başlıktan 150 karakter
    önce – 700 karakter sonra; menü uzunluğundan bağımsız), (3) geri dönüş: gövdenin ilk 3000 karakteri.
    Kenar çubuğu zaten `metin`den kesilmiştir; başka tarihli yan haberler bu yüzden karışmaz."""
    a = re.search(r"<article\b[^>]*>(.*?)</article>", s, re.S | re.I)
    if a:
        am = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>",
                                                                                " ", a.group(1), flags=re.S | re.I))))
        t = _tarihleri_bul(am[:3000])
        if t:
            return t, "article_etiketi"
    bas = makale_basligi(s)
    if bas:
        kisa = bas[:60]
        for m in re.finditer(re.escape(kisa), metin):
            if m.start() < 5 and len(metin) > 500:          # <title> metni gövdenin en başında: atla
                continue
            t = _tarihleri_bul(metin[max(0, m.start() - once): m.end() + sonra])
            if t:
                return t, "makale_basligi_cevresi"
    return _tarihleri_bul(metin[:3000]), "ilk_3000_karakter"


def ilgili_cumleler(metin: str, desen: re.Pattern, en_fazla: int = 12) -> list[str]:
    return [c.strip() for c in re.split(r"(?<=[.!?»”\"])\s+", metin) if 30 < len(c) < 400 and desen.search(c)][:en_fazla]


def yalnizca_js_mi(s: str, metin: str) -> bool:
    return len(metin) < 200 and bool(re.search(r"<script", s, re.I))
