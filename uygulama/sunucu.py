"""Football Intelligence V1 — yerel web arayüzü (yalnızca standart kütüphane; paket kurulumu gerekmez).

Çalıştırma (depo kökünden):  PYTHONPATH=lib python3 -m uygulama [--port 8765]
Sonra tarayıcıda http://127.0.0.1:8765 açılır. Sunucu yalnızca 127.0.0.1'e bağlanır.

Sayfalar: /  günün maçları · /mac/<kod> maç analizi · /arsiv tahmin arşivi · /arastirma/surpriz sürpriz araştırması
"""
from __future__ import annotations

import argparse
import html
import json
import os
import threading
import re
import time
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

from . import guvenlik as G
from . import islemler as IS
from . import yedek as Y
from . import veri as V
from fi import is_akisi as I

E = html.escape

CSS = """
:root{--bg:#f6f7f9;--kart:#fff;--yazi:#1d2330;--soluk:#5d6678;--cizgi:#dde1e8;--vurgu:#1f5fbf;--iyi:#1d7a46;--uyari:#a35c00;--kotu:#b3261e;--kilit:#6b5aa8}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--kart:#1c2027;--yazi:#e6e9ef;--soluk:#9aa3b2;--cizgi:#2e3440;--vurgu:#7aa7f0;--iyi:#5cc98a;--uyari:#e0a050;--kotu:#f08a80;--kilit:#b3a6e8}}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--yazi)}
header{background:var(--kart);border-bottom:1px solid var(--cizgi);padding:10px 16px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
header b{font-size:16px}header a{color:var(--yazi);text-decoration:none}header a:hover{color:var(--vurgu)}
main{max-width:1180px;margin:0 auto;padding:16px}
.kart{background:var(--kart);border:1px solid var(--cizgi);border-radius:8px;padding:14px 16px;margin:0 0 14px}
h1{font-size:21px;margin:4px 0 12px}h2{font-size:17px;margin:0 0 10px}h3{font-size:15px;margin:12px 0 6px}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid var(--cizgi);padding:5px 7px;text-align:left;vertical-align:top}
th{color:var(--soluk);font-weight:600}td.s,th.s{text-align:right;font-variant-numeric:tabular-nums}
.rozet{display:inline-block;padding:1px 7px;border-radius:10px;font-size:12px;border:1px solid currentColor;white-space:nowrap}
.iyi{color:var(--iyi)}.uyari{color:var(--uyari)}.kotu{color:var(--kotu)}.kilit{color:var(--kilit)}.soluk{color:var(--soluk)}
a{color:var(--vurgu)}.not{font-size:13px;color:var(--soluk)}
nav.ic a{margin-right:12px;font-size:14px}
.izgara{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.md table{margin:6px 0 10px}.md pre{white-space:pre-wrap}
form.satir{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:0}
select,button,input{font:inherit;padding:4px 8px;border:1px solid var(--cizgi);border-radius:6px;background:var(--kart);color:var(--yazi)}
button{cursor:pointer;border-color:var(--vurgu);color:var(--vurgu);min-height:36px}
@media (max-width:600px){main{padding:10px}.kart{padding:12px}header{gap:10px;padding:8px 12px}table{font-size:13px}h1{font-size:19px}}
.giris{max-width:360px;margin:40px auto}.giris input{width:100%;margin:4px 0 10px;padding:8px}
.tasma{overflow-x:auto}
"""


_IST = threading.local()          # istek başına: CSRF jetonu, giriş yapılmış mı


def sayfa(baslik: str, govde: str) -> str:
    girisli = getattr(_IST, "kullanici", None)
    ust = ("<a href='/'>Günün maçları</a><a href='/arsiv'>Tahmin arşivi</a><a href='/arastirma/surpriz'>Sürpriz araştırması</a>"
           "<a href='/yonetim'>Yedek ve depolama</a>" if girisli or not G.bulut_mu() else "")
    cikis = dugme("/cikis", "Çıkış") if girisli and G.bulut_mu() else ""
    uyari = ""
    if G.bulut_mu() and girisli and os.environ.get("FI_KALICI_DEPOLAMA") != "1":
        uyari = ("<div class='kart kotu'><b>Geçici depolama:</b> Bu sunucunun diski kalıcı değil. Yeniden başlatma, "
                 "uyku ya da yeni dağıtımda dondurulmuş tahminler ve kayıtlar silinir. <a href='/yonetim'>Yedeği indirin</a>.</div>")
    return (f"<!doctype html><html lang='tr'><head><meta charset='utf-8'><meta name='viewport' "
            f"content='width=device-width,initial-scale=1'><meta name='apple-mobile-web-app-capable' content='yes'>"
            f"<title>{E(baslik)} · Football Intelligence</title>"
            f"<style>{CSS}</style></head><body><header><b>Football Intelligence V1</b>{ust}"
            f"<span class='not'>TR saati: {V.simdi_tr():%d.%m.%Y %H:%M}</span>{cikis}</header><main>{uyari}{govde}</main></body></html>")


def dugme(yol: str, etiket: str, aciklama: str = "", gizli: dict | None = None) -> str:
    gizli = {**(gizli or {}), **({"csrf": _IST.csrf} if getattr(_IST, "csrf", None) else {})}
    alan = "".join(f"<input type='hidden' name='{E(k)}' value='{E(v)}'>" for k, v in gizli.items())
    return (f"<form method='post' action='{E(yol)}' class='satir' style='display:inline-flex'>{alan}"
            f"<button>{E(etiket)}</button><span class='not'>{E(aciklama)}</span></form>")


def rozet(metin: str, sinif: str) -> str:
    return f"<span class='rozet {sinif}'>{E(metin)}</span>"


def yuzde(p) -> str:
    return f"%{100 * p:.1f}".replace(".", ",") if isinstance(p, (int, float)) else E(str(p))


def tr_saat(iso: str | None) -> str:
    if not iso:
        return "—"
    return datetime.fromisoformat(iso).astimezone(I.TR).strftime("%d.%m %H:%M")


# ------------------------------------------------------------------------------------------------ küçük Markdown
def md(metin: str) -> str:
    """Raporlar için yeterli küçük Markdown dönüştürücü (başlık, tablo, liste, kalın, kod)."""
    def satir_ici(s):
        s = E(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
        return re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"<a href='\2' rel='noreferrer'>\1</a>", s)
    out, i, sat = [], 0, metin.splitlines()
    while i < len(sat):
        s = sat[i]
        if s.startswith("|") and i + 1 < len(sat) and re.fullmatch(r"\|?[\s:|-]+\|?", sat[i + 1].strip()):
            bas = [h.strip() for h in s.strip().strip("|").split("|")]
            i += 2
            govde = []
            while i < len(sat) and sat[i].startswith("|"):
                govde.append([c.strip() for c in sat[i].strip().strip("|").split("|")])
                i += 1
            out.append("<div class='tasma'><table><tr>" + "".join(f"<th>{satir_ici(h)}</th>" for h in bas) + "</tr>"
                       + "".join("<tr>" + "".join(f"<td>{satir_ici(c)}</td>" for c in r) + "</tr>" for r in govde)
                       + "</table></div>")
            continue
        m = re.match(r"(#{1,4})\s+(.*)", s)
        if m:
            seviye = min(len(m.group(1)) + 1, 4)
            out.append(f"<h{seviye}>{satir_ici(m.group(2))}</h{seviye}>")
        elif re.match(r"\s*([-*]|\d+\.)\s+", s):
            liste = []
            while i < len(sat) and re.match(r"\s*([-*]|\d+\.)\s+", sat[i]):
                girinti = len(sat[i]) - len(sat[i].lstrip())
                liste.append(f"<li style='margin-left:{girinti * 8}px'>"
                             f"{satir_ici(re.sub(r'^\s*([-*]|\d+\.)\s+', '', sat[i]))}</li>")
                i += 1
            out.append("<ul>" + "".join(liste) + "</ul>")
            continue
        elif s.strip() == "---":
            out.append("<hr>")
        elif s.strip():
            out.append(f"<p>{satir_ici(s)}</p>")
        i += 1
    return "<div class='md'>" + "\n".join(out) + "</div>"


