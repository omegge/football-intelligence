# E2 aşaması — yeni gol modeli ön kaydı (sınama verisi açılmadan önce yazıldı, 26.11.2026)

Gerekçe: E aşamasında (ON_KAYIT_E.md) toplam gol alt/üst, gol aralığı ve KG marketleri frekans tabanını geçmedi;
tahminler aşırı yayılmıştı (düşük tahminler gerçekleşenden düşük, yüksekler yüksek) ve ortalama 1,5–2,5 puan düşüktü.

## Veri ayrımı
- GELİŞTİRME (yalnızca model ve parametre seçimi): fr.1, nl.1, pt.1, de.2, es.2; 2019-07-01 sonrası (E'nin verisi;
  E sonuçları bu verinin artık "görülmüş" olduğunu gösterir, bu yüzden burada başarı iddiası yapılmaz).
- SINAMA (tek çalıştırma, seçim bittikten sonra): **en.2, at.1, be.1, sco.1, tr.1, gr.1**; 2019-07-01 sonrası bütün
  okunabilir maçlar; en.2 için football-data.org 2026-27 (season=2026) bitmiş maçları eklenir. Bu liglerin maç sonu gol
  marketleri bu projede hiçbir değerlendirmede kullanılmadı. Sert tarih tutarsızlığı olan sezonlar okunmaz.
  Not: be.1/sco.1/tr.1/gr.1'de 2021-22…2023-24 kaynakta yok; pencere (1095 gün) sonrası eğitim verisi azalır —
  bütün modeller için aynı koşul, raporda gösterilir.

## Aday modeller (MK-1: oran yok)
- M0 Poisson (E ayarı: ξ 0,003, pencere 1095, ceza 2,0, önsel 0,8/1,2)
- M1 Dixon–Coles (aynı kestirim + ρ)
- M2 Düzenlileştirilmiş Poisson: ceza ∈ {2, 4, 8, 16}, geliştirmede seçilir
- M3 Hiyerarşik büzülme (lig ortalamasına): T = λ_ev + λ_dep, μ = ligin tahmin tarihinden önceki 365 gündeki maç
  başı gol ortalaması; T' = μ·(1 + b) + w·(T − μ); λ'ler T'/T ile ölçeklenir (gol farkı oranı korunur).
  w ∈ {0,30; 0,35; …; 1,00}, b ∈ {−0,06; −0,04; …; +0,06}, geliştirmede seçilir (M2'nin seçilen cezası üzerinde).
- M4 Alternatif dağılım: M3 λ'leriyle takım başına negatif binom, r ∈ {5, 10, 20, 40}; geliştirmede seçilir.
Ortak skor matrisi her modelde 0–10; bütün marketler bu matristen (tutarlılık denetimi zorunlu).

## Seçim kuralı (yalnızca geliştirme)
Ölçüt: gol marketleri kümesi {AU0,5…4,5 üst, KG var, gol aralığı 0–1, 2–3, 4–5, 6+} ortalama log loss.
Seçilen aday = en düşük ölçüt; ancak 1X2 ortalama log loss'u M0'dan 0,001'den fazla kötüleşen aday elenir.
M1 (DC) yalnızca karşılaştırma içindir (D/E'de 0-0'da kötü).

## Sınama ve karar kuralları
Her market için: seçilen aday vs M0 vs taban (ligde tarih öncesi frekans). Güven aralığı: **lig-sezon kümeli**
bootstrap (2.000). Market "bilgi taşıyor" = aday − taban log loss GA üst sınırı < 0; "kalibre" = havuz ECE ≤ 0,02 ve
n ≥ 30 kutularda |tahmin − gerçekleşen| ≤ 0,05 ve her sınama liginde ECE ≤ 0,04. "İyileşme" = aday − M0 GA üst
sınırı < 0. Bir market ancak "bilgi taşıyor" VE "kalibre" ise günlük kapsamda olasılık alabilir; aksi hâlde
hesaplanamaz. Sınama sonucuna göre hiçbir parametre değiştirilmez.
