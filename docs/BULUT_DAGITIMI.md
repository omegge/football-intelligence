# Football Intelligence V1 — Render'a güvenli dağıtım

Hedef: Mac'ten ve iPhone'dan açılan tek bir HTTPS adresi, örneğin `https://football-intelligence.onrender.com` (ad Render'da kesinleşir).

## 1. Mimari
- **Sunucu:** Aynı `uygulama/` kodu bulut kipinde (`FI_ORTAM=bulut`) çalışır.
  - Yalnızca Python standart kütüphanesi kullanılır.
  - Matematiksel modeller ve `lib/fi` değişmedi.
- **HTTPS:** TLS'yi Render sonlandırır. Uygulama `X-Forwarded-Proto` http ise HTTPS'e yönlendirir ve HSTS başlığı gönderir.
- **Derleme:** `deploy/kur.sh` çalışır.
  - Bağımlılıkları kurar: numpy, pandas, openpyxl (`requirements.txt`).
  - OpenFootball verisini yereldeki commit'e sabitlenmiş olarak indirir (`e6744429…`).
  - Temiz klonda SOU–MID donmuş tahmini birebir yeniden üretildi (en büyük fark 0,0).
- **Otomatik dağıtım:**
  - `render.yaml` dağıtımı `feature/football-intelligence-v1` dalına bağlar ve `autoDeployTrigger: checksPass` kullanır.
  - GitHub Actions (`.github/workflows/testler.yml`) bütün testleri çalıştırır; yalnızca testler geçerse Render yeni sürümü yayımlar.
  - main dalı kullanılmaz.

## 2. Güvenlik
| Konu | Uygulama |
|---|---|
| Giriş | Tek kullanıcı (FI_KULLANICI). Parola yalnızca PBKDF2-SHA256 özeti olarak saklanır (310.000 tur). |
| Oturum | HMAC-SHA256 ile imzalı çerez, 14 gün geçerli. `HttpOnly; Secure; SameSite=Strict`. |
| CSRF | Her formda oturuma bağlı jeton. `Origin`/`Referer` denetimi yapılır; `Origin: null` reddedilir. |
| Host | Yalnızca FI_IZINLI_HOST ya da Render'ın kendi alan adı (`RENDER_EXTERNAL_HOSTNAME`). Diğer adlar 421 alır. |
| Başlıklar | HSTS, CSP (`script-src 'self'`, `frame-ancestors 'none'`), nosniff, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`. |
| Giriş denemesi | IP başına 15 dakikada 5 deneme; genelde saatte 30. Her yanlış denemede 1 sn bekletme. Sonra 429. |
| İşlem sınırı | Nesine bülteni 10 dakikada 1 · güncel veri (football-data.org) 10 dakikada 1 · dondurma ve fiyat saatte 20 · yedek yükleme saatte 3. Ayrıca aynı anda tek işlem. |
| Boyut | Form en fazla 16 KB, yedek en fazla 80 MB. Aşılırsa 413. |
| Hatalar | Kullanıcıya anlaşılır mesaj gösterilir. Bulutta teknik ayrıntı, dosya yolu ya da traceback gösterilmez. |
| Günlük | Yalnızca yöntem, yol ve durum kodu yazılır. Parola, çerez, form içeriği ve IP yazılmaz (testle denetlenir). |
| Kapalı başarısızlık | Bulut kipinde zorunlu ayarlardan biri eksikse sunucu açılmaz. Girişsiz kip 127.0.0.1 dışına bağlanamaz. |
| Gizli anahtarlar | Yalnızca Render ortam değişkenlerinde tutulur; depoda yoktur. `FD_TOKEN` yalnızca football-data.org isteğinin başlığına eklenir. |
| MK-1 | Değişmedi: liste ve dondurulmamış maç oransız; fiyatlar yalnızca SHA-256'sı doğrulanmış dondurmadan sonra; donmuş tahminin üzerine yazılmaz; pozitif EV "ayrışma" olarak ayrılır. |
| Nesine | Tek GET ve dürüst User-Agent. 401/403/429 ya da HTML yanıtı engel sayılır: aşılmaya çalışılmaz, kullanıcıya bildirilir. |

## 3. Ortam değişkenleri (Render paneli)
| Değişken | Nereden |
|---|---|
| `FI_KULLANICI` | sizin seçtiğiniz giriş adı |
| `FI_PAROLA_OZETI` | `deploy/parola_ozeti.html` dosyasını Safari'de açın. İnternetsiz çalışır ve parolanız cihazdan çıkmaz. Çıkan özeti yapıştırın. |
| `FI_OTURUM_ANAHTARI` | Render otomatik üretir (`generateValue`) |
| `FD_TOKEN` | football-data.org ücretsiz hesabınızdaki API anahtarı |
| `FI_IZINLI_HOST` | isteğe bağlı; boş bırakılırsa Render'ın verdiği alan adı kullanılır |

## 4. Depolama — karar gerekli
Render'ın ücretsiz web servisinin dosya sistemi **geçicidir** ve kalıcı disk takılamaz. Yeniden dağıtımda, yeniden başlatmada ve 15 dakika hareketsizlik sonrası uykuda yazılan her şey silinir: donmuş tahminler, bültenler, fiyat karşılaştırmaları ve güncel veri.

| Seçenek | Aylık | Kalıcılık | Uyku |
|---|---|---|---|
| **A. Starter + 1 GB disk** (önerilen) | Starter $7 + disk 1 GB × $0,25 ≈ **$7,25** (vergi hariç) | Kalıcı. `/var/data` altında; Render günlük disk anlık görüntüsü alır. | Yok |
| **B. Ücretsiz + elle yedek** | $0 | Yok. "Yedek ve depolama" sayfasından indirip yeniden başlatma sonrası geri yüklemek gerekir. Unutulursa veri kaybolur. | 15 dk sonra uyur; açılış yaklaşık 1 dk |
| **C. Ücretsiz + özel GitHub veri deposuna otomatik eşitleme** | $0 | Her dondurma ve kayıt özel bir depoya yazılır, açılışta geri yüklenir. Ek geliştirme ve yazma yetkili GitHub anahtarı gerekir. | 15 dk sonra uyur |

Render'ın ücretsiz Postgres seçeneği 30 gün sonra sona erdiği için kalıcı arşiv olarak uygun değildir.

A seçeneği için `render.yaml` içinde `plan: starter` yazılır, `disk:` bloğunun ve `FI_OUTPUT` / `FI_KALICI_DEPOLAMA` satırlarının yorumu kaldırılır.

## 5. Ücretsiz planın diğer sınırları
- Çalışma alanı başına ayda 750 servis saati; tek servis için yeterli.
- Uyuyan servis ilk istekte yaklaşık bir dakikada açılır. Render ücretsiz servisi istediği zaman yeniden başlatabilir.
- 512 MB bellek ve 0,5 CPU. Nesine bülteni (10 MB JSON ve Excel üretimi) bu bellekte denenmedi. Yetmezse işlem hata verir; veri kaybı olmaz.
- **Nesine'nin Render'ın Frankfurt sunucularından gelen isteklere yanıt verip vermediği bilinmiyor.** Engel olursa uygulama bunu bildirir ve aşmaya çalışmaz. Bu durumda bülten Claude oturumunda çekilip yedekle yüklenebilir.

## 6. İlk kurulum adımları
Bunları siz yaparsınız; hesap açma, ödeme ve anahtar girişi sizindir.
1. render.com'da hesap açın ve GitHub hesabınızı bağlayın (yalnızca `football-intelligence` deposuna izin verin).
2. **New → Blueprint** → depo `omegge/football-intelligence`, dal `feature/football-intelligence-v1` → `render.yaml` okunur.
3. İstenen değişkenleri girin: `FI_KULLANICI`, `FI_PAROLA_OZETI`, `FD_TOKEN`.
4. İlk dağıtım bitince verilen `https://….onrender.com` adresini açın ve giriş yapın.
5. **Yedek ve depolama → Yedekten geri yükle** ile yerel arşiv yedeğini (`fi_yedek_*.tar.gz`) yükleyin. Yerelde denendi: 150 dosya yazıldı, donmuş tahminler doğrulandı, ikinci yükleme hiçbir şeyin üzerine yazmadı.
6. iPhone'da Safari → Paylaş → **Ana Ekrana Ekle**.

## 7. Doğrulama
- `tests/test_guvenlik.py`: parola, oturum imzası ve süresi, CSRF, sınırlayıcı, kapalı başarısızlık, açık yönlendirme, gizli traceback, FD anahtarının yalnızca başlıkta kullanılması, yedek yol saldırısı, bozuk SHA ve üzerine yazmama. Ayrıca bulut kipinde ayrı süreçte gerçek sunucuyla:
  - giriş zorunluluğu;
  - Host denetimi ve HTTPS yönlendirmesi;
  - CSRF ve köken denetimi;
  - deneme sınırı (5 → 429);
  - güvenlik başlıkları;
  - yedek indirme ve yükleme;
  - günlükte gizli bilgi olmaması.
- Chromium, iPhone 13 görünümü, bulut kipi:
  - giriş → yanlış parola → doğru parola;
  - yedekten geri yükleme;
  - SOU–MID sayfası (donmuş tahmin, fiyat, ayrışma, haber);
  - beş sayfada yatay taşma yok;
  - çıkış.