# ------------------------------------------------------------------------------------------------ sayfalar
def ana_sayfa(sorgu: dict) -> str:
    bl = V.bultenler()
    if not bl:
        return sayfa("Günün maçları", "<div class='kart'>Bülten yok. Önce bülten çekin.</div>")
    bugun_tr = V.simdi_tr().date().isoformat()
    istenen_gun = sorgu.get("gun", [None])[0] or bugun_tr
    # açıkça seçilmediyse: istenen günü (varsayılan bugün) tam kapsayan en yeni bülten; yoksa en yeni bülten
    secili = next((b for b in bl if b.name == sorgu.get("bulten", [""])[0]), None) or \
        next((b for b in bl if istenen_gun in V.bulten_gunleri(b)), bl[0])
    gunler = V.bulten_gunleri(secili)
    bugun = V.simdi_tr().date().isoformat()
    istenen = sorgu.get("gun", [None])[0]
    if not gunler:
        return sayfa("Günün maçları", "<div class='kart uyari'>Bu bülten hiçbir günü tam kapsamıyor. Yeni bülten çekin.</div>")
    if istenen and istenen not in gunler:
        gecerli = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", istenen))
        dg = dugme("/islem/bulten", f"{istenen} bültenini çek", "yalnızca o gün 00:00–23:59", {"gun": istenen}) if gecerli else ""
        return sayfa("Günün maçları", f"<div class='kart uyari'><h2>Bu gün seçilemez</h2><p>{E(istenen)} bu bültende tam "
                     f"kapsanmıyor (bülten penceresi o günün tamamını içermiyor). Kapsanan günler: {E(', '.join(gunler))}. "
                     f"O gün için yeni bülten çekin.</p>{dg}<p><a href='/'>Geri dön</a></p></div>")
    gun = istenen or (bugun if bugun in gunler else gunler[0])
    bilgi = V.bulten_bilgisi(secili)
    maclar = V.gunun_maclari(secili, gun)
    disarida = V.gun_disi_maclar(secili, gun)
    donmus = {k["mac_id"] for k in V.donmus_tahminler()}
    lig_onbellek: dict = {}
    satirlar = []
    for m in maclar:
        h = lig_onbellek[m["mac_id"]] = V.hazirlik_ozeti(m)
        if m["mac_id"] in donmus:
            d = rozet("dondurulmuş", "iyi")
        elif h["durum"] == "hazirlanabilir":
            d = rozet("hazırlanabilir", "uyari")
        elif h["durum"] == "takim_onayi_gerekli":
            d = f"<span class='soluk' title='{E(h['neden'])}'>takım onayı gerekli</span>"
        else:
            d = f"<span class='soluk' title='{E(h['neden'])}'>hesaplanamaz</span>"
        satirlar.append(f"<tr><td>{tr_saat(m['baslama_tr'])}</td><td>{E(m['lig'] or '')}</td>"
                        f"<td><a href='/mac/{m['kod']}'>{E(m['karsilasma'] or '')}</a></td><td>{d}</td></tr>")
    sec_b = "".join(f"<option value='{b.name}'{' selected' if b == secili else ''}>{b.name}</option>" for b in bl)
    sec_g = "".join(f"<option{' selected' if g == gun else ''}>{g}</option>" for g in gunler)
    hazir = sum(1 for m in maclar if lig_onbellek[m["mac_id"]]["durum"] == "hazirlanabilir")
    govde = (f"<h1>Günün maçları — {E(gun)} (Türkiye saati)</h1><div class='kart'><form class='satir'>"
             f"<label>Bülten <select name='bulten'>{sec_b}</select></label>"
             f"<label>Gün <select name='gun'>{sec_g}</select></label><button>Göster</button></form>"
             f"<p>{dugme('/islem/bulten', f'{gun} bültenini çek', 'Nesine maç öncesi, yalnızca o gün 00:00–23:59 TR; tek istek', {'gun': gun})} "
             f"{dugme('/islem/guncel', 'Güncel veri çek', 'football-data.org, 9 yarışma')}</p>"
             f"<p class='not'>Bülten çekimi {E(bilgi['cekim_tr'] or '')} · SHA-256 {E((bilgi['sha256'] or '')[:12])}… · "
             f"{len(maclar)} maç · bağımsız olasılık hazırlanabilir: {hazir}. Bu listede oran gösterilmez (MK-1).</p>"
             f"<p class='not'>Gün kuralı: yalnızca {E(gun)} 00:00–23:59 (TR) arasında başlayan maçlar. Ertesi gün 00:00–03:00 "
             f"arasındaki {disarida} maç bu güne dahil edilmedi; o maçlar kendi günlerinde analiz edilir.</p></div>"
             "<div class='kart tasma'><table><tr><th>Saat</th><th>Lig</th><th>Maç</th><th>Bağımsız tahmin</th></tr>"
             + "".join(satirlar) + "</table></div>")
    return sayfa("Günün maçları", govde)


def _takim_adlari(mac: dict, donmus: dict | None, hz: dict) -> dict:
    """Son maç tablosu için kaynak takım adları: yalnızca donmuş tahmindeki kesin/onaylı eşleme ya da
    football-data.org adaylarıyla kesin/onaylı eşleşme."""
    if donmus:
        t = donmus.get("tahmin") or {}
        ad = {taraf: (t.get(f"{taraf}_esleme") or {}).get("kaynak_adi") for taraf in ("ev", "dep")}
        if all(ad.values()):
            return ad
    lig = hz.get("kaynak_lig")
    if not lig or lig not in V.FD_KODU:
        return {}
    from fi.takim_adlari import TakimEslestirici
    adaylar = set()
    for k in V.guncel_klasorleri():
        y = k / f"{V.FD_KODU[lig]}.json"
        if y.exists():
            adaylar = {x for m in V._json(y) for x in (m["ev"], m["dep"])}
            break
    E_ = TakimEslestirici()
    out = {}
    for taraf, ad in (("ev", mac["ev"]), ("dep", mac["deplasman"])):
        e = E_.eslestir(ad, f"football-data.org:{lig}", sorted(adaylar))
        if e.kullanilabilir:
            out[taraf] = e.kaynak_adi
    return out


