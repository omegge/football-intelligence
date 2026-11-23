# Veri şeması (nesine_bulletin.py 0.1.0)

Her çekim `output/bulten_YYYYAAGG_SSDDss/` klasörüne yazılır. Maç öncesi ve canlı veri ayrı dosyalardır.

| Dosya | İçerik |
|---|---|
| `ham/mac_oncesi.json`, `ham/canli.json` | Nesine yanıtı, bayt bayt (SHA-256 `kaynak.json` içinde) |
| `mac_oncesi.json`, `canli.json` | Düzenlenmiş veri (aşağıda) |
| `mac_oncesi.xlsx`, `canli.xlsx` | Excel (aşağıda) |
| `kaynak.json` | Sürüm, sözlük özeti, pencere, her akış için kaynak meta bilgisi, durum, bütün doğrulama kayıtları |
| `dogrulama.json` | `durum` (BASARILI / UYARILI / BASARISIZ) ve `kayitlar` |

## Kaynak meta bilgisi (`kaynak.json` → `kaynaklar.<akış>`)
`url`, `cekim_utc`, `cekim_tr`, `user_agent`, `http_durumu`, `icerik_turu`, `bayt`, `sha256`, `sure_sn`, `hata`,
`ham_dosya`, `etkinlik_yolu` (normalde `sg.EA`), `yedek_arama`, `ham_etkinlik_sayisi`, `etkinlik_alanlari`
(alan adı → kaç etkinlikte geçtiği; sonraki çekimde yapı değişikliğini yakalamak için).

## Nesine ham yapısı (gözlenen, 23.11.2026)
- `sg.EA`: etkinlikler. Alanlar: `C` (kod), `NID`, `EV`, `HN`/`AN` (ev/deplasman), `ENO`/`ENN` (etkinlik adı),
  `TYPE` (spor; futbol = 1, negatif = uzun vadeli), `GT`, `D`/`T` (TR tarih/saat), `ESD` (epoch ms), `LC` (lig kodu),
  `MA` (marketler), `MSA` (uzun vadeli marketler), `MBS` ve diğer bayraklar.
- `sg.LA`: ligler `{LID, N (ad), CC (ülke/kategori), SO}`. Etkinliklerde `LN` yoktur; lig adı `LC` → `LID` eşlemesiyle gelir.
- `sg.EWMA` (yalnızca maç öncesi): marketi olmayan etkinlikler (`LN` içerir).
- Market: `MTID` (market tipi), `SOV` (çizgi), `ID`, `NO`, `MT`, `MBS`, bazen `MN` (ad), `OCA` (seçenekler).
- Seçenek: `N` (no), `O` (oran; 1.0 = kapalı), bazen `ON` (ad).
- Canlı ve maç öncesi farklı `MTID` kod uzayları kullanır. Canlı etkinliklerde skor/dakika alanı yoktur.

## Düzenlenmiş JSON (`<akış>.json`)
```
kaynak            : kaynak meta bilgisi
pencere_tr        : [başlangıç, bitiş] | null
futbol            : [etkinlik]           # analiz kümesi (spor kodu 1)
spor_belirsiz     : [etkinlik]           # spor kodu yok / negatif (ör. "Şampiyon Kim Olur?")
diger_spor_sayilari: {spor_kodu: adet}   # bu etkinlikler yalnızca ham JSON'da
filtre_disi_kodlar: [kod]                # tarih penceresi dışı
marketsiz_futbol  : [etkinlik]           # EWMA'dan, marketsiz
```
Etkinlik: `akis, kod, nid, ev_kodu, spor_kodu, futbol, lig, lig_ulke, lig_kodu, lig_kaynagi (LN|LA), ev, deplasman,
karsilasma, etkinlik_adi, baslama_tr (ISO, +03:00), baslama_kaynagi (ESD|D/T), tarih_saat_celiskisi, tarih, saat,
mac_mbs, baslama_saati_gecmis, baslamamis_gorunuyor, diger_akista_da_var, zaman_okunamadi, eksik_alanlar,
marketler[], canli (yalnızca canlı akışta)`.

