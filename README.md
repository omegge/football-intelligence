# Football Intelligence

Claude Code üzerinden Türkçe komutlarla çalışan kişisel futbol araştırma ve bağımsız olasılık analizi sistemi.
Şu an hazır olan bileşen: **Nesine futbol bülteni çekici** (maç öncesi + canlı → ham JSON, düzenlenmiş JSON, Excel).

## Kullanım (Claude Code)
Proje bu depo ve `football-intelligence` bulut ortamıyla açıldığında:

> **Güncel futbol bültenini çek**

Claude `football-bulletin-fetch` becerisini çalıştırır, dosyaları gönderir ve özet verir.
Diğer komutlar: "Canlı bülteni çek", "24.11.2026 tarihli bülteni çek". Ayrıntı: `CLAUDE.md`.

## Elle çalıştırma (proje kökünden)
```bash
python3 .claude/skills/football-bulletin-fetch/scripts/nesine_bulletin.py cek
```
- `--akis mac-oncesi|canli` (varsayılan ikisi)
- Maç öncesi için tarih filtresi (TR saati): `--tarih 24.11.2026`, `--bugun`, `--baslangic "2026-11-24 12:00" --bitis "2026-11-24 23:59"`
- Ağ yoksa Colab'da indirilmiş ham yanıtı işle: `isle --mac-oncesi-ham DOSYA --canli-ham DOSYA`
- Önceki bir çekimi yeni istek atmadan yeniden işle: `isle --kaynak-klasor output/bulten_...`

Çıktı yapısı ve alanlar: [`docs/VERI_SEMASI.md`](docs/VERI_SEMASI.md).

## Testler
```bash
python3 -m unittest discover -s tests -v
```
41 test, ağsız (A1–A11): canlı sınıflandırma, canlı market adları, maça özel etiket koruması, spor ayrımı,
çizgi/handikap adları, TR tarih filtresi, yapı doğrulaması, sözlük bütünlüğü, Excel'de seçenek kaybı olmaması,
lig adları, marketsiz maçlar ve veri bütünlüğü (EMBS, MS durumu, SOV2/SOV3, EWMA eşleştirme, futbol uzun vadeli, alternatif adlar).

## Ağ ve güvenlik kuralları
- Yalnızca `cdnbulten.nesine.com` ve `bulten.nesine.com`; her akış için tek GET; dürüst User-Agent.
- Erişim engeli (401/403/429, HTML doğrulama sayfası) aşılmaz; durulur ve raporlanır.
- Tarayıcı otomasyonu, çerez, token kullanılmaz; ücretli API yok; bulut ortamında paket yüklenmez.
- Bahis oranlarından olasılık üretilmez; kupon yalnızca açık istekle.

## Klasörler
| Yol | İçerik |
|---|---|
| `.claude/skills/football-bulletin-fetch/` | Beceri: `SKILL.md`, `scripts/nesine_bulletin.py`, `data/market_sozlugu_v3.json` (104 kod, 190 anahtar) |
| `tests/test_bulletin.py` | Otomatik testler |
| `kaynak/nesine_gunluk_3.ipynb` | Orijinal Colab not defteri (değiştirilmeden; sözlük testleri buna karşı yapılır) |
| `docs/` | Veri şeması |
| `output/` | Çekim çıktıları (git dışı) |

## Bilinen sınırlar (23.11.2026 ilk gerçek çekim)
- Canlı akış maç öncesinden farklı market kodları kullanır; sözlük canlıya uymaz. Canlı marketlerin ~%17'si
  JSON'daki adıyla tanımlanıyor, kalanı koduyla korunuyor.
- Canlı akışta skor/dakika/durum alanı yok; ayrı bir canlı skor kaynağı gerekecek.

## Köken
Bülten mantığı ve 104 marketlik sözlük kullanıcının Colab not defterinden (`kaynak/`). Analiz becerileri
ileride zetamins/Footy-Skills (commit fdd4570, lisans dosyası yok) temel alınarak eklenecek.