def _son_maclar_html(baslik: str, s: dict) -> str:
    if not s.get("satirlar"):
        return f"<div><h3>{E(baslik)}</h3><p class='not'>{E(s.get('neden') or 'veri yok')}</p></div>"
    o = s["ozet"]
    n = s["mac"]
    sat = "".join(f"<tr><td>{E(r['tarih_tr'])}</td><td>{r['saha']}</td><td>{E(r['rakip'])}</td>"
                  f"<td class='s'>{r['skor']}</td><td class='s soluk'>{E(r['iy'] or '—')}</td>"
                  f"<td class='{ {'G': 'iyi', 'B': 'uyari', 'M': 'kotu'}[r['sonuc']] }'>{r['sonuc']}</td></tr>"
                  for r in s["satirlar"])
    return (f"<div><h3>{E(baslik)}</h3><p>Son {n}: {o['G']}G {o['B']}B {o['M']}M · gol {o['atilan']}–{o['yenilen']} · "
            f"KG {o['kg']}/{n} · 2,5 Üst {o['ust25']}/{n}</p><div class='tasma'><table><tr><th>Tarih (TR)</th><th>Saha</th>"
            f"<th>Rakip</th><th class='s'>Skor</th><th class='s'>İY</th><th></th></tr>{sat}</table></div>"
            f"<p class='not'>Kaynak: {E(s['kaynak'])}, anlık görüntü {E(s['anlik_goruntu'])} (UTC).</p></div>")


def _iddia_tablosu(liste: list) -> str:
    if not liste:
        return "<p class='not'>Kayıt yok.</p>"
    sinif = {"resmi": "iyi", "iki_bagimsiz": "iyi", "dogrulanmadi": "uyari", "celiskili": "kotu"}
    sat = []
    for x in liste:
        dg = x.get("dogrulama") or ""
        sat.append(f"<tr><td>{E(str(x.get('konu') or ''))}</td><td>{E(str(x.get('takim') or ''))}</td>"
                   f"<td>{E(str(x.get('kisi') or ''))}</td><td>{rozet(dg, sinif.get(dg, 'soluk'))}</td>"
                   f"<td>{'<br>'.join(E(o) for o in x.get('ozetler') or [])}</td>"
                   f"<td class='s'>{E(str(x.get('zincir_sayisi', '')))}</td></tr>")
    return ("<div class='tasma'><table><tr><th>Konu</th><th>Takım</th><th>Kişi</th><th>Doğrulama</th><th>Özet</th>"
            "<th class='s'>Zincir</th></tr>" + "".join(sat) + "</table></div>")


def _ev_sinifi(s: dict) -> str:
    ev = s.get("beklenen_deger")
    if ev is None:
        return "<span class='soluk'>hesaplanmadı</span>"
    if ev > 0:
        return (rozet("model–piyasa ayrışması · doğrulama gerekli", "uyari")
                + " <a href='#raporlar' class='not'>raporlar</a>")
    return "<span class='soluk'>piyasa fiyatı modelin üstünde değil</span>"


def _tur_bilgisi(mac: dict) -> str:
    from fi.haber.genis import GenisHata, arastirma_turu
    from datetime import timezone
    try:
        b = datetime.fromisoformat(mac["baslama_tr"]).astimezone(timezone.utc).isoformat()
        return f"Şu anki araştırma turu: {arastirma_turu(b, datetime.now(timezone.utc))}."
    except GenisHata:
        return "Maç başladı: maç öncesi araştırma kapandı."


def _host(url: str) -> str:
    return urlparse(url).netloc.removeprefix("www.") or url[:40]


def _skor_p(beklenen, olasiliklar: dict) -> str:
    """Analistin skor beklentisini donmuş modeldeki aynı skorun olasılığıyla yan yana koyar (model değişmez)."""
    m = re.search(r"(\d+)\s*-\s*(\d+)", str(beklenen or ""))
    if not m:
        return "—"
    ad = f"skor_{m.group(1)}_{m.group(2)}"
    if ad in olasiliklar:
        return yuzde(olasiliklar[ad])
    return "hesaplanamaz" if olasiliklar else "—"


