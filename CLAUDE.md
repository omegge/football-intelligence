# Football Intelligence

Kişisel futbol araştırma ve bağımsız olasılık analizi sistemi. Yalnızca futbol.

## Türkçe komutlar
| Kullanıcı der ki | Yapılacak |
|---|---|
| "Güncel futbol bültenini çek" | `football-bulletin-fetch` becerisi: maç öncesi + canlı bülten → Excel + JSON, dosyaları gönder |
| "Canlı bülteni çek" | aynı beceri, `--akis canli` |
| "… tarihli bülteni çek" | aynı beceri, `--tarih` ya da `--baslangic/--bitis` (TR saati) |
| "Arayüzü aç" | `PYTHONPATH=lib python3 -m uygulama` → http://127.0.0.1:8765 (ayrıntı `docs/V1_ARAYUZ.md`) |

(Maç analizi, model, oran karşılaştırması ve backtest becerileri henüz eklenmedi.)

## Değişmez kurallar
1. Bot korumasını ya da erişim engelini aşma; tarayıcı taklidi, Playwright/Selenium, çerez kullanma. Engel varsa dur ve raporla.
2. Otomatik alt ajan runner'ı başlatma (`opencode`, `codex`, `claude -p`).
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

## Çıktılar
`output/` git dışıdır. Şimdilik dosyalar kullanıcıya indirilebilir olarak gönderilir; kalıcı arşiv daha sonra.
