---
name: surpriz-analizi
description: Bir maçta favorinin neden zorlanabileceğini araştırır (bağımsız favori, tarihsel taban oranları, 10+10 sürpriz pilotu, zayıf taraf/oyun akışı/kaos savunucuları) ve en önemli sürpriz sinyalini kanıtı ve karşı kanıtıyla raporlar; ayrıca tarihsel sürpriz araştırmasını gösterir. Kullanıcı "en ilginç sürpriz sinyali hangisi", "favori zorlanır mı", "sürpriz riski", "geçmiş sürpriz örnekleri" dediğinde kullan.
---

# Sürpriz analizi

1. `PYTHONPATH=lib python3 -m uygulama.sohbet surpriz KOD` çıktısı şunları verir:
   - **Bağımsız favori** yalnızca donmuş modelden (MS 1/2 kalibreyse). Yoksa favori belirlenmez. Oranla favori belirleme YASAK (MK-1).
   - **Tarihsel taban:** aynı favori kategorisinde beraberlik ve yenilgi sıklığı (büyük 5 lig, 2022–26, 3.725 maç). Kalibre bir modelde sürprizler çoğunlukla bu oranda ve rastgele gerçekleşir.
   - **10+10 pilotun sinyal sıklıkları:** keşif niteliğinde, kör değil; hiçbir sinyal kanıtlanmadı.
2. Sürpriz kontrol listesi (araştırma soruları; olasılığı değiştirmez):
   - Bağımsız favoride kesin eksik ya da ceza, yoğun fikstür, teknik direktör belirsizliği, son maçlarda form düşüşü (rakip gücüne göre).
   - Rakibin stil uyumu, duran top gücü, alçak blok.
   - Konseyden zayıf taraf, oyun akışı ve kaos savunucularının davası (`../mac-analizi/protokol/konsey.md`).
3. Benzer tarihsel örnekler: `output/arastirma/surpriz_pilot_v1/pilot_kodlama_v2.json`. Benzerlik "kanıtlanmış tahmin gücü değildir" diye etiketlenir.
4. Rapor: en önemli tek sinyal + kanıtı (kaynak, tarih) + karşı kanıtı + bunun kaçınılmaz bir belirsizlik mi yoksa doğrulanabilir bir risk mi olduğu.

Daha büyük tarihsel araştırma (30+30, 100+100) yalnızca kullanıcı isterse yapılır: `docs/` ve `lib/fi/model/ON_KAYIT_S.md`.
