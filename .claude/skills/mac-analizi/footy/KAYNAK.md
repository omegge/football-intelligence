# Footy-Skills kaynağı ve uyarlama kaydı

- Kaynak: https://github.com/zetamins/Footy-Skills, commit `fdd4570` ("Add the Footy Skills package…"). Oturumun başında güvenlik açısından incelendi.
- **Lisans:** depoda LICENSE dosyası yok. Bu kopya yalnızca kişisel ve özel kullanım içindir. Depo herkese açık yapılmamalıdır.
- `orijinal/`: 16 Skill'in SKILL.md metinleri ve `football-match-lite` şablon/mercek/referans dosyaları, değiştirilmeden. Bu dosyalar Skill olarak yüklenmez (klasör düzeyinde SKILL.md yok).
  - Scriptler kopyalanmadı: kazıyıcının ürettiği `report.json` biçimine bağlılar ve kazıyıcı çıkarıldı.

| Özgün | Karar | Nerede |
|---|---|---|
| football-scrape | ÇIKARILDI: Cloudflare'i aşmak için otomasyon gizleme, playwright/httpx kurulumu, oran çekme | — |
| football-match-analyst | ÇIKARILDI: depoda olmayan `football.oracle` motoru | — |
| football-match-collection | UYARLANDI: `run_collection.py` alt ajan runner'ı (opencode/codex/`claude -p`, dış modeller) YOK; adımlar aynı oturumda Claude tarafından | `mac-analizi/SKILL.md` |
| football-match-lite | UYARLANDI (karar verici): sayılar yalnızca önceden kayıtlı modelden (E3/E2/Poisson); `calc.py` Poisson'u yerine `fi.is_akisi`; bahis/stake/kupon/`value.py`/`score.py` yok | `protokol/konsey.md`, `protokol/rapor.md` |
| team-news, tactical-matchup, underlying-stats, context-motivation | KORUNDU, uyarlandı: `xg_delta` kaldırıldı (haber ve yorum olasılığa eklenmez); kanıt tabanı = `uygulama.sohbet mac` + web araştırması | `protokol/uzmanlar.md` |
| media-scout | UYARLANDI: `media.py` (Google News RSS) yerine Claude web araması + `fi.haber.genis` doğrulama katmanı; tahmin siteleri karantinada kaydedilir | `protokol/uzmanlar.md`, `haber-arastir` |
| 7 savunucu (home, away, draw, goals, underdog, gamestate, chaos) | KORUNDU: aynı roller ve "dürüst dava / iki geçiş" yöntemi; oran ve olasılık yok | `protokol/konsey.md` |
