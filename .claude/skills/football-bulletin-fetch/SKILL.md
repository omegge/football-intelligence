---
name: football-bulletin-fetch
description: Nesine futbol bültenini (maç öncesi ve canlı) istek üzerine çeker; bütün erişilebilir futbol liglerini, marketleri, seçenekleri ve oranları ham JSON, düzenlenmiş JSON ve Excel olarak zaman damgalı yeni klasöre kaydeder ve seçilen Türkiye gününün maç listesini sohbette sunar. Kullanıcı "Bülteni çek", "Bugünün bültenini yenile", "Nesine maçlarını getir", "Güncel futbol bültenini çek", "canlı bülteni çek" ya da belirli bir gün için bülten istediğinde kullan. Analiz yapmaz, olasılık üretmez, kupon hazırlamaz.
---

# Futbol bülteni çekme

Kaynak: kullanıcının Colab not defteri `kaynak/nesine_gunluk_3.ipynb` (104 marketlik sözlük `data/market_sozlugu_v3.json` içinde birebir korunur, bu beceri sözlüğe yazmaz).

## Kurallar
- Yalnızca kullanıcı istediğinde çalıştır. Zamanlanmış ya da tekrarlayan çekim kurma.
- Her akış için TEK istek. Hostlar yalnızca `cdnbulten.nesine.com` ve `bulten.nesine.com`. User-Agent dürüst (FootballIntelligence/…); tarayıcı kimliğine bürünme, Playwright/Selenium/çerez/başka adres deneme.
- Erişim engellenirse (401/403/429, HTML doğrulama sayfası, ortam proxy'si 403) DUR ve raporla. Engeli aşmaya çalışma, tekrar deneme. Yalnızca bağlantı hatasında (yanıt hiç gelmediyse) sohbet komutu en fazla 2 kez yeniden dener.
- Bahis oranlarından olasılık üretme. Bülten çekmek hiçbir maç analizini ya da kuponu başlatmaz.
- Maç öncesi ve canlı veri ayrı dosyalardır; canlı sınıflandırma akışa göredir.

## Sohbetten çalıştırma (varsayılan yol)
"Bülteni çek", "bugünün bültenini yenile" ya da "Nesine maçlarını getir" isteğinde:
```
PYTHONPATH=lib python3 -m uygulama.sohbet bulten [--gun YYYY-AA-GG] [--zorla]
```
- Gün verilmezse bugün (TR) kullanılır. Çekim penceresi yalnızca o gün 00:00–23:59 (TR). Ertesi gün 00:00–03:00 arasındaki maçlar o güne dahil edilmez ve sayıları raporlanır.
- Her çekim yeni bir `output/bulten_YYYYAAGG_SSDDss/` klasörüne yazılır; eskisinin üzerine yazılmaz.
- Aynı gün için son başarılı çekim 10 dakikadan yeniyse Nesine'ye yeniden istek gönderilmez. Kullanıcı açıkça yenileme isterse `--zorla`.
- **Yeniden deneme:** Yalnızca bağlantı hatasında (`BAGLANTI`) 15 sn ve 45 sn arayla en fazla 2 kez. Erişim engelinde (`ERISIM_ENGELI`: 401/403/429, HTML) hiç yeniden denenmez; durulur ve raporlanır.
- **Çıktı:** durum, çekim zamanı, maç / market / seçenek / oynanabilir seçenek sayıları, uyarılar, lig özeti ve maç tablosu (oransız: kod, saat, lig, maç, bağımsız model durumu). Bunu sohbette sun ve kullanıcıya ilgilendiği maçları seçebileceğini söyle.
- Bütün marketler ve özel marketler, `market_sozlugu_v3.json` ile adlandırılmış olarak, düzenlenmiş JSON ve Excel'de korunur.
- Maç listesi: `maclar [--gun] [--lig METİN] [--ara METİN] [--hepsi]`.

## Doğrudan betik (gelişmiş)
```
python3 .claude/skills/football-bulletin-fetch/scripts/nesine_bulletin.py cek
```
Seçenekler: `--akis mac-oncesi|canli` (varsayılan ikisi), tarih filtresi yalnızca maç öncesine uygulanır:
`--tarih 24.11.2026` (o gün 00:00 → ertesi gün 03:00 TR), `--bugun` (not defterindeki pencere),
`--baslangic "2026-11-24 12:00" --bitis "2026-11-24 23:59"`. Filtre verilmezse bütün bülten alınır.

Erişim yoksa kullanıcı Colab'da indirdiği ham JSON'u yükleyebilir:
```
python3 .claude/skills/football-bulletin-fetch/scripts/nesine_bulletin.py isle --mac-oncesi-ham DOSYA [--canli-ham DOSYA]
```

## Çıktı: `output/bulten_YYYYAAGG_SSDDss/`
- `ham/mac_oncesi.json`, `ham/canli.json`: yanıtlar bayt bayt
- `mac_oncesi.json`, `canli.json`: normalleştirilmiş futbol verisi (+ `spor_belirsiz`, diğer spor sayıları, filtre dışı kodlar)
- `mac_oncesi.xlsx`, `canli.xlsx`: `ozet`, `tum_oranlar` (her seçenek bir satır, kapalı/seçeneksiz dahil), `maclar_genis`, canlıda `canli_durum`, `dogrulama`, `kaynak`
- `kaynak.json`: URL, çekim zamanı (UTC ve TR), HTTP durumu, bayt, SHA-256, sözlük özeti
- `dogrulama.json`: BASARILI / UYARILI / BASARISIZ ve bütün bulgular

## Kullanıcıya bildirme
1. Durum satırını ve her KRITIK/UYARI bulgusunu Türkçe özetle (ör. isimlendirme oranı, yapı değişikliği, engel).
2. Excel ve JSON dosyalarını SendUserFile ile gönder (`display: attach`).
3. Canlı skor/dakika/durum alanları `CANLI_ALAN_HARITASI` doğrulanana kadar "aday" olarak gösterilir; bunu belirt.
4. Analiz ya da kupon önerme; kullanıcı bir maç seçerse ayrı analiz becerileri kullanılır.

## Test
`python3 -m unittest discover -s tests -v` (A1–A9, ağsız).