def mac_sayfasi(kod: int) -> str:
    mac, klasor = V.mac_bul(kod)
    donmus = V.donmus_bul(kod)
    if mac is None and donmus is None:
        return sayfa("Maç bulunamadı", f"<div class='kart uyari'><h2>Maç bulunamadı</h2><p>Nesine {kod} kayıtlı hiçbir "
                     "bültende ve tahmin arşivinde yok. <a href='/'>Günün maçlarına dön</a>.</p></div>")
    mac = mac or {"kod": kod, "karsilasma": donmus.get("karsilasma"), "lig": donmus.get("lig"),
                  "baslama_tr": donmus.get("baslama_tr"), "ev": "", "deplasman": ""}
    hz = V.hazirlik_ozeti(mac)
    p = []
    p.append(f"<h1>{E(mac['karsilasma'] or '')}</h1><p>{E(mac.get('lig') or '')} · {tr_saat(mac['baslama_tr'])} TR · "
             f"Nesine {kod}" + (f" · bülten {E(klasor.name)}" if klasor else "") + "</p>"
             "<nav class='ic'><a href='#veri'>Sportif veri</a><a href='#olasilik'>Bağımsız olasılıklar</a>"
             "<a href='#haber'>Haberler</a><a href='#analist'>Analistler</a><a href='#surpriz'>Sürpriz riskleri</a>"
             "<a href='#fiyat'>Fiyat karşılaştırması</a><a href='#raporlar'>Raporlar</a></nav>")

    # 1. hazırlık kapısı
    if donmus and not donmus.get("hata"):
        t = donmus["tahmin"]
        hk = "".join(f"<tr><td>{'✔' if h['gecti'] else '✘'}</td><td>{E(h['kriter'])}</td><td>{E(str(h['kanit']))}</td></tr>"
                     for h in t.get("hazirlik", []))
        ust = (f"{rozet('dondurulmuş', 'iyi')} {E(donmus['dondurma_utc'])} UTC · SHA-256 <code>{E(donmus['sha256'][:16])}…</code>"
               f" doğrulandı · veri kesimi {E(str(donmus.get('veri_kesimi')))} · model {E(t.get('model_adi') or '')} · "
               f"commit {E(str((donmus.get('model_surumu') or {}).get('git_commit') or '')[:7])}")
        p.append(f"<div class='kart'><h2>Hazırlık kapısı</h2><p>{ust}</p><details><summary>Kriterler ({len(t.get('hazirlik', []))})"
                 f"</summary><table>{hk}</table></details></div>")
    elif donmus:
        p.append(f"<div class='kart kotu'><h2>Donmuş tahmin bozuk</h2>{E(donmus['hata'])}</div>")
    else:
        p.append(f"<div class='kart'><h2>Hazırlık kapısı</h2><p>{rozet(hz['durum'], 'uyari' if hz['durum'] == 'hazirlanabilir' else 'soluk')}"
                 f" {E(hz['neden'])}</p><p class='not'>Lig: {E(str(hz['kaynak_lig']))} · modeller: {E(', '.join(hz['modeller']) or '—')}"
                 "</p>" + (dugme(f"/islem/dondur/{kod}", "Bağımsız tahmini hesapla ve dondur",
                                 "güncel veri çekilir; oranlar açılmadan SHA-256 ile dondurulur")
                           if hz["durum"] == "hazirlanabilir" else "") + "</div>")

    # 2. sportif veri (son maçlar)
    adlar = _takim_adlari(mac, donmus if donmus and not donmus.get("hata") else None, hz)
    if adlar and hz.get("kaynak_lig"):
        bloklar = "".join(_son_maclar_html(f"{E(mac.get('ev') or '')} → {adlar[t]}" if t in adlar else t,
                                           V.son_maclar(hz["kaynak_lig"], adlar[t], 10) if t in adlar else {"neden": "takım eşlemesi yok"})
                          for t in ("ev", "dep"))
        p.append(f"<div class='kart' id='veri'><h2>Güncel sportif veri — son 10 maç</h2><div class='izgara'>{bloklar}</div></div>")
    else:
        p.append("<div class='kart' id='veri'><h2>Güncel sportif veri</h2><p class='not'>Onaylı lig/takım eşlemesi olmadığı "
                 "için kaynak veri gösterilmiyor (veri yok).</p></div>")

    # 3. bağımsız olasılıklar
    if donmus and not donmus.get("hata") and (donmus["tahmin"] or {}).get("olasiliklar"):
        t = donmus["tahmin"]
        sat = "".join(f"<tr><td>{E(k)}</td><td class='s'>{yuzde(v)}</td></tr>" for k, v in t["olasiliklar"].items())
        hes = "".join(f"<tr><td>{E(k)}</td><td class='not'>{E('; '.join(map(str, v)))}</td></tr>"
                      for k, v in (t.get("hesaplanamaz_pazarlar") or {}).items())
        p.append(f"<div class='kart' id='olasilik'><h2>Bağımsız olasılıklar (donmuş, yalnızca kalibre marketler)</h2>"
                 f"<p>λ ev {t['lambda_ev']:.3f} · λ dep {t['lambda_dep']:.3f} · eğitim {t.get('egitim_mac_sayisi')} maç · "
                 f"{E(t.get('model') or '')}</p><div class='izgara'><div><table><tr><th>Market</th><th class='s'>Olasılık</th></tr>{sat}"
                 f"</table></div><div><h3>Hesaplanamaz ({len(t.get('hesaplanamaz_pazarlar') or {})})</h3><details><summary>"
                 f"Nedenler</summary><table>{hes}</table></details><p class='not'>{E(t.get('kalibrasyon_notu') or '')}</p>"
                 "<p class='not'>“Yüksek güven” verilmez. Olasılıklar oranlardan bağımsızdır ve dondurulduktan sonra değişmez.</p>"
                 "</div></div></div>")
    else:
        p.append("<div class='kart' id='olasilik'><h2>Bağımsız olasılıklar</h2><p class='not'>Donmuş tahmin yok → olasılık "
                 "gösterilmez. Kalibrasyonu başarısız marketlerde hiçbir zaman olasılık üretilmez.</p></div>")

    # 4-5. haberler ve analistler
    hr = V.haber_raporlari(kod)
    if hr:
        r = hr[0]["rapor"]
        surumler = ", ".join(E(x["surum"]) for x in hr)
        tz = V.haber_tazeligi(r, mac["baslama_tr"])
        if tz["guncel"]:
            taz = rozet(f"{tz['simdiki_tur']} turu için araştırıldı · {tz['yas_saat']} saat önce", "iyi")
        else:
            taz = rozet("GÜNCEL DEĞİL", "kotu") + E(f" Son araştırma {tz['yas_saat']} saat önce ({', '.join(tz['turlar'])} turu); "
                                                    f"şu anki tur: {tz['simdiki_tur']}. Bu haberler o anki durumu yansıtır.")
        basin = "".join(f"<tr><td>{E(b.get('sinif') or '')}</td><td>{E(b.get('ozet') or '')}</td>"
                        f"<td>{E(b.get('yayin') or 'yayın zamanı yok')}</td>"
                        f"<td><a href='{E(b.get('kaynak') or '')}' rel='noreferrer'>{E(_host(b.get('kaynak') or ''))}</a></td></tr>"
                        for b in r.get("3_basin_gorusleri") or [])
        sinif = {"resmi": "iyi", "iki_bagimsiz": "iyi", "dogrulanmadi": "uyari", "celiskili": "kotu"}
        idd = "".join(
            f"<tr><td>{tr_saat(i.get('arastirma_utc'))}</td><td>{E(i.get('tur') or '')}</td><td>{E(i.get('konu') or '')}</td>"
            f"<td>{E(i.get('takim') or '')}</td><td>{E(i.get('ozet') or '')}</td>"
            f"<td>{rozet(i['dogrulama'], sinif.get(i['dogrulama'], 'soluk'))}"
            f"{(' · veri: ' + E(i['veri_dogrulamasi'])) if i.get('veri_dogrulamasi') else ''}</td>"
            f"<td>{E(i.get('kaynak_sinifi') or '')}<br><span class='not'>{E(i.get('erisim_yolu') or '')}</span></td>"
            f"<td>{tr_saat(i['yayin_utc']) if i.get('yayin_utc') and 'T' in i['yayin_utc'] else E(i.get('yayin_utc') or 'yok')}</td>"
            f"<td><a href='{E(i.get('url') or '')}' rel='noreferrer'>{E(_host(i.get('url') or ''))}</a></td></tr>"
            for i in V.iddia_satirlari(hr[0]))
        p.append(f"<div class='kart' id='haber'><h2>Haberler, sakatlıklar, cezalar, basın</h2>"
                 "<p class='uyari'><b>Manuel araştırma:</b> Haber ve yorum araştırması bu uygulamada otomatik yapılmaz. "
                 "Claude oturumunda yapılır ve buraya kaydedilir; aşağıdakiler araştırma anındaki durumdur.</p>"
                 f"<p>{taz}</p><p class='not'>Sürüm: {surumler} · son araştırma {tr_saat(tz['son_arastirma_utc'])} TR "
                 f"(maça {tz['maca_kala_saat']} saat kala) · {E(_tur_bilgisi(mac))} Haberler olasılığa uygulanmaz. "
                 "Doğrulama: resmi / iki_bagimsiz = doğrulandı; dogrulanmadi = tek kaynak ya da arama özeti; celiskili = "
                 "kaynaklar çelişiyor. Erişim yolu “arama_ozeti” ise sayfa okunmadı.</p>"
                 f"<h3>İddialar ({len(hr[0]['iddialar'])})</h3><div class='tasma'><table><tr><th>Araştırma (TR)</th><th>Tur</th>"
                 "<th>Konu</th><th>Takım</th><th>Özet</th><th>Doğrulama</th><th>Kaynak / erişim</th><th>Yayın</th><th>Bağlantı</th></tr>"
                 f"{idd}</table></div>"
                 "<details><summary>Gruplanmış görünüm (doğrulanmış / doğrulanamayan)</summary>"
                 f"<h3>Doğrulanmış son dakika</h3>{_iddia_tablosu(r.get('1_dogrulanmis_son_dakika'))}"
                 f"<h3>Doğrulanamayan / çelişkili</h3>{_iddia_tablosu(r.get('2_dogrulanamayan_veya_celiskili'))}</details>"
                 f"<h3>Basın görüşleri</h3><div class='tasma'><table><tr><th>Sınıf</th><th>Özet</th><th>Yayın</th><th>Kaynak</th></tr>{basin}</table></div>"
                 + (f"<details><summary>Araştırma turları</summary>{md(hr[0]['turlar_md'])}</details>" if hr[0]["turlar_md"] else "")
                 + "</div>")
        a = r.get("4_analist_senaryolari") or {}
        po = ((donmus or {}).get("tahmin") or {}).get("olasiliklar") or {} if donmus and not donmus.get("hata") else {}
        gor = "".join(f"<tr><td>{E(str(g.get('kaynak') or ''))}</td><td>{E(str(g.get('sinif') or ''))}</td>"
                      f"<td>{E(str(g.get('beklenen') or ''))}</td><td>{E(str(g.get('gerekce') or '—'))}</td>"
                      f"<td class='s'>{_skor_p(g.get('beklenen'), po)}</td></tr>" for g in a.get("gorusler") or [])
        p.append(f"<div class='kart' id='analist'><h2>Diğer analistler ve gerekçeleri</h2><p class='not'>{E(a.get('not') or '')} "
                 f"Manuel araştırma; kayıt zamanı {tr_saat(tz['son_arastirma_utc'])} TR"
                 f"{'' if tz['guncel'] else ' — GÜNCEL DEĞİL'}.</p>"
                 f"<div class='tasma'><table><tr><th>Kaynak</th><th>Sınıf</th><th>Beklenti</th><th>Gerekçe</th><th class='s'>Donmuş modelde bu skor</th></tr>{gor}</table></div>"
                 "</div>")
        yor = "".join(f"<li>{E(y.get('mekanizma') or '')} <span class='not'>({E(', '.join(y.get('dayanak') or []))})</span></li>"
                      for y in r.get("11_sportif_cikarimlar_yorum") or [])
        ss = r.get("8_en_onemli_surpriz_sinyali") or {}
        p.append(f"<div class='kart' id='surpriz'><h2>Sürpriz riskleri — favori neden zorlanabilir?</h2>"
                 f"<p>Araştırma anındaki kayıt ({tr_saat(tz['son_arastirma_utc'])} TR): {E(str(ss.get('sinyal') or ss.get('not') or '—'))}</p><h3>Sportif çıkarımlar (YORUM)</h3>"
                 f"<ul>{yor}</ul><p class='not'>Bunlar kanıtlanmamış yorumlardır; olasılığa eklenmez. Genel bulgular için "
                 "<a href='/arastirma/surpriz'>sürpriz araştırması</a> (10+10 keşif; hiçbir sinyal kontrollerden ayrışmadı).</p></div>")
    else:
        p.append("<div class='kart' id='haber'><h2>Haberler</h2><p class='not'>Bu maç için haber araştırması kaydı yok. "
                 f"{E(_tur_bilgisi(mac))} Araştırma Claude oturumunda yapılır (ör. “{E(mac['karsilasma'] or '')} için haber "
                 "araştırması yap”) ve output/arastirma/genis_pilot/ altına kaydedilir; bu sayfa onu okur.</p></div>")
        p.append("<div class='kart' id='surpriz'><h2>Sürpriz riskleri</h2><p class='not'>Araştırma yok. "
                 "<a href='/arastirma/surpriz'>Sürpriz araştırması</a> yalnızca bilgi amaçlıdır.</p></div>")

    # 6-7. fiyat karşılaştırması ve en yüksek fiyat
    fk = V.fiyat_karsilastirmasi(kod, donmus)
    if fk["durum"] != "var":
        sinif = "kilit" if fk["durum"] == "kilitli" else "uyari"
        mac_gunu = datetime.fromisoformat(mac["baslama_tr"]).astimezone(I.TR).date().isoformat()
        dg = (dugme("/islem/bulten", f"{mac_gunu} bültenini çek", "dondurmadan sonra yeni çekim", {"gun": mac_gunu})
              + " " + dugme(f"/islem/fiyat/{kod}", "Fiyat karşılaştır", "dondurmadan sonra çekilmiş en yeni bülten kullanılır")) \
            if fk["durum"] == "yok" else ""
        p.append(f"<div class='kart' id='fiyat'><h2>Nesine fiyat karşılaştırması</h2><p>{rozet(fk['durum'], sinif)} {E(fk['neden'])}</p>{dg}</div>")
    else:
        satirlar = [s for s in fk["satirlar"] if s.get("model_marketi")]
        sat = "".join(
            f"<tr><td>{E(s['market_adi'])}</td><td>{E(s['secenek_adi'])}</td><td class='s'>{s.get('oran') or '—'}</td>"
            f"<td class='s'>{yuzde(s['bagimsiz_olasilik'])}</td><td class='s'>{yuzde(s['basabas_esigi']) if s.get('basabas_esigi') else '—'}</td>"
            f"<td class='s'>{(f'{s['beklenen_deger']:+.3f}') if s.get('beklenen_deger') is not None else E(s.get('not') or '')}</td>"
            f"<td>{_ev_sinifi(s)}</td></tr>"
            for s in satirlar)
        ayrisma = sum(1 for s in satirlar if (s.get("beklenen_deger") or -1) > 0)
        ey = V.en_yuksek_fiyatlar(fk)
        eys = "".join(f"<tr><td>{E(g['olay'] or '')}</td><td>{E(g['en_yuksek']['market_adi'])} — {E(g['en_yuksek']['secenek_adi'])}</td>"
                      f"<td class='s'>{g['en_yuksek']['oran']}</td><td class='s'>{g['kesin_oynanabilir']}/{g['uye_sayisi']}</td>"
                      f"<td class='s'>{g['fark']}</td><td class='s'>{g['kontrol_gerekli']}</td></tr>" for g in ey)
        sy = fk["esdegerlik"].get("sayilar", {})
        p.append(f"<div class='kart' id='fiyat'><h2>Nesine fiyat karşılaştırması (dondurmadan sonra)</h2>"
                 f"<p class='not'>Karşılaştırma {E(fk['karsilastirma_utc'])} UTC · bülten {E(fk['klasor'])} · donmuş SHA eşleşiyor. "
                 "Başabaş eşiği = 1/oran (olasılık değildir). EV = p × oran − 1 bilgi amaçlıdır, öneri değildir.</p>"
                 f"<div class='tasma'><table><tr><th>Market</th><th>Seçenek</th><th class='s'>Oran</th><th class='s'>Bağımsız p</th>"
                 f"<th class='s'>Başabaş</th><th class='s'>EV</th><th>Değerlendirme</th></tr>{sat}</table></div>"
                 f"<p class='not'>{ayrisma} satırda EV pozitif. Bu satırlar avantaj olarak gösterilmez: bağımsız modelin piyasaya "
                 "karşı kazanç sağladığı ileriye dönük olarak doğrulanmadı, kalibrasyon sınırlı, güncel form ve sezon kayması "
                 "denetimi yok. Bu yüzden “model–piyasa ayrışması · doğrulama gerekli” olarak ayrılırlar.</p>"
                 f"<h3>Eşdeğer marketlerde en yüksek fiyat</h3><p class='not'>Seçenek {sy.get('toplam_secenek')} · skor uzayına eşlenen "
                 f"{sy.get('skor_uzayina_eslenen')} · kesin {sy.get('kesin')} · kontrol gerekli {sy.get('kontrol_gerekli')} · alt küme fiyat "
                 f"tutarsızlığı {len(fk['esdegerlik'].get('alt_kume_fiyat_tutarsizliklari') or [])}. Yalnızca oynanabilir ve kesin eşdeğer "
                 "üyeler arasından seçilir; fiyat oranları olasılık olarak sunulmaz.</p><div class='tasma'><table><tr><th>Olay</th>"
                 f"<th>En yüksek fiyatlı seçenek</th><th class='s'>Oran</th><th class='s'>Kesin/üye</th><th class='s'>Fark</th>"
                 f"<th class='s'>Kontrol gerekli</th></tr>{eys}</table></div></div>")

    # 8. raporlar
    rap = V.analiz_raporlari(kod)
    if rap:
        p.append("<div class='kart' id='raporlar'><h2>Analiz raporları</h2>" + "".join(
            f"<details><summary>{E(r['ad'])}</summary>{md(r['metin'])}</details>" for r in rap) + "</div>")
    return sayfa(mac["karsilasma"] or str(kod), "".join(p))


