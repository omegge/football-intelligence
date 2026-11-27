"""Araştırma/tahmin verisinin yedeği (dışa aktar) ve geri yüklenmesi (içe aktar).

Biçim: tar.gz; içinde `output/<yol>` dosyaları ve `output/yedek/MANIFEST_<zaman>.sha256` (sha256sum biçimi).
Yerelde oluşturulan yedekler (output/yedek/arastirma_yedegi_*.tar.gz) aynı biçimdedir ve buluta yüklenebilir.

İçe aktarma kuralları (veri kaybını ve dondurma ihlalini önlemek için):
  - Manifestteki her dosyanın SHA-256'sı tutmalı; manifest dışı dosya alınmaz.
  - Yalnızca izinli üst klasörler; mutlak yol, '..', bağlantı (symlink/hardlink) ve aygıt dosyası reddedilir.
  - Var olan dosyanın ÜZERİNE YAZILMAZ: aynı içerikse atlanır, farklıysa "çakışma" olarak raporlanır.
  - tahminler/kayit.jsonl birleştirilir (satır bazında, tekrar eklenmez); donmuş tahmin dosyaları SHA ile denetlenir.
"""
from __future__ import annotations

import hashlib
import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from . import veri as V

IZINLI_UST = ("arastirma", "tahminler", "raporlar", "denetim", "guncel", "veri_uygunlugu", "veri_butunlugu",
              "arayuz_onizleme")
BULTEN_DOSYALARI = ("mac_oncesi.json", "kaynak.json")      # ham/ ve Excel yedeğe girmez
EN_FAZLA_BAYT = 80 * 1024 * 1024


class YedekHatasi(ValueError):
    pass


def _dosyalar(kok: Path) -> list[Path]:
    out = []
    for ust in IZINLI_UST:
        d = kok / ust
        if d.is_dir():
            out += [p for p in d.rglob("*") if p.is_file() and not p.is_symlink()]
    for b in V.bultenler(kok):
        out += [b / ad for ad in BULTEN_DOSYALARI if (b / ad).is_file()]
        out += sorted(p for p in b.glob("*.json") if p.name.startswith(("dogrulama_", "fiyat_karsilastirma_")))
    return sorted(set(out))


def yedek_olustur(kok: Path | None = None) -> tuple[bytes, str]:
    kok = Path(kok or V.OUTPUT)
    zaman = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    satirlar = []
    tampon = io.BytesIO()
    with tarfile.open(fileobj=tampon, mode="w:gz") as tar:
        for p in _dosyalar(kok):
            ad = "output/" + p.relative_to(kok).as_posix()
            veri = p.read_bytes()
            satirlar.append(f"{hashlib.sha256(veri).hexdigest()}  {ad}")
            bilgi = tarfile.TarInfo(ad)
            bilgi.size, bilgi.mtime = len(veri), int(p.stat().st_mtime)
            tar.addfile(bilgi, io.BytesIO(veri))
        man = ("\n".join(satirlar) + "\n").encode()
        bilgi = tarfile.TarInfo(f"output/yedek/MANIFEST_{zaman}.sha256")
        bilgi.size, bilgi.mtime = len(man), int(datetime.now().timestamp())
        tar.addfile(bilgi, io.BytesIO(man))
    return tampon.getvalue(), f"fi_yedek_{zaman}.tar.gz"


def _guvenli_hedef(ad: str, kok: Path) -> Path:
    y = PurePosixPath(ad)
    if y.is_absolute() or ".." in y.parts or not y.parts or y.parts[0] != "output" or len(y.parts) < 3:
        raise YedekHatasi(f"güvensiz yol: {ad}")
    ic = y.parts[1:]
    izinli = ic[0] in IZINLI_UST or (ic[0].startswith("bulten_") and V.BULTEN_DESENI.fullmatch(ic[0]) and len(ic) == 2
                                      and (ic[1] in BULTEN_DOSYALARI or ic[1].startswith(("dogrulama_", "fiyat_karsilastirma_"))))
    if not izinli:
        raise YedekHatasi(f"izinli olmayan yol: {ad}")
    hedef = (kok / Path(*ic)).resolve()
    if not str(hedef).startswith(str(kok.resolve()) + "/"):
        raise YedekHatasi(f"kök dışına çıkan yol: {ad}")
    return hedef


