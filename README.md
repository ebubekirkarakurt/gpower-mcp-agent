# gpower-mcp-agent

G*Power 3.1.9.7 bağımsız güç analizi motoru ve CLI arayüzü (`chi2-contingency` ailesi).

Bu proje [CONTRACT.md](CONTRACT.md) sürüm 1.0.0 arayüz sözleşmesine tam uyumlu olarak geliştirilmiştir.

## 1. Kurulum

Python >= 3.12 gerekir. Proje kök dizininde sanal ortam oluşturup etkinleştirin:

```powershell
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
# Betik çalıştırma engellenirse (yalnızca bu oturum için):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

Tek komutla kurulum (CLI, MCP sunucusu ve Ollama ajanı için yeterli):

```bash
pip install -e .
```

Test bağımlılıkları ve Claude (Anthropic) ajanı ile birlikte tam kurulum:

```bash
pip install -e ".[dev,agent]"
```

`[agent]` ek paketi (`anthropic`) yalnızca `--provider anthropic` için gerekir; Ollama sağlayıcısı onu kullanmaz.

Kurulum üç komut sağlar: `gpower-clone` (CLI), `gpower-clone-mcp` (MCP sunucusu), `gpower-clone-agent` (AI ajanı).

Mimari: hesap yalnızca `src/gpower_clone/engine.py` içindeki `calculate()` fonksiyonundadır. CLI (`cli.py`), MCP sunucusu (`mcp_server.py`) ve ajan (`agent.py`, Ollama sağlayıcısı `ollama_agent.py`) bu tek motoru kullanır; MCP ve ajan katmanında hesap kodu yoktur.

```
gpower-clone-agent ──(Claude ya da Ollama araç çağrısı)──► MCP istemcisi ──stdio──► gpower-clone-mcp ──► calculate()
gpower-clone (CLI) ──────────────────────────────────────────────────────────────────────────────────► calculate()
```

## 2. Kullanım

Sürüm sorgusu:
```bash
gpower-clone --version
```
Çıktı (`engine` alanı çalıştıran Python sürümünü gösterir):
```json
{"contract_version": "1.0.0", "name": "gpower-clone", "engine": "python 3.13"}
```

### Desteklenen Test Ailesi ve Modlar

Test Ailesi: `chi2-contingency` (Goodness-of-fit tests: Contingency tables)

#### 1. A priori Modu (Gerekli örneklem büyüklüğü hesabı)
```bash
gpower-clone --test chi2-contingency --mode a-priori --w 0.3 --alpha 0.05 --power 0.95 --df 5
```
Çıktı:
```json
{"ncp": 19.8, "critical_chi2": 11.070497693516351, "n_total": 220, "actual_power": 0.9502155018970163}
```

#### 2. Post hoc Modu (Ulaşılan güç hesabı)
```bash
gpower-clone --test chi2-contingency --mode post-hoc --w 0.3 --alpha 0.05 --n_total 100 --df 5
```
Çıktı:
```json
{"ncp": 9.0, "critical_chi2": 11.070497693516351, "power": 0.6235846116825704}
```

#### 3. Compromise Modu (β/α oranına göre α ve güç hesabı)
```bash
gpower-clone --test chi2-contingency --mode compromise --w 0.3 --beta_alpha_ratio 1 --n_total 100 --df 5
```
Çıktı:
```json
{"ncp": 9.0, "critical_chi2": 7.680495430077545, "alpha": 0.17474549408567286, "beta": 0.17474549408567286, "power": 0.8252545059143271}
```

#### 4. Criterion Modu (Gereken α hesabı)
```bash
gpower-clone --test chi2-contingency --mode criterion --w 0.3 --power 0.95 --n_total 100 --df 5
```
Çıktı:
```json
{"ncp": 9.0, "critical_chi2": 4.661845179413014, "alpha": 0.4585252929820489}
```

#### 5. Sensitivity Modu (Saptanabilir en küçük etki büyüklüğü hesabı)
```bash
gpower-clone --test chi2-contingency --mode sensitivity --alpha 0.05 --power 0.95 --n_total 100 --df 5
```
Çıktı:
```json
{"ncp": 19.78013437390676, "critical_chi2": 11.070497693516351, "w": 0.44474862983382824}
```

## 3. Testleri Çalıştırma

Tüm test paketini çalıştırmak için (`pip install -e ".[dev]"` sonrası, sanal ortam etkinken):

```bash
pytest -v
```

Sanal ortamı etkinleştirmeden Windows'ta: `.venv\Scripts\python.exe -m pytest -v`. Atlanan testlerin nedenini görmek için `-rs` ekleyin. Ollama çalışmıyorsa `tests/test_ollama_live.py` **atlanır** (geçmiş sayılmaz).

| Dosya | Kapsam |
|---|---|
| `tests/test_engine.py`, `tests/test_vectors.py`, `tests/test_cli.py` | Motor, referans vektörleri, CLI biçimi ve hata kodları |
| `tests/test_mcp_equivalence.py` | CONTRACT.md §9'daki 25 vektör + `public_vectors_chi2.jsonl` + hatalı girişler için CLI stdout satırı ile MCP metin çıktısının **birebir aynı** olduğu; aracın tek ve adının `power_analysis` olduğu |
| `tests/test_mcp_errors.py` | MCP üzerinden eksik (`MISSING_PARAM`), bilinmeyen/ilgisiz (`UNKNOWN_PARAM`), hatalı tip (`INVALID_VALUE`), aralık dışı (`OUT_OF_RANGE`), tutarsız (`INCONSISTENT`) ve desteklenmeyen (`UNSUPPORTED`) girdiler |
| `tests/test_agent.py` | Sahte (betikli) Claude + gerçek MCP sunucusu ile ajan: araç çağrısı, log biçimi, hata loglama, stdio alt süreç testi. Ağ ve API anahtarı gerektirmez |
| `tests/test_agent_ollama.py` | Sahte Ollama modeli + gerçek MCP sunucusu: araç çağrısı ve log, uydurma sonuç koruması, HTTP katmanı (`MockTransport`), sağlayıcı/model yapılandırması, anahtarsız çalışma. Ağ gerektirmez |
| `tests/test_ollama_live.py` | Gerçek yerel Ollama modeli ile uçtan uca test (N=220). Ollama çalışmıyorsa ya da model indirilmemişse **atlanır** (skip) |

> Sözleşmedeki 25 vektörün 20'si bu projenin kapsamı dışındaki ailelere aittir; bunlarda CLI ve MCP aynı `UNSUPPORTED` hatasını döner ve eşdeğerlik testi bunu doğrular.

## 4. MCP Sunucusu

Tek araç: **`power_analysis`**. Girdi alanları CLI bayraklarıyla aynıdır (`test`, `mode` zorunlu; diğerleri moda göre zorunlu). Çıktı, CLI'nin stdout'a yazdığı tek satır JSON'un aynısıdır ve metin içeriği olarak döner; hata durumunda aynı hata JSON'u `isError: true` ile döner.

Sunucuyu stdio üzerinden başlatma:

```bash
gpower-clone-mcp
# ya da
python -m gpower_clone.mcp_server
```

Bir MCP istemcisine (ör. Claude Desktop / Claude Code) ekleme örneği (`command` olarak sanal ortamdaki tam yolu verin):

```json
{
  "mcpServers": {
    "gpower-clone": {
      "command": "C:\\path\\to\\gpower-clone\\.venv\\Scripts\\gpower-clone-mcp.exe"
    }
  }
}
```

Claude Code için: `claude mcp add gpower-clone -- <tam-yol>/gpower-clone-mcp`

Örnek çağrı ve yanıt:

```json
{"test": "chi2-contingency", "mode": "a-priori", "w": 0.3, "alpha": 0.05, "power": 0.95, "df": 5}
```
```json
{"ncp": 19.8, "critical_chi2": 11.070497693516351, "n_total": 220, "actual_power": 0.9502155018970163}
```

Tasarım notu: SDK'nın düşük seviye `Server` sınıfı kullanılır ve argümanlar SDK tarafından doğrulanmadan/dönüştürülmeden doğrudan `calculate()`'e iletilir. Böylece bilinmeyen alanlar (`UNKNOWN_PARAM`) ve tam sayı yerine ondalık (`INVALID_VALUE`) gibi durumlar CLI ile aynı hata kodlarını üretir.

## 5. AI Ajanı

`gpower-clone-agent`, Türkçe soruları anlayan bir ajandır. Varsayılan sağlayıcı Claude'dur (`claude-opus-5-5`); API anahtarı olmadan yerel model için aşağıdaki Ollama bölümüne bakın. MCP sunucusunu stdio alt süreci olarak başlatır, `power_analysis` aracını MCP üzerinden keşfeder ve çağırır; sayısal sonuçları kendisi hesaplamaz.

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
# bash
export ANTHROPIC_API_KEY="sk-ant-..."

# Tek soru
gpower-clone-agent "Kurgusal bir çalışmada iki tedavi kolunun yanıt oranlarını 2x3 tabloyla karşılaştıracağız. w=0.3, alfa 0.05, güç 0.80 için kaç katılımcı gerekir?"

# Etkileşimli mod (boş satır ya da 'çık' ile çıkılır)
gpower-clone-agent
```

