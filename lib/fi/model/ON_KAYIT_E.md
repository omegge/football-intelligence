# E aşaması — önceden kayıt (değerlendirme çalıştırılmadan önce yazıldı, 26.11.2026)

Amaç: Gol modellerinden (Poisson, Dixon–Coles) türetilen marketlerin HER BİRİNİ ayrı ayrı, zaman sıralı olarak sınamak;
bütün marketlerin aynı ortak skor dağılımından tutarlı türetildiğini denetlemek. Parametre ayarı YAPILMAZ.

## Veri
OpenFootball (CC0). Değerlendirme ligleri: **fr.1, nl.1, pt.1, de.2, es.2** — bu projede daha önce hiçbir model
değerlendirmesinde ya da parametre seçiminde kullanılmadı. Değerlendirme dönemi: 2019-07-01 sonrası bütün skorlu maçlar
(kaynağın son skorlu tarihine kadar); öncesi yalnızca eğitim/ısınma. Sert tarih tutarsızlığı olan sezon olursa okunmaz
ve raporlanır.

## Modeller (parametreler D aşamasıyla aynı, değiştirilmez)
GolModeli ξ = 0,003, pencere 1095 gün, ceza 2,0, yeni takım önseli (0,8; 1,2); Dixon–Coles ve aynı kestirimin Poisson
görünümü. Skor matrisi 0–10 gol. MK-1: bahis oranı yok.

## Taban
Her market için aynı ligde, tahmin tarihinden ÖNCE oynanmış bütün maçlardaki olay sıklığı (genişleyen pencere).

## Marketler
1X2 (H, D, A); çifte şans (1X, 12, X2); toplam gol alt/üst 0,5–4,5; ev ve deplasman gol alt/üst 0,5 ve 1,5 (2,5);
karşılıklı gol; gol aralığı 0–1, 2–3, 4–5, 6+; tek/çift; MS ve 2,5 alt/üst (6); MS ve KG (6); ev handikap −1 (3 yollu);
doğru skor 0-0, 1-0, 0-1, 1-1, 2-0, 0-2, 2-1, 1-2, 2-2.

## Ölçütler ve karar kuralları
- Her ikili olay için log loss, Brier, ECE (10 eşit genişlikli kutu), taban farkı ve tarih kümeli bootstrap %95 GA.
- E1 "bilgi taşıyor": model − taban log loss farkının GA üst sınırı < 0.
- E2 "kalibre": ECE ≤ 0,02 ve kutu başına n ≥ 30 olan kutularda |tahmin − gerçekleşen| ≤ 0,05.
  Bu iki koşuldan biri sağlanmazsa market "kalibrasyon sorunu" olarak işaretlenir.
- E3 DC − Poisson farkı her market için raporlanır; düşük skor marketlerinde (0-0, 1-1, 1,5 alt, KG yok) DC'nin daha iyi
  olacağı ÖNCEDEN BEKLENMEZ (D aşamasında H1 ertelendi); yalnızca ölçülür.
- Tutarlılık: her maç için Σ olasılık = 1, ÇŞ = bileşen toplamları, alt/üst tümleyen, alt(c) çizgiyle artan,
  MS&AÜ bileşenleri toplamı MS; tolerans 1e-9. Tek ihlal = hata.
- Olay sıklığı < %2 ya da > %98 olan market raporlanır ama E1/E2 kararı verilmez (yetersiz olay).