def arsiv_sayfasi() -> str:
    a = V.arsiv()
    sat = []
    for r in a:
        pu = r.get("puan") or {}
        sat.append(f"<tr><td><a href='/mac/{r['mac_id'].split(':')[1]}'>{E(r.get('karsilasma') or r['mac_id'])}</a></td>"
                   f"<td>{tr_saat(r['baslama_tr'])}</td><td>{E(r['dondurma_utc'])}</td><td>{E(r['durum'])}</td>"
                   f"<td class='{'kotu' if r['butunluk'].startswith('HATA') else ''}'>{E(r['butunluk'])}</td><td>{E(r.get('sonuc') or '—')}</td>"
                   f"<td class='s'>{pu.get('market', '—')}</td><td class='s'>{pu.get('ort_log_loss', '—')}</td>"
                   f"<td class='s'>{pu.get('ort_brier', '—')}</td></tr>")
    puanli = [r for r in a if r.get("puan")]
    ozet = (f"{len(a)} donmuş tahmin · {len(puanli)} puanlandı" + (
        f" · ortalama log-kayıp {sum(r['puan']['ort_log_loss'] for r in puanli) / len(puanli):.4f}" if puanli else ""))
    govde = (f"<h1>Tahmin arşivi ve performans</h1><div class='kart'><p>{ozet}</p><p class='not'>Sonuçlar football-data.org "
             "anlık görüntüsünden (normal süre) alınır; puanlama donmuş olasılıklarla yapılır, olasılıklar değişmez. "
             "Performans değerlendirmesi için yeterli örneklem (≥ 100 puanlanmış maç) henüz yok.</p>"
             f"{dugme('/islem/guncel', 'Sonuçları güncelle', 'football-data.org güncel veri çekimi')}</div>"
             "<div class='kart tasma'><table><tr><th>Maç</th><th>Başlama (TR)</th><th>Dondurma (UTC)</th><th>Durum</th>"
             "<th>Bütünlük</th><th>Sonuç</th><th class='s'>Market</th><th class='s'>Ort. log-kayıp</th><th class='s'>Ort. Brier</th></tr>"
             + "".join(sat) + "</table></div>")
    return sayfa("Tahmin arşivi", govde)


