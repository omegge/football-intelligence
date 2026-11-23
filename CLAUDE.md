# Football Intelligence

Kişisel futbol araştırma ve bağımsız olasılık analizi sistemi. Yalnızca futbol.

## Türkçe komutlar
| Kullanıcı der ki | Yapılacak |
|---|---|
| "Güncel futbol bültenini çek" | `football-bulletin-fetch` becerisi: maç öncesi + canlı bülten → Excel + JSON, dosyaları gönder |
| "Canlı bülteni çek" | aynı beceri, `--akis canli` |
| "… tarihli bülteni çek" | aynı beceri, `--tarih` ya da `--baslangic/--bitis` (TR saati) |

(Maç analizi, model, oran karşılaştırması ve backtest becerileri henüz eklenmedi.)

## Değişmez kurallar
1. Bot korumasını ya da erişim engelini aşma; tarayıcı taklidi, Playwright/Selenium, çerez kullanma. Engel varsa dur ve raporla.
2. Otomatik alt ajan runner'ı başlatma (`opencode`, `codex`, `claude -p`).
3. Ücretli API kullanma; paket yükleme (mevcut kütüphaneler: requests, pandas, numpy, openpyxl, xlsxwriter).
4. Bahis oranlarını olasılık modelinin girdisi yapma. Oranlar yalnızca dondurulmuş bağımsız tahminden SONRA karşılaştırılır.
5. Her veri için kaynak, veri tarihi ve doğrulama zamanı göster; veri yoksa sayı uydurma, "veri yok" de.
6. Kullanıcı açıkça istemeden kupon hazırlama ve bütün maçları ayrıntılı analiz etmeye başlama. Kupon istense bile
   `dogrulanmamis_eslesme` / `isim_celiskisi` işaretli maçları ve `oynanabilirlik` değeri `oynanabilir` olmayan
   oranları (ör. `durumu_dogrulanmamis`, market durumu MS≠1 ya da eksik) kupona alma; nedenini kullanıcıya söyle.
7. Hiçbir pazara doğrulanmamış "yüksek güven" verme.

## Çıktılar
`output/` git dışıdır. Şimdilik dosyalar kullanıcıya indirilebilir olarak gönderilir; kalıcı arşiv daha sonra.
