"""Bağımsız olasılık modelleri (MK-1: Nesine oranları hiçbir model girdisine giremez).

  optim       : küçük, bağımlılıksız Nelder–Mead ve altın oran araması (scipy kurulu değil)
  elo         : özgün Elo benzeri takım gücü + sıralı lojistik (1X2) dönüşümü
  goller      : zaman ağırlıklı Poisson (Maher) ve Dixon–Coles; skor matrisi; gol pazarları
  metrikler   : log-loss, Brier, RPS, kalibrasyon, bootstrap
  surpriz     : model favorisine göre sürpriz tespiti, yanlış alarm oranı, AUC
  backtest    : kronolojik (yürüyen) test motoru ve sızıntı korumaları
  calistir    : prototip backtest komut satırı
"""

DESTEKLENMEYEN_PAZARLAR = {"korner", "kart", "oyuncu", "ozel", "birlesik_korner_kart"}


def pazar_destegi(pazar: str) -> dict:
    """Verisi ya da doğrulanmış modeli olmayan pazarlarda olasılık üretilmez (MK-1, madde 6)."""
    if pazar in DESTEKLENMEYEN_PAZARLAR:
        return {"pazar": pazar, "durum": "hesaplanamaz",
                "neden": "eksik veri/model: açık lisanslı kaynaklarda bu pazar için güncel veri yok"}
    return {"pazar": pazar, "durum": "destekleniyor"}
