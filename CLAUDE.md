# Football Intelligence

Kişisel futbol araştırma ve bağımsız olasılık analizi sistemi. Yalnızca futbol.

## Çalışma biçimi

**Asıl soru (her analizde):** "Bu bahis sonucunun gerçekleşmesini destekleyen somut kanıtlar nelerdir, karşıt kanıtlar nelerdir ve bu ihtimal neden araştırmaya değerdir?" Amaç yüksek oranı haklı çıkarmak değil; iki yönü de araştırıp en güçlü gerekçeli seçenekleri bulmaktır. Nesine oranları şirket marjı içerir ve gerçek olasılık değildir. Oranlar yalnızca marketleri keşfetmek, piyasa görüşünü anlamak ve (geçerli model varsa) fiyat karşılaştırmak için kullanılır. EV ya da fiyat avantajı ZORUNLU değildir: yalnızca kalibre bir bağımsız olasılık varsa ve belirsizliğiyle birlikte gösterilir.

Football Intelligence ayrı bir uygulama değildir. Kullanıcı Claude Code'da Türkçe konuşur. Claude şunları birleştirerek sonucu doğrudan sohbette sunar:
- proje Skill'leri (`.claude/skills/`);
- Python komutları (`PYTHONPATH=lib python3 -m uygulama.sohbet …`);
- kendi web araştırması (WebSearch; izinli hostlarda sayfa okuma).

Nesine bülteni ana maç havuzudur. Web arayüzü (`uygulama/sunucu.py`) ve Render hazırlığı korunur ama kullanılmaz.

| Kullanıcı der ki | Yapılacak |
|---|---|
| "Bülteni çek", "Bugünün bültenini yenile", "Nesine maçlarını getir", "… tarihli bülteni çek" | `football-bulletin-fetch`: `sohbet bulten [--gun]` → sayılar + maç listesi sohbette |
| "Bütün maçları tara", "yüksek oranlı gerekçeli ihtimalleri bul", "favorilerin zorlanabileceği maçlar", "yüksek fiyatlı özel marketler" | `bulten-tara`: `sohbet tara` → önceliklendirme → kısa web eleme → aday raporu |
| "Şu maçı araştır / derinlemesine incele", "X–Y analiz" | `mac-analizi`: `mac` → `dondur` (model varsa) → haber → uzman notları → konsey → `karsilastir` → `marketler` |
| "Haberleri araştır", "diğer siteler/analistler ne diyor", "sakatlık durumu" | `haber-arastir` (+ `sohbet haber-kaydet`) |
| "En ilginç sürpriz sinyali", "favori zorlanır mı" | `surpriz-analizi` (`sohbet surpriz`) |
| "Bu maçın marketlerini incele", "200'den fazla marketi incele", "eşdeğer marketlerde en yüksek fiyat" | `market-incele` (`sohbet karsilastir`, `sohbet marketler`) |
| "Tahmin performansı", "arşiv" | `tahmin-performansi` (`sohbet performans`) |
| "Araştırma hafızası", "önceki araştırmalar" | `sohbet hafiza [--guncelle]` (çıkarım, sonuç, manifest; silme yok) |
| "Eski bültenleri temizle" | `sohbet temizle` (yalnızca plan); `--uygula` YALNIZCA kullanıcı açıkça isterse |
| "Hafızayı kaydet / geri getir" | `sohbet hafiza-dali hazirla` (yerel özel dal; push kullanıcı onayıyla) / `hafiza-dali geri` |
| "Arayüzü aç" (yalnızca açıkça istenirse) | `PYTHONPATH=lib python3 -m uygulama` (yerel, `docs/V1_ARAYUZ.md`) |

Oran tarafsızlığı:
- Oran bir eleme ölçütü değildir.
- Yüksek oran otomatik riskli, düşük oran otomatik güvenli sayılmaz.
- Favori ve sürpriz seçenekleri aynı titizlikle incelenir.
- Olayın olasılığı (yalnızca bağımsız model) ile fiyatın cazibesi ayrı değerlendirilir.
- Gerekçesi güçlü ama olasılığı hesaplanamayan seçenekler "hesaplanamaz" etiketiyle araştırma adayı olarak kalır.

## Değişmez kurallar
1. Bot korumasını ya da erişim engelini aşma; tarayıcı taklidi, Playwright/Selenium, çerez kullanma. Engel varsa dur ve raporla.
2. Otomatik alt ajan runner'ı başlatma (`opencode`, `codex`, `claude -p`). Footy-Skills protokolü (uzmanlar, konsey, karar verici) aynı oturumda Claude tarafından adım adım uygulanır (`.claude/skills/mac-analizi/`).
3. Ücretli API kullanma; paket yükleme (mevcut kütüphaneler: requests, pandas, numpy, openpyxl, xlsxwriter).
4. **MK-1 Oran bağımsızlığı (değişmez modelleme kuralı; ayrıntı `docs/MODEL_KURALLARI.md`).**
   - Nesine oranları; favori belirleme, takım gücü değerlendirme, maç sonucu tahmini ve olasılık hesaplamada
     KESİNLİKLE kullanılmaz. Favori ve sürpriz adayları yalnızca bağımsız futbol verileriyle belirlenir.
   - Oranlardan ima edilen olasılıklarla bağımsız tahmin düzeltilmez, ağırlıklandırılmaz, kalibre edilmez.
   - Sıra: (1) geçmiş performans, rakip kalitesi, güncel haberler, kadro, taktik ve doğrulanmış istatistiklerden tahmin;
     (2) tahmini zaman damgası + SHA-256 ile dondur; (3) ANCAK SONRA Nesine oranlarını aç ve fiyat karşılaştırması yap.
   - Aynı olayın farklı Nesine pazarlarındaki fiyatları matematiksel olarak karşılaştırılabilir; ama bu fiyat oranları
     gerçek ya da bağımsız (koşullu) olasılık olarak SUNULMAZ.
   - Yeterli veri ya da doğrulanmış model olmayan (özel) pazarlarda olasılık uydurulmaz: "hesaplanamaz" denir.
5. Her veri için kaynak, veri tarihi ve doğrulama zamanı göster; veri yoksa sayı uydurma, "veri yok" de.
6. Kullanıcı açıkça istemeden kupon hazırlama ve bütün maçları ayrıntılı analiz etmeye başlama. Kupon istense bile
   `dogrulanmamis_eslesme` / `isim_celiskisi` işaretli maçları ve `oynanabilirlik` değeri `oynanabilir` olmayan
   oranları (ör. `durumu_dogrulanmamis`, market durumu MS≠1 ya da eksik) kupona alma; nedenini kullanıcıya söyle.
7. Hiçbir pazara doğrulanmamış "yüksek güven" verme.

## Çıktılar ve araştırma hafızası
`output/` git dışıdır.
- **Kalıcı araştırma hafızası:** `output/hafiza/`, `output/tahminler/`, `output/arastirma/`, `output/raporlar/`.
- **Bültenler geçicidir.** Son 3 gün tutulur; daha eski tam bültenler ancak hafızaya çıkarım ve SHA-256 doğrulamasından sonra, kullanıcı isterse silinir.
- **Oturumlar arası:** aynı özel depoda kod içermeyen `arastirma-hafizasi` dalı. Push kullanıcı onayıyla yapılır.
- **Hafıza dalına girmeyenler:** ham bülten, Excel, önbellek ve kaydedilmiş ham web sayfaları (gömülü üçüncü taraf anahtarları içerebilir).