def surpriz_sayfasi() -> str:
    s = V.surpriz_arastirmasi()
    if not s["rapor_md"]:
        return sayfa("Sürpriz araştırması", "<div class='kart'>Araştırma çıktısı yok.</div>")
    tablo = ""
    k = s.get("kodlama") or {}
    if k.get("sinyal_sikligi"):
        tablo = ("<table><tr><th>Sinyal</th><th class='s'>Sürpriz</th><th class='s'>Kontrol (yanlış alarm)</th></tr>" + "".join(
            f"<tr><td>{E(t['sinyal'])}</td><td class='s'>{t['surpriz']}/10</td><td class='s'>{t['kontrol_yanlis_alarm']}/10</td></tr>"
            for t in k["sinyal_sikligi"]) + "</table>")
    govde = (f"<h1>Sürpriz araştırması (bilgi ve araştırma bölümü)</h1><div class='kart uyari'>{E(s['uyari'])}</div>"
             f"<div class='kart'><h2>Sinyal sıklıkları ({E(s['kodlama_dosyasi'] or '')})</h2>{tablo}</div>"
             f"<div class='kart'>{md(s['rapor_md'])}</div>")
    return sayfa("Sürpriz araştırması", govde)


def hata_sayfasi(e: Exception, geri: str) -> str:
    import socket
    from urllib.error import URLError
    if isinstance(e, (URLError, socket.timeout, ConnectionError, TimeoutError)):
        ozet = "Ağ bağlantısı kurulamadı ya da yanıt gelmedi. Biraz sonra yeniden deneyin."
    elif isinstance(e, FileNotFoundError):
        ozet = "Gerekli bir dosya bulunamadı."
    elif isinstance(e, (ValueError, KeyError)):
        ozet = f"Veri beklenen biçimde değil: {e}"
    else:
        ozet = f"Beklenmeyen hata: {type(e).__name__}"
    ayrinti = "" if G.bulut_mu() else (f"<details><summary>Teknik ayrıntı</summary><pre>{E(traceback.format_exc())}</pre>"
                                        "</details>")
    if G.bulut_mu():
        print(f"HATA {type(e).__name__}: {e}", flush=True)       # ayrıntı yalnızca sunucu günlüğüne
    return sayfa("Hata", f"<div class='kart kotu'><h2>İşlem tamamlanamadı</h2><p>{E(ozet)}</p>"
                         "<p>Hiçbir donmuş tahmin ya da önceki çıktı değiştirilmedi.</p>"
                         f"<p><a href='{E(geri)}'>Geri dön</a></p>{ayrinti}</div>")


def giris_sayfasi(hata: str = "", sonraki: str = "/") -> str:
    return sayfa("Giriş", f"<div class='kart giris'><h1>Giriş</h1>{f'<p class=kotu>{E(hata)}</p>' if hata else ''}"
                          "<form method='post' action='/giris'>"
                          f"<input type='hidden' name='sonraki' value='{E(sonraki)}'>"
                          "<label>Kullanıcı adı<input name='kullanici' autocomplete='username' autocapitalize='none' required></label>"
                          "<label>Parola<input name='parola' type='password' autocomplete='current-password' required></label>"
                          "<button>Giriş yap</button></form></div>")


def yonetim_sayfasi() -> str:
    d = Y.depolama_durumu()
    kalici = rozet("kalıcı disk", "iyi") if d["kalici"] else rozet("GEÇİCİ: yeniden başlatmada silinir", "kotu")
    return sayfa("Yedek ve depolama", (
        "<h1>Yedek ve depolama</h1><div class='kart'>"
        f"<p>Depolama: {kalici} · {E(d['kok'])} · boş {d['bos_mb']} MB / {d['toplam_mb']} MB · "
        f"{d['donmus_tahmin']} donmuş tahmin · {d['bulten']} bülten</p>"
        "<p><a href='/yonetim/yedek.tar.gz'><button type='button'>Yedeği indir (tar.gz)</button></a> "
        "<span class='not'>Tahminler, arşiv, haber araştırmaları, raporlar, güncel veri anlık görüntüleri ve bültenlerin "
        "oransız/oranlı JSON kayıtları; ham yanıt ve Excel hariç. SHA-256 manifestli.</span></p></div>"
        "<div class='kart'><h2>Yedekten geri yükle</h2><p class='not'>Var olan dosyaların üzerine yazılmaz; çakışmalar "
        "raporlanır. Manifestle uyuşmayan yedek reddedilir. Donmuş tahminler SHA-256 ile denetlenir.</p>"
        f"<input type='file' id='yedek' accept='.tar.gz,.tgz,application/gzip'> "
        f"<button type='button' id='yukle' data-csrf='{E(getattr(_IST, 'csrf', '') or '')}'>Yükle</button>"
        "<pre id='sonuc' class='not'></pre><script src='/statik/yukle.js'></script></div>"))


