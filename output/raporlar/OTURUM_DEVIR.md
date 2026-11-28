# Football Intelligence — oturum devir belgesi (2026-11-28T01:55Z)

## Sürümler ve ortam
- Kod: `omegge/football-intelligence`, dal `feature/football-intelligence-v1` @ `613ba07` (main `b0432e7`'ye dokunulmaz).
- Hafıza: `arastirma-hafizasi` dalı (bu devirle güncellenir; commit kimliği sohbette bildirildi). İkinci oturumun yerel `68a1c78` commit'i KULLANILMAZ ve birleştirilmez.
- Bulut ortamı: `football-intelligence` (kişisel, sınırlı ağ). 51 izinli host; 28.11'de eklenen: ligue1.com, parisfc.fr, brondby.com, www.heracles.nl. football-data.org anahtarı ağ gizli anahtarı olarak durur (koda/dosyaya yazılmaz).
- ChatGPT Work: temel ZIP 27.11 (≡ f40ec55) + fark paketi `football_intelligence_chatgpt_guncelleme_613ba07.zip`.

## Çalışma kuralları (özet; tamamı CLAUDE.md)
- Varsayılan ARAŞTIRMA MODU; Türkiye ligleri hariç; ~10 uluslararası maç; yalnızca nihai sonuç; kupon yok; ara aday listesi/onay sorusu yok.
- MK-1: oranlar modele girmez; önce `dondur`, sonra `karsilastir` (dondurmadan sonra çekilen bültenle).
- Haberler yalnızca `sohbet haber-kaydet` ile; [tam sayfa]/[özet] ayrımı; yayın tarihi + ilgili maç doğrulaması; kesin ilk 11: resmî kaynak + bağımsız ikinci kaynak.
- İstatistik ↔ market koşulu eşleştirilir; takım bazlı marketlerde takımın kendi golü, toplam gol marketinde toplam gol; turnuva kapsamı (lig / tüm yarışmalar) her zaman belirtilir. Kalibre model yoksa "hesaplanamaz".
- Model değerlendirmesinde örneklem = maç sayısı (ilişkili marketler bağımsız sayılmaz).

## Önemli bulgular
- 27.11: SOU–MID pilotu tamamlandı (2-0, İY 0-0; log-kayıp 0,3034, Brier 0,079 — tek maç, sonuç çıkarılmaz). Venezia hoca tarihi düzeltmesi (Nicola 14/15.10).
- 28.11: 26 tahmin donduruldu (fiyat karşılaştırması `bulten_20261128_040328`, 01:03:28Z). En büyük model ayrışmaları yükselen takımlarda → yanlılık şüphesi (test planı hazır, uygulanmadı).
- Öne çıkanlar: Torino–Lazio MS 2 (model %56,7 / BE %51,8 @1,93); Hamburg–Bayern EÇGOY 2.Y (BL1 7/10; Kane, Musiala, Olise yok — resmî); Elche–Atlético 1Y KG Yok 0/13 (Lookman, Cuti Romero yok); PSV ligde İY önde 12/13.

## Kayıt yerleri (output/, git dışı; hafıza dalında)
- `arastirma/guncel/gun_20261127/BULGULAR.md`, `gun_20261128/` (BULGULAR, DUZELTMELER, DUZELTME_EK_PSV, TAHMIN_FIYAT_ESLESMESI.json, HABER_INDEKSI.json)
- `arastirma/genis_pilot/*_20261128T01*Z/` (haber-kaydet çıktıları), SOU_MID turları ve PILOT_TAMAM / TUR_ZAMANLARI
- `tahminler/` (dondurulmuş tahminler + kayit.jsonl), `raporlar/` (YUKSELEN_TAKIM_YANLILIK_TEST_PLANI, DEGERLENDIRME_PROTOKOLU_20261128, bu belge)

## Tamamlanmamış işler
1. 28.11 maç sonuçları: maçlar bitince `PYTHONPATH=lib python3 -m fi.kaynaklar.guncel guncelle` + `sohbet hafiza --guncelle` (tahminlere dokunulmaz).
2. İkinci oturum raporunun karşılaştırması (rapor bekleniyor; 04:12 çekimi ve 68a1c78 bu ortamda yok).
3. Yükselen takım yanlılığı testi ve maç bazlı değerlendirme çıktısı (kod gerektirir; onay bekliyor).
4. Hafıza dalı push'u yalnızca kullanıcı onayıyla.

## Yeni oturumda ilk adımlar
1. `PYTHONPATH=lib python3 -m uygulama.sohbet hafiza-dali geri` (SessionStart kancası zaten çalıştırır) → `sohbet hafiza`.
2. `git log --oneline -1` ile `feature/football-intelligence-v1` @ 613ba07 olduğunu doğrula.
3. Bu belgeyi oku: `output/raporlar/OTURUM_DEVIR.md`.
4. 2–3 sayfayla `web-fetch` erişim kontrolü (CLAUDE.md "Yeni oturum başında").