def ice_aktar(veri: bytes, kok: Path | None = None) -> dict:
    kok = Path(kok or V.OUTPUT)
    if len(veri) > EN_FAZLA_BAYT:
        raise YedekHatasi("yedek çok büyük")
    try:
        tar = tarfile.open(fileobj=io.BytesIO(veri), mode="r:gz")
        uyeler = tar.getmembers()
    except (tarfile.TarError, OSError, EOFError) as e:
        raise YedekHatasi(f"geçerli bir tar.gz değil: {e}") from None
    manifestler = [m for m in uyeler if m.isfile() and PurePosixPath(m.name).parent == PurePosixPath("output/yedek")
                   and PurePosixPath(m.name).name.startswith("MANIFEST_")]
    if len(manifestler) != 1:
        raise YedekHatasi("yedekte tek bir MANIFEST_*.sha256 olmalı")
    beklenen = {}
    for s in tar.extractfile(manifestler[0]).read().decode("utf-8").splitlines():
        if s.strip():
            oz, ad = s.split("  ", 1)
            beklenen[ad.strip()] = oz.strip()
    rapor = {"yazilan": 0, "ayni_atlanan": 0, "cakisma": [], "reddedilen": [], "kayit_satiri_eklenen": 0}
    yazilacak = []
    for m in uyeler:
        if m is manifestler[0] or m.isdir():
            continue
        if not m.isfile():
            rapor["reddedilen"].append(f"{m.name}: düz dosya değil")
            continue
        if m.name not in beklenen:
            rapor["reddedilen"].append(f"{m.name}: manifestte yok")
            continue
        govde = tar.extractfile(m).read()
        if hashlib.sha256(govde).hexdigest() != beklenen[m.name]:
            raise YedekHatasi(f"SHA-256 uyuşmuyor: {m.name} (yedek bozuk; hiçbir dosya yazılmadı)")
        try:
            hedef = _guvenli_hedef(m.name, kok)
        except YedekHatasi as e:
            rapor["reddedilen"].append(str(e))
            continue
        yazilacak.append((m.name, hedef, govde))
    for ad, hedef, govde in yazilacak:          # bütün SHA'lar tuttuktan sonra yaz
        if hedef.name == "kayit.jsonl" and hedef.parent.name == "tahminler":
            mevcut = hedef.read_text(encoding="utf-8").splitlines() if hedef.exists() else []
            yeni = [s for s in govde.decode("utf-8").splitlines() if s.strip() and s not in mevcut]
            if yeni:
                hedef.parent.mkdir(parents=True, exist_ok=True)
                with open(hedef, "a", encoding="utf-8") as f:
                    f.write("".join(s + "\n" for s in yeni))
            rapor["kayit_satiri_eklenen"] += len(yeni)
            continue
        if hedef.exists():
            if hedef.read_bytes() == govde:
                rapor["ayni_atlanan"] += 1
            else:
                rapor["cakisma"].append(ad)
            continue
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes(govde)
        rapor["yazilan"] += 1
    # donmuş tahminlerin bütünlüğü (içe aktarılanlar dahil)
    from fi import is_akisi as I
    bozuk = []
    for k in V.donmus_tahminler(kok / "tahminler"):
        try:
            I.donmus_oku(Path(k["yol"]))
        except (ValueError, FileNotFoundError) as e:
            bozuk.append(f"{k['dosya']}: {e}")
    rapor["donmus_bozuk"] = bozuk
    return rapor


def depolama_durumu(kok: Path | None = None) -> dict:
    import os
    import shutil
    kok = Path(kok or V.OUTPUT)
    kok.mkdir(parents=True, exist_ok=True)
    d = shutil.disk_usage(kok)
    return {"kok": str(kok), "kalici": os.environ.get("FI_KALICI_DEPOLAMA") == "1",
            "bos_mb": d.free // 2**20, "toplam_mb": d.total // 2**20,
            "donmus_tahmin": len(V.donmus_tahminler(kok / "tahminler")), "bulten": len(V.bultenler(kok))}


def json_ozet(r: dict) -> str:
    return json.dumps(r, ensure_ascii=False, indent=1)
