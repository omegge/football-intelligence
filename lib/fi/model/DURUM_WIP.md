# DURUM: YARIM ÇALIŞMA (WIP) — TAMAMLANMADI, TEST EDİLMEDİ

Tarih: 23.11.2026. Bu klasördeki model kodu ve `lib/fi/kaynaklar/openfootball.py` **hiç çalıştırılmadı** (yalnızca
sözdizimi kontrolü yapıldı), **testi yok** ve **tahmin üretmek için kullanılmamalı**. `main` dalına alınmadan önce
tamamlanması, testlerinin yazılması ve backtest sonuçlarının kullanıcıya sunulması gerekir.

## Dosyalar
| Dosya | Durum |
|---|---|
| `lib/fi/kaynaklar/openfootball.py` | OpenFootball JSON okuyucusu + veri anlık görüntüsü (commit, dosya SHA-256). Test yok. Takım adı normalleştirmesinin sezon içinde çakışma üretmediği doğrulanmadı. |
| `lib/fi/model/__init__.py` | Paket açıklaması; `pazar_destegi()` korner/kart/oyuncu/özel pazarlar için "hesaplanamaz" döndürür. Test yok. |
| `lib/fi/model/optim.py` | Bağımlılıksız Nelder–Mead ve altın oran araması (scipy kurulu değil). Test yok. |
| `lib/fi/model/elo.py` | Özgün Elo (gol farkı çarpanı, ev avantajı, sezon başı ortalamaya çekme, yeni takıma düşenlerin ortalaması) + sıralı lojistik 1X2 dönüşümü (yalnızca geçmiş sezonlarla kestirim). Test yok; hiperparametreler (K=20, H=60, λ=0.2) doğrulanmadı; sıralı lojistik kestirimi saf Python döngüsü — hızı ölçülmedi. |
| `lib/fi/model/goller.py` | Zaman ağırlıklı, cezalandırılmış Poisson (IRLS) + Dixon–Coles ρ (iki aşamalı). Test yok; ξ, pencere, ceza ve yeni takım önseli (hücum ×0.8, savunma ×1.2 — DOĞRULANMAMIŞ VARSAYIM) ayarlanmadı. |

## Bilinen sorunlar (düzeltilecek)
1. `goller.py` — Dixon–Coles ρ üst sınırı hesabına yanlışlıkla `1/λ_ev` ve `1/λ_dep` eklenmiş; bunlar alt sınır
   koşullarıdır. Doğru kısıtlar: ρ < 1, ρ < 1/(λ_ev·λ_dep), ρ > −1/λ_ev, ρ > −1/λ_dep.
2. `goller.py` — her kestirimde yoğun tasarım matrisi kuruluyor; backtest süresi ölçülmedi.
3. `elo.py` — sıralı lojistik parametrelerinin sezon başında yeniden kestirimi için en az 200 geçmiş maç şartı keyfî.

## Henüz yazılmayanlar
- `metrikler.py` (log-loss, Brier, RPS, kalibrasyon, bootstrap), `surpriz.py` (sürpriz tespiti, yanlış alarm oranı, AUC),
  `backtest.py` (yürüyen test motoru + sızıntı denetimleri), `calistir.py` (prototip komut satırı).
- `tests/test_model.py` (sentetik veriyle parametre geri kazanımı, olasılık toplamları, sızıntı/karıştırma testleri,
  MK-1 oran reddi, "hesaplanamaz" pazarlar).
- Prototip backtest: İngiltere Premier Lig (`en.1`), 2010-11 ısınma; ayar 2011-12–2017-18; doğrulama 2018-19–2020-21;
  test 2021-22–2025-26 (2026-27 eksik sezon dahil değil).

## Kurallar
MK-1 geçerli: Nesine oranları hiçbir model girdisine giremez. Veri kaynağı yalnızca OpenFootball (CC0, git klonu).