Seçenekler:

| Seçenek | Ortam değişkeni | Varsayılan |
|---|---|---|
| `--provider anthropic\|ollama` | `GPOWER_AGENT_PROVIDER` | `anthropic` |
| `--model` | `GPOWER_AGENT_MODEL` | `claude-opus-5-5` (anthropic), `qwen2.5:7b` (ollama) |
| `--ollama-host` | `OLLAMA_HOST` | `http://localhost:11434` |
| `--log` | `GPOWER_AGENT_LOG` | `logs/agent_calls.jsonl` |

### Ollama ile yerel model (API anahtarı gerekmez)

Ajan, Ollama üzerinden yerel bir modelle de çalışır. Bu yolda `anthropic` paketi hiç kullanılmaz ve `ANTHROPIC_API_KEY` gerekmez. Ollama REST API'si, MCP SDK'nın zaten bağımlı olduğu `httpx2` ile çağrılır; ek paket kurmak gerekmez.

1. Ollama'yı kurun (Windows):
   ```powershell
   winget install Ollama.Ollama
   ```
   macOS/Linux için: https://ollama.com/download. Kurulumdan sonra Ollama arka planda çalışır; çalışmıyorsa `ollama serve` ile başlatın.
2. Modeli indirin (~4.7 GB):
   ```powershell
   ollama pull qwen2.5:7b
   ollama list
   ```
   Daha hafif bir alternatif: `ollama pull qwen2.5:3b` (4 GB VRAM'e sığar ama araç çağırmada daha az güvenilirdir); kullanmak için `--model qwen2.5:3b`.
3. Gerçek MCP + ajan demosu (log yolu göreli olduğu için proje kök dizininden çalıştırın):
   ```powershell
   gpower-clone-agent --provider ollama "Kurgusal bir araştırma senaryosu: kontenjans tablosu için ki-kare testi planlıyoruz. Etki büyüklüğü w=0.3, alpha=0.05, power=0.95 ve df=5. Gerekli toplam örneklem büyüklüğü nedir?"
   Get-Content logs\agent_calls.jsonl
   ```
   Beklenen: Yanıtta ve log satırının `tool_output` alanında `"n_total": 220`. Ajan, model yanıtının altına MCP aracının ham çıktısını da yazdırır.
4. Canlı testi çalıştırın (Ollama yoksa atlanır):
   ```powershell
   pytest -v -rs tests/test_ollama_live.py
   ```

Uydurma sonuç koruması (yalnızca Ollama sağlayıcısında): Yerel model yapılandırılmış bir araç çağrısı (`tool_calls`) üretmezse ajan sonuç göstermez ve `HATA: Model yapılandırılmış araç çağrısı üretmedi; hesap sonucu gösterilmiyor.` mesajını yazar (tek soru modunda çıkış kodu `1`). Bu iki durumda olur:
- model araç çağrısını metin içinde JSON olarak yazarsa (bu çağrı **çalıştırılmaz**), ya da
- o soru için araç çağrılmadığı hâlde yanıt; kullanıcının sorusunda, sistem istemindeki Cohen eşiklerinde ya da önceki araç çıktılarında geçmeyen bir sayı içerirse.

"df değerini belirtir misiniz?" gibi açıklama soruları bu kontrolden geçer. Log biçimi iki sağlayıcıda da aynıdır; Ollama için `tokens_in`/`tokens_out`, Ollama'nın `prompt_eval_count`/`eval_count` değerleridir.

Ajan davranışı:
- Eksik parametrede hesaplamadan önce soru sorar; varsayılan değer uydurmaz.
- "Orta etki" gibi kategorilerde Cohen eşiğini önerir ve onay ister (CONTRACT.md §10).
- Araç hata JSON'u dönerse hatayı Türkçe açıklar.
- Yalnızca kurgusal araştırma senaryolarıyla kullanılmalıdır; soruya gerçek hasta verisi yazmayın.

### Araç çağrısı logu

Her araç çağrısı `logs/agent_calls.jsonl` dosyasına bir satır olarak eklenir (CONTRACT.md §8):

```json
{"ts": "2026-10-25T14:02:11+03:00", "question": "...", "tool_input": {"test": "chi2-contingency", "mode": "a-priori", "w": 0.3, "alpha": 0.05, "power": 0.95, "df": 5}, "tool_output": {"ncp": 19.8, "critical_chi2": 11.070497693516351, "n_total": 220, "actual_power": 0.9502155018970163}, "tokens_in": 0, "tokens_out": 0}
```

`tokens_in`/`tokens_out`, aracı çağıran model yanıtının `usage` değerleridir; bir yanıtta birden fazla araç çağrısı varsa tokenlar yalnızca ilk satıra yazılır (toplamlar iki kez sayılmaz). Varsayılan log yolu çalışılan dizine göredir; `logs/` dizini `.gitignore`'dadır.

Sınırlama: Ajanın sayı uydurmaması sistem istemiyle sağlanır; testler araç çağrısı yolunu doğrular, ancak bir dil modelinin davranışı %100 garanti edilemez. Kesin sonuç için araç çıktısı (log) esastır.
