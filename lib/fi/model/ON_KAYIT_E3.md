# E3 aşaması — zaman sıralı güç farkı ve toplam gol düzeltmesi (ön kayıt)

Yazıldı: 27.11.2026, sınama liglerinin E2 kayıtları üretilmeden ve hiçbir E3 sonucu görülmeden önce. MK-1: oran yok.
Bu ön kayıt E2'yi (ON_KAYIT_E2.md; ceza 16, M3 w 0,65 b 0) değiştirmez; E3 E2'nin λ'larının üstüne kurulur.

## Gerekçe (E2 sınamasından)
- MS_1/MS_2: uçlarda sistematik eksik güven. Güç farkı fazla büzülmüş: düşük olasılık kutuları gerçekleşenden yüksek,
  yüksek olasılık kutuları düşük.
- Lig bazında ECE yüksek. Toplam gol düzeyi sezon içinde kayıyor (Championship 2026-27).

## Model (yalnızca tahmin tarihinden ÖNCEKİ aynı lig maçlarıyla; geleceğe bakış yok)
E2 λ'ları (M3 sonrası): T = λ_ev + λ_dep, d = ln(λ_ev / λ_dep).

**A — güç farkı ölçeği ve ev kayması:**
- d' = γ·d + δ; λ_ev' = T·e^{d'}/(1+e^{d'}), λ_dep' = T/(1+e^{d'}). T korunur.
- γ ∈ {0,80; 0,85; …; 1,60} ve δ ∈ {−0,20; −0,15; …; +0,20} ızgarasında seçilir.
- Ölçüt: aynı ligde [t − 730 gün, t) aralığındaki E2 kayıtlarında 1X2 log-olabilirliği (bağımsız Poisson matris).
- Yeniden kestirim takvim ayı başına en fazla bir kez yapılır (ayın ilk maç gününde).
- Pencerede 300'den az maç varsa γ = 1, δ = 0.

**B — sezon içi toplam düzeyi:**
- Aynı ligin son K maçında G = gerçekleşen toplam gol, P = (A sonrası, B öncesi) tahmini toplam.
- κ = 1 + s·(G/P − 1); T'' = κ·T. Oran (d') korunur.
- K maçtan azsa κ = 1.
- K ∈ {100, 150, 250}, s ∈ {0; 0,25; 0,5; 0,75; 1} geliştirmede seçilir.

Skor matrisi: bağımsız Poisson 0–10 (E2 ile aynı). Bütün marketler bu matristen; tutarlılık denetimi zorunlu.

## Veri ayrımı
- **GELİŞTİRME** (yalnızca K, s seçimi ve A'nın kullanılıp kullanılmayacağı): fr.1, nl.1, pt.1, de.2, es.2. Bunlar E2'nin geliştirme ligleridir.
- **ASIL SINAMA** (tek çalıştırma; seçim bittikten sonra): en.1, de.1, it.1, es.1, en.3, en.4, fr.2, it.2.
  - Bu liglerin gol marketleri hiçbir değerlendirmede kullanılmadı.
  - Açıklama:
    - en.1 D aşamasında (Poisson, 2019–2024) 1X2 ve gol için geliştirme verisi olarak kullanıldı.
    - en.1, de.1, it.1, es.1 için 27.11'de sürpriz pilotu havuzunda Poisson E (ceza 2) favori kazanma kalibrasyonu kategori düzeyinde görüldü.
    - Bu yüzden 1X2 bulguları bu liglerde "tam kör" değildir. Gol marketleri kördür.
  - en.3, en.4, fr.2, it.2'de yalnızca 2024-25 ve sonrası okunabiliyor; kayıtlar kısadır (pencere koşulları bütün modellerde aynı).
- **İKİNCİL** (görülmüş; başarı iddiası yok): E2 sınama ligleri en.2, at.1, be.1, sco.1, tr.1, gr.1.
- Değerlendirme dönemi: kayıtlardaki mu365 tanımlı bütün maçlar (2019-07-01 sonrası, E2 ile aynı).

## Seçim kuralı (yalnızca geliştirme)
- Adaylar: E2 · E2+A · E2+B(K,s) · E2+A+B(K,s).
- Ölçüt: GOL_MARKETLERI ve MS (1X2) ortalama log loss'larının ortalaması.
- Koşul: aday, E2'ye göre MS ortalama log loss'unda ya da gol ortalama log loss'unda 0,001'den fazla kötüleşmez.
- En düşük ölçütlü aday seçilir. E2 seçilirse E3 yoktur ve sınama yapılmaz.

## Sınama ve karar kuralları (E2 ile AYNI; hedef kaydırılmaz)
- Her market için seçilen E3, E2 ve taban (ligde tarih öncesi frekans) karşılaştırılır.
- GA: lig-sezon kümeli bootstrap (2.000).
- "Bilgi taşıyor" = E3 − taban log loss GA üst sınırı < 0.
- "Kalibre" = havuz ECE ≤ 0,02 ve n ≥ 30 kutularda |tahmin − gerçekleşen| ≤ 0,05 ve her ASIL SINAMA liginde ECE ≤ 0,04.
- "E2'ye göre iyileşme" = E3 − E2 GA üst sınırı < 0.
- Kapsam kaydına E3 yalnızca asıl sınama ligleri için eklenir. Bir market ancak "bilgi taşıyor" VE "kalibre" ise kapsamda olur.
- Sınama sonucuna göre hiçbir parametre değiştirilmez.
- Asıl sınama başarısız olursa E3 kullanılmaz. E2 kapsamı değişmez.

## Günlük kullanım (sınama başarılıysa)
γ, δ, κ dondurma anında yalnızca o güne kadarki veriyle hesaplanır ve donmuş kayda yazılır (veri kesimi ile birlikte).
