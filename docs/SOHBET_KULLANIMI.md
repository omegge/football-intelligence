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

## Kurallar
- MK-1: oranlar bağımsız olasılığa girmez; önce dondurma, sonra karşılaştırma.
- Oran tarafsızlığı: yüksek oran otomatik riskli, düşük oran otomatik güvenli değildir.
- Kalibre olmayan markette yüzde ya da EV verilmez.
- Asıl soru: destekleyen ve karşıt kanıtlar neler, bu ihtimal neden araştırmaya değer?
