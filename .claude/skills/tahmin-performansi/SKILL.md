---
name: tahmin-performansi
description: Donmuş bağımsız tahmin arşivini SHA-256 bütünlüğüyle listeler, gerçekleşen sonuçlarla (football-data.org, normal süre) log-kayıp ve Brier puanlarını gösterir ve ileriye dönük doğrulamanın durumunu raporlar. Kullanıcı "tahmin performansı", "arşivi göster", "modellerimiz nasıl gidiyor", "dondurulan tahminler" dediğinde kullan.
---

# Tahmin performansı

1. Sonuçların güncel olması için önce `PYTHONPATH=lib python3 -m fi.kaynaklar.guncel guncelle` çalıştır. Bu komut football-data.org ücretsiz planına 9 istek gönderir; sık çalıştırma.
2. `PYTHONPATH=lib python3 -m uygulama.sohbet performans` çıktısında şunlar var: her donmuş tahmin için bütünlük, sonuç, puanlanan market sayısı, ortalama log-kayıp ve Brier.
3. Rapor:
   - Örneklem küçüklüğünü açıkça söyle. İleriye dönük değerlendirme için ≥ 100 puanlanmış maç gerekir.
   - Tek maçtan ders çıkarma.
   - Bir donmuş tahmin SHA uyuşmazlığı verirse bunu kritik bulgu olarak bildir.
4. Model kalibrasyonunun geçmiş değerlendirmeleri:
   - `veri/model_kapsami.json` (kaynaklar bölümü);
   - E2 sınaması `output/model/e2_sinama_*`;
   - E3 sınaması `output/model/e3/e3_sinama_*`.
