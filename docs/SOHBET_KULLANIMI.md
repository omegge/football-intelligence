# Football Intelligence'ı Claude Code içinde kullanma

Ayrı uygulama yoktur. Claude Code'da bu depo açıkken Türkçe yazarsınız. Claude:
- proje Skill'lerini (`.claude/skills/`) seçer;
- gerekirse Python komutlarını çalıştırır (`PYTHONPATH=lib python3 -m uygulama.sohbet …`);
- web araştırması yapar;
- sonucu sohbette sunar.

## Örnek istekler
| Siz | Claude ne yapar |
|---|---|
| "Bugünün bültenini çek" | Nesine çekicisi (o TR günü 00:00–23:59), sayılar ve maç listesi |
| "28 Kasım bültenini çek" | aynı, `--gun 2026-11-28` |
| "Bütün maçları tara, gerekçeli yüksek oranlı ihtimalleri bul" | `bulten-tara`: tarama → önceliklendirme (araştırılabilirlik) → kısa web eleme → aday raporu |
| "Favorilerin zorlanabileceği maçlar hangileri?" | aynı; favori yalnızca bağımsız modelden/veriden |
| "Southampton–Middlesbrough'yu derinlemesine araştır" | `mac-analizi`: dondurma → haber → 5 uzman → 7 savunucu → fiyat → özel marketler |
| "Bu maçın bütün marketlerine bak" | `market-incele` |
| "Analistler ne diyor?" | `haber-arastir` |
| "En ilginç sürpriz sinyali hangisi?" | `surpriz-analizi` |
| "Tahmin performansımız nasıl?" | `tahmin-performansi` |

## Bulut oturumu (claude.ai/code) koşulları
1. **Depo:** `omegge/football-intelligence`, dal `feature/football-intelligence-v1` (commit sonrası). `main` kullanılmaz.
2. **Ağ izinleri** (ortam ayarı):
   - `cdnbulten.nesine.com`, `bulten.nesine.com` (bülten);
   - `api.football-data.org` (güncel veri);
   - `github.com` (OpenFootball klonu);
   - web araması Claude'un kendi aracıdır.
3. **Gizli anahtar:** football-data.org anahtarı ortamın "network secrets" kaydında (`X-Auth-Token`). Depoya yazılmaz.
4. **Git dışı veri** (yeni bir bulut oturumunda yoktur):
   - `output/kaynak_veri/openfootball-football.json`: sabit commit `e6744429…`. `KUR_PIP=0 bash deploy/kur.sh` ile kurulur (paket kurmaz, yalnızca klonlar). Ortam kurulum betiğine eklenebilir.
   - `output/tahminler`, `output/arastirma`, `output/bulten_*`: donmuş tahminler, araştırma geçmişi, bültenler. Konteyner geçicidir.
     - Önerilen kalıcılık: oturum sonunda `output/yedek` arşivi ya da onayla ayrı bir veri dalı.
     - Şu an elle yedek alınıyor.
5. **Paket:** numpy, pandas, openpyxl. Varsayılan bulut görüntüsünde kurulu; değilse ortam kurulum betiği gerekir.

## Araştırma hafızası ve saklama
- **Hafıza (`output/hafiza/`):**
  - Araştırılan, dondurulan ya da fiyatı karşılaştırılan her maç için o çekimdeki bütün marketler ve oranlar saklanır. Bunlar zaman damgalı anlık görüntülerdir ve model girdisi değildir.
  - Fiyat karşılaştırması ve dışa aktarım dosyaları.
  - Gerçekleşen sonuç.
  - Her bülten için oransız günlük maç listesi.
  - `MANIFEST.sha256`.
  - Komut: `sohbet hafiza --guncelle`; hiçbir şey silmez.
- **Saklama:**
  - Son 3 günün bültenleri tutulur; her günün en yeni başarılı çekimi mutlaka kalır.
  - Aynı gün içindeki eski kopyalar, karşılaştırmada kullanılmadıysa ve 6 saatten eskiyse silinebilir.
  - Başarısız çekimler silinebilir.
  - Daha eski tam bültenler önce hafızaya çıkarılır, sonra silinebilir.
  - Tahminler, araştırmalar, raporlar, model çıktıları, kaynak verisi ve yedekler hiçbir zaman silinmez.
  - `sohbet temizle` yalnızca planı gösterir. `--uygula` ancak kullanıcı açıkça isterse kullanılır.
- **Oturumlar arası hafıza:**
  - Aynı özel depoda kod içermeyen `arastirma-hafizasi` dalı.
  - `sohbet hafiza-dali hazirla`: yerel commit; push kullanıcı onayıyla.
  - `sohbet hafiza-dali geri`: yeni oturumda geri yükler; var olan dosyanın üzerine yazmaz.
  - Dala ham bülten, Excel, önbellek ve kaydedilmiş ham web sayfaları girmez (sayfalar gömülü üçüncü taraf anahtarları içerebilir).

## Kurallar
- MK-1: oranlar bağımsız olasılığa girmez; önce dondurma, sonra karşılaştırma.
- Oran tarafsızlığı: yüksek oran otomatik riskli, düşük oran otomatik güvenli değildir.
- Kalibre olmayan markette yüzde ya da EV verilmez.
- Asıl soru: destekleyen ve karşıt kanıtlar neler, bu ihtimal neden araştırmaya değer?