YUKLE_JS = """document.getElementById('yukle').addEventListener('click', async (e) => {
  const f = document.getElementById('yedek').files[0], s = document.getElementById('sonuc');
  if (!f) { s.textContent = 'Önce bir yedek dosyası seçin.'; return; }
  s.textContent = 'Yükleniyor…';
  try {
    const r = await fetch('/yonetim/ice-aktar', {method: 'POST', body: f, credentials: 'same-origin',
      headers: {'Content-Type': 'application/gzip', 'X-CSRF': e.target.dataset.csrf}});
    s.textContent = (r.ok ? '' : 'Hata ' + r.status + ': ') + await r.text();
  } catch (err) { s.textContent = 'Bağlantı hatası: ' + err; }
});"""


# ------------------------------------------------------------------------------------------------ HTTP
AYAR: dict = {}
EN_FAZLA_FORM = 16 * 1024


class Isleyici(BaseHTTPRequestHandler):
    server_version = "FootballIntelligence"
    sys_version = ""
    timeout = 60
    protocol_version = "HTTP/1.1"

    # -------------------------------------------------------------- yanıt
    def _gonder(self, kod: int, govde, tur: str = "text/html; charset=utf-8", ek: dict | None = None):
        b = govde.encode("utf-8") if isinstance(govde, str) else govde
        if self.command == "POST" and not getattr(self, "_govde_okundu", False):
            self.close_connection = True           # okunmamış gövde sonraki istek sanılmasın
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(b)))
        for k, v in {**G.guvenlik_basliklari(G.bulut_mu()), **(ek or {})}.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(b)

    def _yonlendir(self, yer: str, ek: dict | None = None, kod: int = 303):
        self._gonder(kod, "", "text/plain; charset=utf-8", {"Location": yer, **(ek or {})})

    def _uyari(self, kod: int, baslik: str, metin: str, geri: str = "/"):
        self._gonder(kod, sayfa(baslik, f"<div class='kart uyari'><h2>{E(baslik)}</h2><p>{E(metin)}</p>"
                                        f"<p><a href='{E(geri)}'>Geri dön</a></p></div>"))

    # -------------------------------------------------------------- ortak denetimler
    def _host(self) -> str:
        return (self.headers.get("Host") or "").split(":")[0].lower()

    def _izinli_hostlar(self) -> list[str]:
        return AYAR.get("hostlar") if G.bulut_mu() else ["127.0.0.1", "localhost"]

    def _on_denetim(self) -> bool:
        """Host, HTTPS ve oturum. False dönerse yanıt verilmiştir."""
        _IST.kullanici, _IST.csrf, _IST.oturum = None, None, None
        if self._host() not in self._izinli_hostlar():
            self._gonder(421, "Bu ana makine adı için hizmet verilmiyor.", "text/plain; charset=utf-8")
            return False
        if G.bulut_mu() and (self.headers.get("X-Forwarded-Proto") or "https") != "https":
            self._yonlendir(f"https://{self._host()}{self.path}", kod=301)
            return False
        if not G.bulut_mu():
            return True
        oturum = G.cerez_oku(self.headers.get("Cookie"))
        k = G.oturum_dogrula(AYAR["anahtar"], oturum)
        if k and hmac_esit(k, AYAR["kullanici"]):
            _IST.kullanici, _IST.oturum, _IST.csrf = k, oturum, G.csrf_jetonu(AYAR["anahtar"], oturum)
        return True

    def _giris_gerekli(self) -> bool:
        if G.bulut_mu() and not _IST.kullanici:
            if self.command == "GET":
                self._yonlendir("/giris?sonraki=" + quote(self.path, safe=""))
            else:
                self._uyari(401, "Oturum gerekli", "Oturumunuz yok ya da süresi doldu. Yeniden giriş yapın.", "/giris")
            return True
        return False

    def _koken_dogru(self) -> bool:
        koken = self.headers.get("Origin") or self.headers.get("Referer")
        if koken == "null":
            return False
        return not koken or (urlparse(koken).hostname or "").lower() in self._izinli_hostlar()

    def _govde(self, sinir: int) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        if n > sinir:
            raise BuyukIstek()
        veri = self.rfile.read(n) if n else b""
        self._govde_okundu = True
        return veri

    def _ip(self) -> str:
        return G.istemci_ip(self.headers.get("X-Forwarded-For"), self.client_address[0])

    # -------------------------------------------------------------- GET
    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/saglik":
            return self._gonder(200, '{"durum":"ok"}', "application/json")
        if not self._on_denetim():
            return
        try:
            if u.path == "/giris":
                if _IST.kullanici or not G.bulut_mu():
                    return self._yonlendir("/")
                return self._gonder(200, giris_sayfasi(sonraki=_guvenli_sonraki(parse_qs(u.query).get("sonraki", ["/"])[0])))
            if u.path == "/statik/yukle.js":
                return self._gonder(200, YUKLE_JS, "application/javascript; charset=utf-8")
            if self._giris_gerekli():
                return
            if u.path == "/":
                return self._gonder(200, ana_sayfa(parse_qs(u.query)))
            m = re.fullmatch(r"/mac/(\d{1,12})", u.path)
            if m:
                return self._gonder(200, mac_sayfasi(int(m.group(1))))
            if u.path == "/arsiv":
                return self._gonder(200, arsiv_sayfasi())
            if u.path == "/arastirma/surpriz":
                return self._gonder(200, surpriz_sayfasi())
            if u.path == "/yonetim":
                return self._gonder(200, yonetim_sayfasi())
            if u.path == "/yonetim/yedek.tar.gz":
                veri, ad = Y.yedek_olustur()
                return self._gonder(200, veri, "application/gzip", {"Content-Disposition": f"attachment; filename={ad}"})
            return self._gonder(404, sayfa("Bulunamadı", "<div class='kart uyari'><h2>Sayfa bulunamadı</h2><p>Bu adreste "
                                           "bir sayfa yok. <a href='/'>Günün maçlarına dön</a>.</p></div>"))
        except Exception as e:
            return self._gonder(500, hata_sayfasi(e, "/"))

    # -------------------------------------------------------------- POST
    def do_POST(self):
        self._govde_okundu = False
        u = urlparse(self.path)
        if not self._on_denetim():
            return
        if not self._koken_dogru():
            return self._uyari(403, "Yasak", "İstek bu uygulamanın sayfalarından gelmedi.")
        geri = "/"
        try:
            if u.path == "/giris":
                return self._giris(parse_qs(self._govde(EN_FAZLA_FORM).decode("utf-8")))
            if self._giris_gerekli():
                return
            if u.path == "/yonetim/ice-aktar":
                if G.bulut_mu() and not G.csrf_dogru(AYAR["anahtar"], _IST.oturum, self.headers.get("X-CSRF")):
                    return self._gonder(403, "CSRF jetonu geçersiz.", "text/plain; charset=utf-8")
                self._sinir("ice_aktar")
                r = Y.ice_aktar(self._govde(Y.EN_FAZLA_BAYT))
                return self._gonder(200, Y.json_ozet(r), "text/plain; charset=utf-8")
            form = parse_qs(self._govde(EN_FAZLA_FORM).decode("utf-8"))
            if G.bulut_mu() and not G.csrf_dogru(AYAR["anahtar"], _IST.oturum, (form.get("csrf") or [None])[0]):
                return self._uyari(403, "Güvenlik denetimi", "Form jetonu geçersiz. Sayfayı yenileyip yeniden deneyin.")
            if u.path == "/cikis":
                return self._yonlendir("/giris", {"Set-Cookie": G.cerez_yaz("", G.bulut_mu(), sil=True)})
            if u.path == "/islem/bulten":
                gun = (form.get("gun") or [None])[0]
                if gun and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", gun):
                    raise IS.IslemHatasi("geçersiz gün")
                self._sinir("bulten")
                r = IS.bulten_cek(gun)
                geri = f"/?bulten={r['klasor']}&gun={r['gun']}"
            elif u.path == "/islem/guncel":
                self._sinir("guncel")
                r = IS.guncel_veri_cek()
            elif m := re.fullmatch(r"/islem/dondur/(\d{1,12})", u.path):
                geri = f"/mac/{m.group(1)}"
                self._sinir("dondur")
                r = IS.dondur_mac(int(m.group(1)))
            elif m := re.fullmatch(r"/islem/fiyat/(\d{1,12})", u.path):
                geri = f"/mac/{m.group(1)}#fiyat"
                self._sinir("fiyat")
                r = IS.fiyat_karsilastir_mac(int(m.group(1)))
            else:
                return self._gonder(404, sayfa("Bulunamadı", "<div class='kart uyari'><h2>İşlem yok</h2></div>"))
            if r.get("islem") == "dondurma" and not r.get("donduruldu"):
                govde = (f"<h1>Dondurulmadı</h1><div class='kart uyari'><h2>Bağımsız tahmin hesaplanamaz</h2><ul>"
                         + "".join(f"<li>{E(n)}</li>" for n in r.get("nedenler") or [])
                         + "</ul><p>Hazırlık kapısı geçilmediği için olasılık üretilmedi ve hiçbir kayıt oluşturulmadı.</p>"
                         f"<p><a href='{E(geri)}'>Geri dön</a></p></div>")
                return self._gonder(200, sayfa("Dondurulmadı", govde))
            gorunen = {k: v for k, v in r.items() if k not in ("yol", "cikti")} if G.bulut_mu() else r
            govde = (f"<h1>İşlem tamamlandı</h1><div class='kart'><pre>{E(json.dumps(gorunen, ensure_ascii=False, indent=1))}</pre>"
                     f"<p><a href='{E(geri)}'>Geri dön</a></p></div>")
            return self._gonder(200, sayfa("İşlem", govde))
        except SinirAsildi as e:
            return self._uyari(429, "Çok sık istek", f"Bu işlem için sınır doldu; {e.sn} saniye sonra yeniden deneyin. "
                               "(Dış kaynaklara aşırı yük bindirmemek için.)", geri)
        except BuyukIstek:
            return self._uyari(413, "İstek çok büyük", "Gönderilen veri izin verilen boyutu aşıyor.", geri)
        except IS.IslemHatasi as e:
            return self._uyari(409, "İşlem yapılmadı", str(e), geri)
        except Y.YedekHatasi as e:
            return self._gonder(409, f"Yedek reddedildi: {e}", "text/plain; charset=utf-8")
        except Exception as e:
            return self._gonder(500, hata_sayfasi(e, geri))

    def _sinir(self, ad: str):
        ok, sn = G.ISLEM_SINIRLARI[ad].izin(ad)
        if not ok:
            raise SinirAsildi(sn)

    def _giris(self, form: dict):
        if not G.bulut_mu():
            return self._yonlendir("/")
        ip = self._ip()
        for s in (G.GIRIS_IP, G.GIRIS_GENEL):
            ok, sn = s.izin(ip if s is G.GIRIS_IP else "genel")
            if not ok:
                return self._gonder(429, giris_sayfasi(f"Çok fazla deneme. {sn // 60 + 1} dakika sonra yeniden deneyin."))
        k = (form.get("kullanici") or [""])[0]
        p = (form.get("parola") or [""])[0]
        sonraki = _guvenli_sonraki((form.get("sonraki") or ["/"])[0])
        if hmac_esit(k, AYAR["kullanici"]) and G.parola_dogru(p, AYAR["parola_ozeti"]):
            oturum = G.oturum_olustur(AYAR["anahtar"], k)
            return self._yonlendir(sonraki, {"Set-Cookie": G.cerez_yaz(oturum, True)})
        time.sleep(1.0)
        return self._gonder(401, giris_sayfasi("Kullanıcı adı ya da parola yanlış.", sonraki))

    def log_message(self, fmt, *args):
        if G.bulut_mu():           # yol ve durum kodu; çerez, form ve IP günlüğe yazılmaz
            print(f"{self.command} {urlparse(self.path).path} {args[1] if len(args) > 1 else ''}", flush=True)


