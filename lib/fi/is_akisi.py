"""K + L aşaması: tek maç araştırma iş akışı, tahmin dondurma, sonradan fiyat karşılaştırması ve ileri doğrulama kaydı.

Sıra (MK-1): (1) Türkiye gününe göre maç seçimi → (2) veri/model kapsamı → (3) bağımsız olasılık ya da "hesaplanamaz"
→ (4) DONDURMA (zaman, veri kesimi, model sürümü, SHA-256) → (5) ANCAK SONRA Nesine fiyatları: başabaş eşiği, beklenen
değer, market tutarlılığı. Dondurulmamış ya da maç başladıktan sonra dondurulmuş tahminle karşılaştırma yapılmaz.

Model kapsamı (E/F aşaması sonuçlarına göre; doğrulanmamış hiçbir markete olasılık verilmez):
  - Yalnızca veri/model_kapsami.json'da "kapsamda" olan marketler (taban üstü + kalibre + lig ECE; fi.model.kapsam).
    DOGRULANAN_E (v1 listesi) yalnızca geçmiş kayıt için tutulur; artık kullanılmaz.
  - Toplam gol alt/üst, KG, gol aralığı, tek/çift: E'de tabanı geçmedi → hesaplanamaz.
  - Devre marketleri: F-v2'de tabanı geçmedi / bağımsızlık reddedildi → hesaplanamaz.
  - Korner, kart, oyuncu, özel marketler: doğrulanmış model yok → hesaplanamaz.
Lig ve takım eşlemesi yalnızca kullanıcı onaylı (veri/lig_eslemeleri.json) ya da 'kesin' eşleşmeyle yapılır.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from .girdi import oransiz_mi
from .takim_adlari import TakimEslestirici

TR = ZoneInfo("Europe/Istanbul")
KOK = Path(__file__).resolve().parents[2]
LIG_ESLEME = KOK / "veri" / "lig_eslemeleri.json"
TAHMIN_KOK = KOK / "output" / "tahminler"
SURUM = "is-akisi-0.1"
EN_FAZLA_VERI_BOSLUGU_GUN = 14
# E aşamasında (fr.1, nl.1, pt.1, de.2, es.2; 10.158 maç) Poisson'un taban üstü bulunduğu maç sonu marketleri
DOGRULANAN_E = ("MS_1", "MS_X", "MS_2", "CS_1X", "CS_12", "CS_X2", "H-1_1", "H-1_X", "H-1_2",
                "ev0.5_alt", "ev0.5_ust", "dep0.5_alt", "dep0.5_ust", "ev1.5_alt", "ev1.5_ust", "dep1.5_alt",
                "dep1.5_ust", "ev2.5_alt", "ev2.5_ust", "dep2.5_alt", "dep2.5_ust", "MS1_AU2.5_alt", "MS1_AU2.5_ust",
                "MS1_KG_var", "MS1_KG_yok", "MS2_AU2.5_alt", "MS2_AU2.5_ust", "MS2_KG_var", "MS2_KG_yok",
                "skor_0_1", "skor_1_1", "skor_2_0", "skor_0_2", "skor_2_1", "skor_1_2")
KALIBRASYON_NOTU = ("E aşamasında çoğu markette ECE 0,01–0,03; kutularda ≤0,05 sapma koşulu birçok markette sağlanmadı. "
                    "'Yüksek güven' verilmez.")


# --------------------------------------------------------------------------------------------- 1. gün filtresi
def gunun_maclari(fikstur: dict, gun: str) -> list[dict]:
    """Yalnızca Türkiye saatine göre `gun` (YYYY-AA-GG) içinde 00:00–23:59 başlayan maçlar; gece yarısı sonrası dışarıda."""
    hedef = date.fromisoformat(gun)
    out = []
    for m in fikstur.get("maclar", []):
        b = m.get("baslama_tr")
        if not b:
            continue
        t = datetime.fromisoformat(b).astimezone(TR)
        if t.date() == hedef:
            out.append(m)
    return sorted(out, key=lambda m: m["baslama_tr"])


# --------------------------------------------------------------------------------------------- 2-3. kapsam ve olasılık
def lig_eslemesi(nesine_lig: str, yol: Path = LIG_ESLEME) -> str | None:
    if not Path(yol).exists():
        return None
    for k in json.loads(Path(yol).read_text(encoding="utf-8")).get("eslemeler", []):
        if k["nesine_lig"] == nesine_lig:
            return k["kaynak_lig"]
    return None


def kapsam_yukle(yol: Path | None = None) -> tuple[dict, str]:
    from .model.kapsam import kapsam_oku, KAYIT
    return kapsam_oku(yol or KAYIT)


def bagimsiz_tahmin(mac: dict, lig_maclari: list[dict] | None, kaynak_lig: str | None,
                    eslestirici: TakimEslestirici | None = None, kapsam: tuple[dict, str] | None = None,
                    model_adi: str | None = None) -> dict:
    """Oransız fikstür satırından bağımsız olasılık ya da gerekçeli 'hesaplanamaz'.

    Hazırlık kapısı (madde 8): her kriter `hazirlik` listesine kanıtıyla yazılır; biri sağlanmazsa olasılık verilmez.
    """
    oransiz_mi(mac, "mac")
    kapsam_veri, kapsam_sha = kapsam or kapsam_yukle()
    if model_adi is None:      # ligde ileriye dönük sınanmış model öncelikli (E2), yoksa E Poisson
        model_adi = next((ad for ad in ("E3", "E2_aday", "poisson_E") if ad in kapsam_veri["modeller"]
                          and kaynak_lig in kapsam_veri["modeller"][ad]["degerlendirme_ligleri"]), "poisson_E")
    model = kapsam_veri["modeller"][model_adi]
    spec = model.get("spec", {"ceza": 2.0})
    hz = []

    def kriter(ad, gecti, kanit):
        hz.append({"kriter": ad, "gecti": bool(gecti), "kanit": kanit})
        return bool(gecti)

    baslama = datetime.fromisoformat(mac["baslama_tr"])
    sonuc = {"durum": "hesaplanamaz", "hazirlik": hz, "kapsam_sha256": kapsam_sha, "model_adi": model_adi}
    ok = kriter("lig_eslemesi_onayli", kaynak_lig is not None,
                f"{mac.get('lig')} → {kaynak_lig}" if kaynak_lig else "veri/lig_eslemeleri.json'da onaylı kayıt yok")
    ok &= kriter("model_bu_ligde_degerlendirildi", kaynak_lig in model["degerlendirme_ligleri"],
                 f"{model_adi} değerlendirme ligleri: {model['degerlendirme_ligleri']}")
    ok &= kriter("lig_verisi_var", bool(lig_maclari), f"{len(lig_maclari or [])} maç")
    if not ok:
        sonuc["nedenler"] = [f"{h['kriter']}: {h['kanit']}" for h in hz if not h["gecti"]]
        return sonuc
    gecmis = [m for m in lig_maclari if m["tarih"] < baslama.date().isoformat()]
    kesim = max((m["tarih"] for m in gecmis), default=None)
    bosluk = (baslama.date() - date.fromisoformat(kesim)).days if kesim else None
    sonuc.update({"veri_kesimi": kesim, "veri_boslugu_gun": bosluk,
                  "veri_kaynaklari": sorted({m.get("kaynak", "openfootball") for m in gecmis})})
    ok &= kriter("veri_guncel", bosluk is not None and bosluk <= EN_FAZLA_VERI_BOSLUGU_GUN,
                 f"son skorlu maç {kesim}, boşluk {bosluk} gün (sınır {EN_FAZLA_VERI_BOSLUGU_GUN})")
    E = eslestirici or TakimEslestirici()
    adlar = sorted({m["ev_ad"] for m in gecmis} | {m["dep_ad"] for m in gecmis})
    anahtar = {m["ev_ad"]: m["ev"] for m in gecmis} | {m["dep_ad"]: m["dep"] for m in gecmis}
    takim = {}
    for taraf, ad in (("ev", mac["ev"]), ("dep", mac["deplasman"])):
        e = E.eslestir(ad, f"openfootball:{kaynak_lig}", adlar)
        sonuc[f"{taraf}_esleme"] = {"durum": e.durum, "kaynak_adi": e.kaynak_adi, "alternatifler": e.alternatifler}
        if kriter(f"takim_eslemesi_{taraf}", e.durum in ("kesin", "onayli"), f"'{ad}' → {e.durum} {e.kaynak_adi}"):
            takim[taraf] = anahtar[e.kaynak_adi]
        else:
            ok = False
    kapsamdaki = [a for a, r in model["marketler"].items() if r["kapsamda"]]
    ok &= kriter("test_edilmis_ve_kalibre_market_var", bool(kapsamdaki), f"{len(kapsamdaki)} market: {kapsamdaki}")
    kriter("veri_kesimi_kaydedildi", kesim is not None, str(kesim))
    kriter("oranlardan_once_dondurulacak", True, "olasılık yalnızca dondur() ile kaydedilir; fiyat karşılaştırması "
           "fiyat_karsilastir()'ta dondurmadan sonra (oran bu fonksiyona girmez: oransiz_mi)")
    if not ok:
        sonuc["nedenler"] = [f"{h['kriter']}: {h['kanit']}" for h in hz if not h["gecti"]]
        return sonuc
    from .model.goller import GolModeli, skor_matrisi
    from .model.pazar_modelleri import market_olasiliklari, tutarlilik_denetimi
    gm = GolModeli(xi=0.003, pencere_gun=1095, ceza=spec["ceza"], yeni_hucum=0.8, yeni_savunma=1.2, dixon_coles=False)
    son_sezon = gecmis[-1]["sezon"]
    takimlar = {t for m in gecmis if m["sezon"] == son_sezon for t in (m["ev"], m["dep"])} | set(takim.values())
    gm.hazirla(gecmis, baslama.date().isoformat(), takimlar)
    lh, la = gm.oranlar(takim["ev"], takim["dep"])
    if spec.get("w") is not None:          # E2 M3: toplamı lig 365 gün ortalamasına büz (yeni_gol.matris ile aynı)
        from datetime import timedelta
        bas = (baslama.date() - timedelta(days=365)).isoformat()
        son = [m["ev_gol"] + m["dep_gol"] for m in gecmis if m["tarih"] >= bas]
        if len(son) < 50:
            return {"durum": "hesaplanamaz", "hazirlik": hz, "nedenler": ["son 365 günde < 50 maç: lig ortalaması yok"]}
        mu = sum(son) / len(son)
        T = lh + la
        T2 = max(mu * (1 + spec["b"]) + spec["w"] * (T - mu), 0.2)
        lh, la = lh * T2 / T, la * T2 / T
        sonuc["lig_ortalamasi_365"] = mu
    if spec.get("A"):                      # E3: zaman sıralı güç farkı ölçeği γ ve ev kayması δ (ON_KAYIT_E3)
        from .model import e3 as E3
        gd = E3.canli_gamma_delta(kaynak_lig, baslama.date().isoformat())
        lh, la = E3.donustur(lh, la, gd["gamma"], gd["delta"])
        sonuc["e3_duzeltmesi"] = gd
    mtr = skor_matrisi(lh, la, 0.0)
    p = market_olasiliklari(mtr)
    hata = tutarlilik_denetimi(p, mtr)
    if hata:
        return {"durum": "hesaplanamaz", "hazirlik": hz, "nedenler": ["ortak dağılım tutarsız: " + "; ".join(hata)]}
    sonuc.update({"durum": "hesaplandi", "model": model["tanim"],
                  "lambda_ev": lh, "lambda_dep": la, "egitim_mac_sayisi": len(gecmis),
                  "olasiliklar": {k: p[k] for k in kapsamdaki},
                  "hesaplanamaz_pazarlar": {a: r["nedenler"] for a, r in model["marketler"].items() if not r["kapsamda"]},
                  "kalibrasyon_notu": KALIBRASYON_NOTU,
                  "skor_matrisi": [[round(float(x), 10) for x in r] for r in mtr[:8, :8]]})
    return sonuc


# --------------------------------------------------------------------------------------------- 4. dondurma
def _kanonik(o) -> bytes:
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _commit() -> str | None:
    try:
        return subprocess.run(["git", "-C", str(KOK), "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=5).stdout.strip() or None
    except Exception:
        return None


def dondur(mac: dict, tahmin: dict, kok: Path = TAHMIN_KOK, simdi: datetime | None = None) -> dict:
    oransiz_mi(mac, "mac")
    oransiz_mi(tahmin, "tahmin")
    simdi = simdi or datetime.now(timezone.utc)
    baslama = datetime.fromisoformat(mac["baslama_tr"])
    if simdi >= baslama:
        raise ValueError("maç başlamış: maç öncesi tahmin dondurulamaz")
    govde = {"tur": "donmus_tahmin", "mac_id": mac.get("mac_id"), "karsilasma": mac.get("karsilasma"),
             "lig": mac.get("lig"), "baslama_tr": mac["baslama_tr"], "dondurma_utc": simdi.isoformat(timespec="seconds"),
             "veri_kesimi": tahmin.get("veri_kesimi"), "model_surumu": {"is_akisi": SURUM, "git_commit": _commit()},
             "tahmin": tahmin}
    oz = hashlib.sha256(_kanonik(govde)).hexdigest()
    kayit = {**govde, "sha256": oz}
    kok = Path(kok)
    kok.mkdir(parents=True, exist_ok=True)
    yol = kok / f"{(mac.get('mac_id') or 'mac').replace(':', '_')}_{simdi:%Y%m%dT%H%M%SZ}.json"
    yol.write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(kok / "kayit.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"dosya": yol.name, "sha256": oz, "mac_id": govde["mac_id"],
                            "baslama_tr": govde["baslama_tr"], "dondurma_utc": govde["dondurma_utc"],
                            "durum": tahmin.get("durum")}, ensure_ascii=False) + "\n")
    return {"yol": str(yol), "sha256": oz}


def donmus_oku(yol: Path) -> dict:
    k = json.loads(Path(yol).read_text(encoding="utf-8"))
    oz = k.pop("sha256")
    if hashlib.sha256(_kanonik(k)).hexdigest() != oz:
        raise ValueError("donmuş tahmin değiştirilmiş: SHA-256 uyuşmuyor")
    k["sha256"] = oz
    return k


# --------------------------------------------------------------------------------------------- 5. fiyat karşılaştırması
def fiyat_karsilastir(donmus_yol: Path, nesine_mac: dict, simdi: datetime | None = None) -> dict:
    """Donmuş tahmini Nesine dışa aktarımıyla (bulten_dogrulama) karşılaştırır. Olasılık burada DEĞİŞMEZ."""
    from .model.pazar_modelleri import olay_maskeleri
    from .pazar import esdegerlik as ES
    d = donmus_oku(donmus_yol)
    simdi = simdi or datetime.now(timezone.utc)
    if datetime.fromisoformat(d["dondurma_utc"]) >= datetime.fromisoformat(d["baslama_tr"]):
        raise ValueError("tahmin maç başladıktan sonra dondurulmuş: karşılaştırma geçersiz")
    if simdi < datetime.fromisoformat(d["dondurma_utc"]):
        raise ValueError("karşılaştırma zamanı dondurmadan önce olamaz")
    p = (d["tahmin"] or {}).get("olasiliklar") or {}
    # model marketlerini ES ızgarasında maç sonu maskesine çevir
    ms_anahtar = {}
    es_maskeleri = olay_maskeleri(ES.H, ES.A)
    for ad in p:
        es_maske = es_maskeleri[ad]
        ms_anahtar[hashlib.sha1(np.packbits(es_maske).tobytes()).hexdigest()] = ad
    satirlar = []
    for mk in nesine_mac.get("marketler", []):
        for s in ES.market_olaylari(mk, nesine_mac.get("mac_kodu")):
            if s.olay is None:
                continue
            ad = ms_anahtar.get(hashlib.sha1(np.packbits(s.olay.maske).tobytes()).hexdigest())
            satir = {**s.ozet(), "model_marketi": ad}
            if ad is None:
                satir["bagimsiz_olasilik"] = "hesaplanamaz"
            elif s.olay.kesinlik != "kesin":
                satir["bagimsiz_olasilik"] = "kontrol gerekli (market eşdeğerliği kesin değil)"
            elif s.oynanabilirlik != "oynanabilir" or not s.oran or s.oran <= 1:
                satir["bagimsiz_olasilik"] = round(p[ad], 4)
                satir["not"] = "oynanabilir değil: başabaş/EV hesaplanmadı"
            else:
                satir.update({"bagimsiz_olasilik": round(p[ad], 4), "basabas_esigi": round(1 / s.oran, 4),
                              "beklenen_deger": round(p[ad] * s.oran - 1, 4),
                              "not": "EV = p × oran − 1; p kalibrasyonu sınırlı, 'yüksek güven' yok; başabaş eşiği "
                                     "olasılık değildir"})
            satirlar.append(satir)
    return {"donmus_sha256": d["sha256"], "dondurma_utc": d["dondurma_utc"], "karsilastirma_utc":
            simdi.isoformat(timespec="seconds"), "tahmin_durumu": d["tahmin"].get("durum"),
            "satirlar": satirlar, "esdegerlik": ES.mac_denetimi(nesine_mac)}


# --------------------------------------------------------------------------------------------- L. ileri doğrulama
def ileri_puanla(donmus_yol: Path, ev_gol: int, dep_gol: int, sonuc_kaynagi: str) -> dict:
    """Maç sonucu geldikten sonra donmuş tahmini puanlar (olasılıklar değişmez; sonuç kaynağı kaydedilir)."""
    from .model.pazar_modelleri import gozlenen
    d = donmus_oku(donmus_yol)
    p = (d["tahmin"] or {}).get("olasiliklar")
    if not p:
        return {"durum": "puanlanamaz (tahmin hesaplanamaz idi)", "sha256": d["sha256"]}
    y = gozlenen(ev_gol, dep_gol)
    pu = {}
    for ad, q in p.items():
        q = min(max(q, 1e-15), 1 - 1e-15)
        o = float(y[ad])
        pu[ad] = {"p": q, "y": o, "log_loss": float(-(o * np.log(q) + (1 - o) * np.log(1 - q))), "brier": (q - o) ** 2}
    return {"sha256": d["sha256"], "skor": [ev_gol, dep_gol], "sonuc_kaynagi": sonuc_kaynagi, "puanlar": pu}
