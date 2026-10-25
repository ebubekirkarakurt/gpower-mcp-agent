# DEMO_SCRIPT.md — gpower-clone demo videosu

Hedef süre: ~6–8 dakika. Tüm sorular **kurgusal** araştırma senaryolarıdır; ekranda gerçek hasta verisi veya API anahtarı görünmemelidir (anahtarı kayıttan önce ayarlayın).

## 0. Hazırlık (kayıt öncesi)

```powershell
cd gpower-clone
.venv\Scripts\Activate.ps1
pip install -e ".[dev,agent]"
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # yalnızca Claude sağlayıcısı için; kayıt dışında ayarlayın
# Önceki logu silmeden yedekleyin (kanıt olarak gerekebilir), demo temiz bir logla başlasın:
if (Test-Path logs\agent_calls.jsonl) { Move-Item logs\agent_calls.jsonl "logs\agent_calls.$(Get-Date -Format yyyyMMdd-HHmmss).jsonl" }
```

API anahtarı olmadan (Ollama ile yerel model):

```powershell
ollama list                               # qwen2.5:7b listede olmalı
$env:GPOWER_AGENT_PROVIDER = "ollama"     # bundan sonra gpower-clone-agent Ollama'yı kullanır
# Modeli belleğe almak için kayıttan önce bir kez ısındırın (ilk yanıt yavaş olabilir):
ollama run qwen2.5:7b "merhaba" | Out-Null
```

## 1. Giriş (30 sn)

- Proje: G*Power 3.1.9.7 `χ² tests – Contingency tables` ailesinin bağımsız yeniden yazımı; CONTRACT.md 1.0.0.
- Mimari şemayı README'den göster: tek motor (`calculate()`), üç arayüz (CLI, MCP, ajan).
- Etik not: G*Power kodu kopyalanmadı; yalnızca davranış gözlendi (`evidence/observations.md`).

## 2. CLI (1 dk)

```powershell
gpower-clone --version
gpower-clone --test chi2-contingency --mode a-priori --w 0.3 --alpha 0.05 --power 0.95 --df 5
gpower-clone --test chi2-contingency --mode post-hoc --w 0.3 --alpha 0.05 --n_total 100 --df 5
gpower-clone --test chi2-contingency --mode post-hoc --w 0.3 --alpha 0.05 --n_total 100 --df 5 --tails 1
echo $LASTEXITCODE
```

Anlatılacak: tek satır JSON, `n_total: 220` G*Power ile aynı; `--tails` bu ailede `UNKNOWN_PARAM`, çıkış kodu `2`.

## 3. Testler (1 dk)

```powershell
pytest -v -rs
```

Vurgula: `test_mcp_equivalence.py` (CONTRACT §9'daki 25 vektör için CLI == MCP), `test_mcp_errors.py` (hata kodları), `test_agent.py` / `test_agent_ollama.py` (ajan MCP aracını çağırıyor, logluyor, uydurma sonucu reddediyor), `test_ollama_live.py` (gerçek yerel modelle N=220; Ollama kapalıysa SKIPPED görünür). Ekrandaki gerçek geçti/atlandı sayısını okuyun.

## 4. MCP sunucusu (1–1.5 dk)

Seçenek A — MCP Inspector (Node.js gerekir):

```powershell
npx @modelcontextprotocol/inspector .venv\Scripts\gpower-clone-mcp.exe
```

- Tools listesinde yalnızca `power_analysis` olduğunu göster.
- Çağrı 1: `{"test":"chi2-contingency","mode":"a-priori","w":0.3,"alpha":0.05,"power":0.95,"df":5}` → CLI ile aynı JSON.
- Çağrı 2: `df` = `2.5` → `INVALID_VALUE`, `isError: true`.
- Çağrı 3: fazladan `"foo": 1` → `UNKNOWN_PARAM`.

Seçenek B — Claude Code / Claude Desktop'a README §4'teki yapılandırmayla ekleyip aracı oradan çağırın.

## 5. AI ajanı (2–3 dk)

Ollama varyantında önce hedef soruyu tek seferlik modda gösterin:

```powershell
gpower-clone-agent --provider ollama "Kurgusal bir araştırma senaryosu: kontenjans tablosu için ki-kare testi planlıyoruz. Etki büyüklüğü w=0.3, alpha=0.05, power=0.95 ve df=5. Gerekli toplam örneklem büyüklüğü nedir?"
```

→ Yanıtın altındaki "MCP power_analysis çıktısı" satırında `"n_total": 220` olduğunu gösterin. Model araç çağrısı yapmazsa ajanın uydurma sonuç yerine `HATA: Model yapılandırılmış araç çağrısı üretmedi...` yazdığını anlatın.

Ardından etkileşimli mod (`GPOWER_AGENT_PROVIDER` ayarlıysa Ollama, değilse Claude):

```powershell
gpower-clone-agent
```

Sırayla sorulacak kurgusal sorular:

1. **A-priori:** `Kurgusal bir çalışmada iki tedavi kolunda yanıt oranlarını karşılaştıracağız (2x2 tablo). w=0.3, alfa 0.05, güç 0.95 için kaç katılımcı gerekir?`
   → Ajanın df = (2−1)(2−1) = 1 dönüşümünü açıkladığını ve aracı çağırdığını göster.
2. **Belirsiz etki büyüklüğü:** `Üç tedavi kolu ve üç yanıt kategorisi var, orta düzey bir etki bekliyoruz. Alfa 0.05, güç 0.80. Kaç kişi gerekir?`
   → Ajan "orta"yı sessizce 0.3 kabul etmemeli; öneriyi söyleyip onay istemeli. Sonra: `Evet, 0.3 kullan.`
3. **Post-hoc:** `Kurgusal pilot çalışmada 100 katılımcı vardı, w=0.3, df=5, alfa 0.05. Ulaşılan güç nedir?`
4. **Eksik parametre:** `w=0.3 ve güç 0.9 için örneklem hesapla.` → Ajan alfa ve df'yi sormalı.
5. **Hatalı giriş:** `Alfa 1.5, w=0.3, df=2, güç 0.8 ile örneklem hesapla.` → Araçtan `OUT_OF_RANGE` dönüşü ve Türkçe açıklama (ajan önce kullanıcıyı uyarabilir; ikisi de kabul edilebilir).

Çıkış: boş satır.

## 6. Log kanıtı (1 dk)

```powershell
Get-Content logs\agent_calls.jsonl
```

Her satırda `ts`, `question`, `tool_input`, `tool_output`, `tokens_in`, `tokens_out` alanlarını göster. Ajanın yanıtındaki sayıların `tool_output` ile aynı olduğunu bir örnek üzerinden karşılaştır (ajan hesap yapmıyor, aracı çağırıyor).

## 7. Kapanış (30 sn)

- Tek motor, üç arayüz; MCP çıktısı CLI ile birebir aynı (testlerle kanıtlı).
- Sınırlamalar: yalnızca `chi2-contingency` ailesi; ajan bir dil modeli olduğundan kesin sonuç için log esas alınır.
