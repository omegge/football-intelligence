# Southampton – Middlesbrough araştırma turları (Nesine 3331002 · football-data.org 561968)

Başlama: 27.11.2026 23:00 TR = 20:00 UTC (iki kaynakta aynı; 26.11 bülteni + fd.org season=2026).

| Tur | TR | UTC | Durum |
|---|---|---|---|
| T−24s | 26.11 ~21:30 | 26.11 ~18:30 | YAPILDI (v2: 10 sorgu + v1'in 4 sorgusu) |
| T−6s | 27.11 17:00 | 27.11 14:00 | YAPILMADI — otomatik zamanlayıcı kurulmadı (onay bekliyor) |
| T−90dk | 27.11 21:30 | 27.11 18:30 | YAPILMADI — ilk 11'ler bu turda beklenir |

## Her turda çalıştırılacaklar (sıra MK-1'e uygun)
1. Güncel sonuç verisi ve bütünlük:
   `PYTHONPATH=lib python3 -m fi.kaynaklar.guncel guncelle`
2. (Yalnızca lig eşlemesi onaylandıysa) bağımsız tahmin + dondurma — oranlar açılmadan:
   `fi.is_akisi.bagimsiz_tahmin(...)` → `fi.is_akisi.dondur(...)` (T−6s turunda; T−90dk'da yeni tahmin YOK, yalnızca haber).
3. Haber aramaları (her iki takım ayrı): kulüp (southamptonfc.com, mfc.co.uk), yerel basın (Daily Echo, Teesside Live),
   ulusal (BBC, Sky), ajans (Hayters, PA), muhabirler, önizlemeler, Reddit (r/SaintsFC, r/Boro: yalnızca arama özeti).
   T−90dk: "Southampton starting XI Middlesbrough", "Middlesbrough team news confirmed lineup".
4. Kayıt: yeni tur kayıtları `tur="T-6s"` / `"T-90dk"` ile `genis.Iddia` olarak eklenir; `genis.tur_karsilastir`
   önceki turla farkları (ör. Lankshear hazır ↔ şüpheli, Jander dönüş) gösterir.
5. Bülten (dondurmadan SONRA): `python3 .claude/skills/football-bulletin-fetch/scripts/nesine_bulletin.py cek --tarih 27.11.2026 --akis mac-oncesi`
   → `fi.is_akisi.fiyat_karsilastir(donmus_yol, nesine_mac)`.

## Onay gerekenler
- Lig eşlemesi: İngiltere Championship [52] → en.2 (kanıt: veri/lig_esleme_kanitlari.json, fikstür hizalaması).
- Sayfa okuma için host değerlendirmesi: southamptonfc.com, mfc.co.uk, gazettelive.co.uk, dailyecho.co.uk, thefa.com
  (robots.txt AI ajanları + kullanım koşulları denetlenmeden açılmaz).
- Zamanlayıcı: T−6s ve T−90dk turlarının otomatik başlatılması.
