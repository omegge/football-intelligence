"""Araştırma hafızası ve bülten saklama politikası.

Amaç geçmiş bültenleri biriktirmek değil, araştırılan maçların bilgisini kalıcı tutmaktır.

Hafıza (`output/hafiza/`, kalıcı):
  maclar/<kod>/bulten_<klasör>.json   araştırılan/dondurulan maçın o çekimdeki BÜTÜN marketleri ve oranları
                                       (zaman damgalı; model girdisi DEĞİL, MK-1)
  maclar/<kod>/<klasör>__fiyat_karsilastirma_<kod>.json, …__dogrulama_<kod>.json   karşılaştırma ve dışa aktarımlar
  maclar/<kod>/sonuc.json              gerçekleşen sonuç (football-data.org, normal süre), bulunduğunda
  gunluk/<klasör>.json                 her bültenin oransız maç listesi ve özeti (küçük)
  MANIFEST.sha256                      bütün hafıza dosyalarının özetleri

Saklama (`plan` → yalnızca öneri; `uygula` ancak açıkça istenirse):
  - Son SAKLAMA_GUN günün (TR, bugün dahil) bültenleri tutulur; her gün için en yeni başarılı çekim mutlaka kalır.
  - Aynı gün içindeki eski kopyalar, fiyat karşılaştırmasında kullanılmadıysa ve AYNI_GUN_SAAT saatten eskiyse silinebilir.
  - Başarısız çekimler silinebilir.
  - Daha eski tam bültenler, hafızaya çıkarım yapılıp SHA-256 ile doğrulandıktan sonra silinebilir.
  - KORUNAN klasörlere (tahminler, arastirma, raporlar, model, kaynak_veri, yedek, guncel, …) asla dokunulmaz.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fi import is_akisi as I

from . import veri as V

SAKLAMA_GUN = 3
AYNI_GUN_SAAT = 6
KORUNAN = ("tahminler", "arastirma", "raporlar", "model", "kaynak_veri", "yedek", "guncel", "denetim", "hafiza",
           "onbellek", "veri_uygunlugu", "veri_butunlugu", "arayuz_onizleme", "ligler_arasi", "vakalar", "fdorg_test")
KLASOR = re.compile(r"bulten_(\d{8})_(\d{6})")


def _kok(kok: Path | None) -> Path:
    return Path(kok or V.OUTPUT)


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _yaz(p: Path, veri) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    b = json.dumps(veri, ensure_ascii=False, indent=1, default=str).encode("utf-8")
    p.write_bytes(b)
    return hashlib.sha256(b).hexdigest()


def _cekim_tr(klasor: Path) -> datetime:
    """Klasör adı Türkiye saatiyle yazılır (nesine_bulletin.py: datetime.now(TR))."""
    m = KLASOR.fullmatch(Path(klasor).name)
    return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(tzinfo=I.TR)


def tum_bultenler(kok: Path | None = None) -> list[Path]:
    """Başarılı ve başarısız bütün bülten klasörleri (eskiden yeniye)."""
    return sorted((p for p in _kok(kok).glob("bulten_*") if p.is_dir() and KLASOR.fullmatch(p.name)), key=lambda p: p.name)


def _basarisiz(k: Path) -> bool:
    return not (k / "mac_oncesi.json").exists() or V._basarisiz(k)


# ------------------------------------------------------------------------------------------------ hafıza kümesi
def hafiza_kodlari(kok: Path | None = None) -> dict[int, list[str]]:
    """Kalıcı hafızaya alınacak maçlar ve nedenleri: donmuş tahmin, haber araştırması, fiyat karşılaştırması."""
    kok = _kok(kok)
    out: dict[int, list[str]] = {}

    def ekle(mac_id: str | None, neden: str):
        if mac_id and str(mac_id).startswith("nesine:") and str(mac_id)[7:].isdigit():
            out.setdefault(int(str(mac_id)[7:]), [])
            if neden not in out[int(str(mac_id)[7:])]:
                out[int(str(mac_id)[7:])].append(neden)
    for k in V.donmus_tahminler(kok / "tahminler"):
        ekle(k["mac_id"], "donmus_tahmin")
    for r in (kok / "arastirma" / "genis_pilot").glob("*/rapor.json"):
        try:
            ekle((json.loads(r.read_text(encoding="utf-8")).get("mac") or {}).get("mac_id"), "haber_arastirmasi")
        except ValueError:
            continue
    for b in tum_bultenler(kok):
        for f in b.glob("fiyat_karsilastirma_*.json"):
            ekle("nesine:" + f.stem.rsplit("_", 1)[1], "fiyat_karsilastirmasi")
    return out


# ------------------------------------------------------------------------------------------------ çıkarım
def cikar(klasor: Path, kok: Path | None = None) -> dict:
    """Bir bültenden hafızaya: günlük oransız liste + hafıza maçlarının tam market/oran anlık görüntüsü +
    karşılaştırma ve dışa aktarım dosyaları. Tekrar çalıştırmak güvenlidir (aynı içerik yeniden yazılmaz)."""
    kok, klasor = _kok(kok), Path(klasor)
    h = kok / "hafiza"
    yazilan = []
    if _basarisiz(klasor):
        return {"klasor": klasor.name, "durum": "basarisiz_cekim", "yazilan": []}
    b = json.loads((klasor / "mac_oncesi.json").read_text(encoding="utf-8"))
    kaynak = b.get("kaynak") or {}
    maclar = b.get("futbol", [])
    gunluk = {"klasor": klasor.name, "cekim_tr": kaynak.get("cekim_tr"), "cekim_utc": kaynak.get("cekim_utc"),
              "ham_sha256": kaynak.get("sha256"), "pencere_tr": b.get("pencere_tr"),
              "mac": len(maclar), "market": sum(len(m.get("marketler") or []) for m in maclar),
              "secenek": sum(len(mk.get("secenekler") or []) for m in maclar for mk in m.get("marketler") or []),
              "maclar": [{k: m.get(k) for k in ("kod", "lig", "lig_kodu", "ev", "deplasman", "baslama_tr")} | {
                  "market_sayisi": len(m.get("marketler") or [])} for m in maclar]}
    p = h / "gunluk" / f"{klasor.name}.json"
    if not p.exists():
        _yaz(p, gunluk)
        yazilan.append(str(p.relative_to(kok)))
    kodlar = hafiza_kodlari(kok)
    for m in maclar:
        if m.get("kod") not in kodlar:
            continue
        d = h / "maclar" / str(m["kod"])
        p = d / f"{klasor.name}.json"
        if not p.exists():
            _yaz(p, {"not": "Zaman damgalı Nesine anlık görüntüsü; olasılık değildir, model girdisi değildir (MK-1).",
                     "bulten": klasor.name, "kaynak": kaynak, "mac": m})
            yazilan.append(str(p.relative_to(kok)))
        for f in list(klasor.glob(f"fiyat_karsilastirma_{m['kod']}.json")) + list(klasor.glob(f"dogrulama_{m['kod']}.json")):
            hedef = d / f"{klasor.name}__{f.name}"
            if not hedef.exists():
                d.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, hedef)
                yazilan.append(str(hedef.relative_to(kok)))
    return {"klasor": klasor.name, "durum": "tamam", "yazilan": yazilan}


def sonuclari_guncelle(kok: Path | None = None) -> list[dict]:
    """Hafıza maçlarının gerçekleşen sonuçları (football-data.org anlık görüntüsü; donmuş tahminden kimlikle)."""
    kok = _kok(kok)
    out = []
    for k in V.donmus_tahminler(kok / "tahminler"):
        try:
            d = I.donmus_oku(Path(k["yol"]))
        except (ValueError, FileNotFoundError):
            continue
        fid = ((d.get("tahmin") or {}).get("mac_kimligi_dogrulama") or {}).get("fd_mac_id")
        lig = I.lig_eslemesi(d.get("lig")) if d.get("lig") else None
        if not (fid and lig):
            continue
        fd = V.mac_durumu_fd(lig, fid, kok / "guncel")
        if fd and fd.get("durum") == "FINISHED" and fd.get("normal_sure_ev") is not None:
            p = kok / "hafiza" / "maclar" / k["mac_id"][7:] / "sonuc.json"
            kayit = {"mac_id": k["mac_id"], "fd_mac_id": fid, "skor_normal_sure": [fd["normal_sure_ev"], fd["normal_sure_dep"]],
                     "ilk_yari": [fd.get("iy_ev"), fd.get("iy_dep")], "kaynak": "football-data.org",
                     "anlik_goruntu": fd.get("anlik_goruntu")}
            if not p.exists():
                _yaz(p, kayit)
            out.append(kayit)
    return out


def manifest(kok: Path | None = None) -> dict:
    kok = _kok(kok)
    h = kok / "hafiza"
    dosyalar = sorted(p for p in h.rglob("*") if p.is_file() and p.name != "MANIFEST.sha256")
    satir = [f"{_sha(p)}  {p.relative_to(h).as_posix()}" for p in dosyalar]
    if dosyalar:
        (h / "MANIFEST.sha256").write_text("\n".join(satir) + "\n", encoding="utf-8")
    return {"dosya": len(dosyalar), "bayt": sum(p.stat().st_size for p in dosyalar)}


def guncelle(kok: Path | None = None) -> dict:
    """Bütün bültenlerden çıkarım + sonuçlar + manifest. Hiçbir şey silinmez."""
    kok = _kok(kok)
    cik = [cikar(b, kok) for b in tum_bultenler(kok)]
    son = sonuclari_guncelle(kok)
    return {"bulten": len(cik), "yeni_dosya": sum(len(c["yazilan"]) for c in cik), "hafiza_maci": len(hafiza_kodlari(kok)),
            "sonuc": len(son), "manifest": manifest(kok)}


# ------------------------------------------------------------------------------------------------ saklama planı
def plan(kok: Path | None = None, simdi: datetime | None = None) -> list[dict]:
    """Her bülten klasörü için karar: tut / sil (gerekçeli). Hiçbir şey silmez."""
    kok = _kok(kok)
    simdi = (simdi or datetime.now(timezone.utc)).astimezone(I.TR)
    bas_gun = (simdi - timedelta(days=SAKLAMA_GUN - 1)).date()
    bl = tum_bultenler(kok)
    gunun_en_yenisi = {}
    for b in bl:
        if not _basarisiz(b):
            gunun_en_yenisi[_cekim_tr(b).date()] = b
    out = []
    for b in bl:
        t = _cekim_tr(b)
        referans = any(b.glob("fiyat_karsilastirma_*.json")) or any(b.glob("dogrulama_*.json"))
        boyut = sum(p.stat().st_size for p in b.rglob("*") if p.is_file())
        if _basarisiz(b):
            karar, neden = "sil", "başarısız çekim (kullanılabilir veri yok)"
        elif t.date() < bas_gun:
            karar, neden = "sil", f"{SAKLAMA_GUN} günlük saklama süresi doldu (önce hafızaya çıkarım)"
        elif gunun_en_yenisi.get(t.date()) == b:
            karar, neden = "tut", "günün en yeni başarılı bülteni"
        elif referans:
            karar, neden = "tut", "fiyat karşılaştırmasında kullanıldı (saklama süresi içinde)"
        elif simdi - t < timedelta(hours=AYNI_GUN_SAAT):
            karar, neden = "tut", f"aynı gün daha yeni çekim var ama {AYNI_GUN_SAAT} saatten yeni"
        else:
            karar, neden = "sil", "aynı gün daha yeni başarılı çekim var (önce hafızaya çıkarım)"
        out.append({"klasor": b.name, "cekim_tr": t.isoformat(), "karar": karar, "neden": neden, "mb": round(boyut / 2**20, 1)})
    return out


def uygula(kok: Path | None = None, simdi: datetime | None = None) -> dict:
    """Planı uygular: her silinecek bülten için önce çıkarım ve doğrulama; yalnızca output/bulten_* silinir."""
    kok = _kok(kok).resolve()
    silinen, atlanan = [], []
    for p in plan(kok, simdi):
        if p["karar"] != "sil":
            continue
        b = (kok / p["klasor"]).resolve()
        if b.parent != kok or not KLASOR.fullmatch(b.name) or b.name.split("_")[0] in KORUNAN:
            atlanan.append({"klasor": p["klasor"], "neden": "güvenlik: beklenmeyen yol"})
            continue
        c = cikar(b, kok)
        if c["durum"] == "tamam":
            beklenen = [kok / "hafiza" / "gunluk" / f"{b.name}.json"]
            if not all(x.exists() for x in beklenen):
                atlanan.append({"klasor": b.name, "neden": "hafıza çıkarımı doğrulanamadı"})
                continue
        shutil.rmtree(b)
        silinen.append(p)
    return {"silinen": silinen, "atlanan": atlanan, "manifest": manifest(kok)}


# ------------------------------------------------------------------------------------------------ oturumlar arası hafıza
HAFIZA_DALI = "arastirma-hafizasi"
HAFIZA_ICERIGI = ("hafiza", "tahminler", "arastirma", "raporlar", "denetim")


def dal_paketi(hedef: Path, kok: Path | None = None) -> dict:
    """Hafıza dalına konacak içeriği `hedef` klasörüne kopyalar (yalnızca araştırma hafızası; ham bülten, Excel,
    önbellek, kaydedilmiş ham web sayfaları (`sayfalar/`, .html: üçüncü taraf içerik ve gömülü anahtarlar içerebilir)
    ve gizli bilgi yok). Git işlemi yapmaz."""
    kok, hedef = _kok(kok), Path(hedef)
    n = 0
    for ad in HAFIZA_ICERIGI:
        k = kok / ad
        if not k.exists():
            continue
        for p in k.rglob("*"):
            if p.is_file() and p.suffix in (".json", ".md", ".jsonl", ".sha256", ".txt") and "sayfalar" not in p.parts:
                h = hedef / "output" / p.relative_to(kok)
                h.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, h)
                n += 1
    return {"dosya": n}


def dal_geri_yukle(kaynak: Path, kok: Path | None = None) -> dict:
    """Hafıza dalının çalışma kopyasından (`kaynak/output/...`) yerel output/ altına geri yükler; var olan dosyanın
    ÜZERİNE YAZMAZ (aynıysa atlar, farklıysa çakışma), tahminler/kayit.jsonl satır bazında birleştirilir."""
    kok, kaynak = _kok(kok), Path(kaynak) / "output"
    r = {"yazilan": 0, "ayni": 0, "cakisma": []}
    for p in sorted(kaynak.rglob("*")):
        if not p.is_file():
            continue
        hedef = kok / p.relative_to(kaynak)
        if hedef.name == "kayit.jsonl" and hedef.parent.name == "tahminler":
            mevcut = hedef.read_text(encoding="utf-8").splitlines() if hedef.exists() else []
            yeni = [s for s in p.read_text(encoding="utf-8").splitlines() if s.strip() and s not in mevcut]
            hedef.parent.mkdir(parents=True, exist_ok=True)
            with open(hedef, "a", encoding="utf-8") as f:
                f.write("".join(s + "\n" for s in yeni))
            r["yazilan"] += bool(yeni)
            continue
        if hedef.exists():
            if hedef.read_bytes() == p.read_bytes():
                r["ayni"] += 1
            else:
                r["cakisma"].append(str(hedef.relative_to(kok)))
            continue
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, hedef)
        r["yazilan"] += 1
    return r


# ------------------------------------------------------------------------------------------------ git dalı (yerel)
def _git(*arg, cwd=None) -> str:
    import subprocess
    r = subprocess.run(["git", *arg], cwd=cwd or V.KOK, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(arg)}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def dal_hazirla(kok: Path | None = None, mesaj: str | None = None) -> dict:
    """Hafıza paketini yerel `arastirma-hafizasi` dalına commit eder (yetim dal; kod dallarından bağımsız).
    PUSH YAPMAZ. Push ayrı ve kullanıcı onayıyla: git push origin arastirma-hafizasi"""
    kok = _kok(kok)
    wt = kok / ".hafiza_dali"
    var = bool(_git("branch", "--list", HAFIZA_DALI))
    if not wt.exists():
        if var:
            _git("worktree", "add", str(wt), HAFIZA_DALI)
        else:
            _git("worktree", "add", "--detach", str(wt))
            _git("checkout", "--orphan", HAFIZA_DALI, cwd=wt)
            _git("rm", "-rfq", ".", cwd=wt)
    for p in list((wt / "output").glob("*")) if (wt / "output").exists() else []:
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    r = dal_paketi(wt, kok)
    (wt / "README.md").write_text("# Football Intelligence araştırma hafızası\n\nÖzel veri dalı. Kod yok; yalnızca "
                                  "araştırma hafızası (tahminler, haber araştırmaları, raporlar, hafıza anlık görüntüleri). "
                                  "Ham bülten, önbellek ve gizli bilgi içermez. Geri yükleme: "
                                  "`PYTHONPATH=lib python3 -m uygulama.sohbet hafiza-dali geri`.\n", encoding="utf-8")
    _git("add", "-A", cwd=wt)
    if not _git("status", "--porcelain", cwd=wt):
        return {"dal": HAFIZA_DALI, "dosya": r["dosya"], "commit": _git("rev-parse", "HEAD", cwd=wt), "degisiklik": False}
    _git("-c", "user.name=Football Intelligence", "-c", "user.email=noreply@anthropic.com", "commit", "-q", "-m",
         mesaj or f"Araştırma hafızası {datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ}", cwd=wt)
    return {"dal": HAFIZA_DALI, "dosya": r["dosya"], "commit": _git("rev-parse", "HEAD", cwd=wt), "degisiklik": True}


def dal_geri(kok: Path | None = None, uzak: bool = True) -> dict:
    """origin/arastirma-hafizasi (ya da yerel dal) içeriğini output/ altına üzerine yazmadan geri yükler."""
    import tempfile
    kok = _kok(kok)
    ref = HAFIZA_DALI
    if uzak:
        _git("fetch", "-q", "origin", f"{HAFIZA_DALI}:refs/remotes/origin/{HAFIZA_DALI}")
        ref = f"origin/{HAFIZA_DALI}"
    gecici = Path(tempfile.mkdtemp(prefix="fi_hafiza_"))
    try:
        import io
        import subprocess
        import tarfile
        arsiv = subprocess.run(["git", "archive", "--format=tar", ref, "output"], cwd=V.KOK, capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(arsiv)) as t:
            t.extractall(gecici, filter="data")
        r = dal_geri_yukle(gecici, kok)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    return {"kaynak": ref, **r}