class SinirAsildi(Exception):
    def __init__(self, sn: int):
        super().__init__(sn)
        self.sn = sn


class BuyukIstek(Exception):
    pass


def hmac_esit(a: str, b: str) -> bool:
    import hmac as _h
    return _h.compare_digest(a.encode(), b.encode())


def _guvenli_sonraki(yol: str) -> str:
    """Açık yönlendirmeyi önler: yalnızca site içi mutlak yol."""
    return yol if yol.startswith("/") and not yol.startswith("//") and "\\" not in yol else "/"


def calistir(port: int = 8765, adres: str = "127.0.0.1") -> None:
    AYAR.clear()
    AYAR.update(G.ayarlar())               # bulut kipinde eksik ayar → AyarHatasi, sunucu açılmaz
    if G.bulut_mu() and adres == "127.0.0.1":
        adres = "0.0.0.0"
    if not G.bulut_mu() and adres not in ("127.0.0.1", "localhost"):
        raise G.AyarHatasi("girişsiz yerel kip yalnızca 127.0.0.1'e bağlanabilir; internete açmak için FI_ORTAM=bulut")
    sunucu = ThreadingHTTPServer((adres, port), Isleyici)
    sunucu.daemon_threads = True
    kip = "bulut (giriş zorunlu)" if G.bulut_mu() else "yerel"
    print(f"Football Intelligence V1 [{kip}]: http://{adres}:{port}", flush=True)
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        pass


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description="Football Intelligence V1 arayüzü")
    a.add_argument("komut", nargs="?", choices=["sunucu", "parola-ozeti"], default="sunucu")
    a.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8765)))
    a.add_argument("--host", default="127.0.0.1")
    x = a.parse_args(argv)
    if x.komut == "parola-ozeti":
        import getpass
        p1 = getpass.getpass("Yeni parola (en az 12 karakter): ")
        if p1 != getpass.getpass("Yeniden: "):
            print("Parolalar uyuşmuyor.")
            return 1
        print(G.parola_ozeti(p1))
        return 0
    try:
        calistir(x.port, x.host)
    except G.AyarHatasi as e:
        print(f"Sunucu başlatılmadı: {e}", flush=True)
        return 2
    return 0