Market: `market_blok (MA|MSA), market_sira, market_tip_id, market_json_id, market_no, market_mt, ozel_deger,
market_mbs, market_adi, market_adi_kaynagi (json|sozluk|yok), sozluk_adi, maca_ozel, secenekler[]`.

Seçenek: `secenek_no, secenek_adi, secenek_adi_kaynagi (json|sozluk|yok), oran (açık değilse null), oran_ham,
oran_durumu (acik|kapali|gecersiz|yok)`.

Canlı: `resmi` (doğrulanmış `CANLI_ALAN_HARITASI` ile skor/dakika/durum; harita boşken boş), `adaylar`,
`alanlar` (market dışı bütün alanlar düzleştirilmiş), `harita_dogrulandi`.

## İsimlendirme kuralları
1. Market adı: JSON `MN` → yoksa futbolda sözlük (`MTID|SOV`, yoksa `MTID|*`; handikap işareti ve `{cizgi}` şablonu)
   → yoksa `market <kod> (<çizgi>)`. JSON adı sözlükle çelişirse JSON kullanılır, uyarı yazılır.
2. Seçenek adı: JSON `ON` → maça özel markette (Oyuncu/Kaleci/Karşılaşma/Takım ya da sözlükte `maca_ozel`)
   ASLA sözlük kullanılmaz → diğerlerinde sözlük (`{ev}`/`{dep}` yerine takım adı) → `seçenek <N>`.

## Excel sayfaları
| Sayfa | İçerik |
|---|---|
| `ozet` | maç başına market, seçenek, açık oran, isimsiz market sayısı |
| `tum_oranlar` (gerekirse `_2`, `_3`…) | her seçenek bir satır; kapalı ve seçeneksiz marketler dahil. **Esas tablo** |
| `maclar_genis` | maç başına tek satır, her market/seçenek bir sütun; kapalı `-`, seçeneksiz `seçenek yok`; çakışan adlara kod eki. Excel sütun sınırı aşılırsa yazılmaz (raporlanır) |
| `canli_durum` | yalnızca canlı: son doğrulama zamanı, skor/dakika (doğrulanmışsa), adaylar, bütün alanlar |
| `spor_belirsiz`, `marketsiz_maclar`, `filtre_disi` | varsa |
| `dogrulama`, `kaynak` | doğrulama kayıtları ve kaynak meta bilgisi |

Yazımdan sonra dosya geri okunur; `tum_oranlar` satır sayısı seçenek sayısına eşit değilse KRITIK kayıt düşülür.

## Doğrulama kodları
KRITIK: `BAGLANTI, ERISIM_ENGELI, HTTP_DURUMU, BOS_YANIT, JSON_HATASI, ETKINLIK_YOK (maç öncesi), SATIR_KAYBI,
GENIS_TABLO_KAYIP, EXCEL_SATIR_KAYBI`.
UYARI: `YAPI_DEGISTI, TEKRAR_KOD, EKSIK_ALAN, SECENEKSIZ_MARKET, GECERSIZ_ORAN, ASIRI_ORAN, ISIMLENDIRME (<%90),
SOZLUK_JSON_UYUMSUZ, ZAMAN_CELISKISI, BASLAMAMIS_CANLI, CANLI_ALANLAR (harita doğrulanmamış), LIG_ADI_YOK,
ALAN_KAYBOLDU, SAYI_DEGISIMI`.
BILGI: `ORAN_DURUMLARI, BILINMEYEN_MARKET, SPOR_DAGILIMI, BASLAMIS_OLABILIR, IKI_AKISTA, FILTRE_DISI,
MARKETSIZ_MAC, YENI_ALAN, GENIS_TABLO_ATLANDI, KESILEN_HUCRE, KONTROL_KARAKTERI`.
