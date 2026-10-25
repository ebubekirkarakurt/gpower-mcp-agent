# Spesifikasyon Taslağı: G*Power `chi2-contingency` Test Ailesi Yeniden Uygulaması

**Sürüm:** 0.2.0-draft  
**Durum:** TASLAK (Sözleşme bilgileri hariç tüm algoritmik/matematiksel kabuller `[UNVERIFIED]` olarak işaretlenmiştir)  
**Hedef Test Ailesi:** `chi2-contingency` (Bölüm 4.4, Kod: K4)  
**Sözleşme:** [CONTRACT.md](file:///c:/Users/ebuka/Desktop/yazilim_gercekleme_test/gpower-clone/CONTRACT.md)  
**Kanıt Defteri:** [evidence/observations.md](file:///c:/Users/ebuka/Desktop/yazilim_gercekleme_test/gpower-clone/evidence/observations.md)  
**Referans Vektörler:** [public_vectors_chi2.jsonl](file:///c:/Users/ebuka/Desktop/yazilim_gercekleme_test/gpower-clone/public_vectors_chi2.jsonl)  

---

## 1. Amaç ve Doğrulanmış Sözleşme Kuralları (Kesinleşmiş Bilgiler)

`CONTRACT.md` belgesine göre aşağıdaki hususlar sözleşmeyle **bağlayıcı ve doğrulanmıştır**:

1. **Test Kimliği:** `--test chi2-contingency`
2. **Klinik Örnek:** Tedaviye yanıt oranları (kontenjans tabloları).
3. **Analiz Modları ve Zorunluluk Durumu:**
   - Zorunlu modlar: `a-priori`, `post-hoc`.
   - Bonus modlar: `compromise`, `criterion`, `sensitivity`.
4. **`tails` Parametresi KESİNLİKLE YOKTUR:**
   - Sözleşme Bölüm 4.0: `tails` yalnızca t testlerinde kullanılır.
   - Bu ailede `--tails` argümanı verilirse `UNKNOWN_PARAM` hata kodu ile reddedilmelidir.
5. **`df` (Serbestlik Derecesi) Bir GİRDİDİR:**
   - Kontenjans tablolarında serbestlik derecesi örneklem büyüklüğünden ($N$) bağımsız olarak tablo boyutlarına ($r \times c$) bağlıdır: $df = (r-1)(c-1)$.
   - Kullanıcı `df` değerini girdi olarak verir.
   - **Çıktı JSON nesnesinde `df` alanı yer almaz.**
6. **Modlara Göre Parametre Sözleşmesi:**
   - `a-priori`: Girdi $\rightarrow$ `w`, `alpha`, `power`, `df` | Çıktı $\rightarrow$ `ncp`, `critical_chi2`, `n_total`, `actual_power`
   - `post-hoc`: Girdi $\rightarrow$ `w`, `alpha`, `n_total`, `df` | Çıktı $\rightarrow$ `ncp`, `critical_chi2`, `power`
   - `compromise`: Girdi $\rightarrow$ `w`, `beta_alpha_ratio`, `n_total`, `df` | Çıktı $\rightarrow$ `ncp`, `critical_chi2`, `alpha`, `beta`, `power`
   - `criterion`: Girdi $\rightarrow$ `w`, `power`, `n_total`, `df` | Çıktı $\rightarrow$ `ncp`, `critical_chi2`, `alpha`
   - `sensitivity`: Girdi $\rightarrow$ `alpha`, `power`, `n_total`, `df` | Çıktı $\rightarrow$ `ncp`, `critical_chi2`, `w`
7. **Sözleşme Sınır Değerleri:**
   - $w > 0$, $0 < \alpha < 1$, $0 < \text{power} < 1$, $df \ge 1$ (tamsayı), $n\_total \ge 2$ (tamsayı), $beta\_alpha\_ratio > 0$.
8. **Çıktı ve Hata Biçimi:**
   - Başarı durumunda çıkış kodu `0`, stdout'a tek satır JSON, sayılar tam double hassasiyetiyle, tamsayılar integer olarak.
   - Hata durumunda çıkış kodu `2` (girdi hatası) veya `1` (iç hata / çözümsüzlük), format: `{"error": "...", "code": "...", "field": "..."}`.

---

## 2. Matematiksel Hipotezler ve Sayısal Model (`[UNVERIFIED]`)

Aşağıdaki matematiksel bağıntılar istatistik teorisine dayanan çalışma hipotezleridir; **G*Power 3.1.9.7 Windows GUI üzerinde gözlemlenip doğrulanana kadar `[UNVERIFIED]` statüsündedir**.

### 2.1 Hipotezler ve Test İstatistiği
- $H_0$: Satır ve sütun değişkenleri bağımsızdır.
- $H_1$: Değişkenler arasında ilişki / bağımlılık vardır.
- Test istatistiği: $\chi^2 = \sum \frac{(O_{ij} - E_{ij})^2}{E_{ij}}$

### 2.2 Kritik Değer ($\chi^2_{crit}$)
- $H_0$ altında test istatistiği serbestlik derecesi $df$ olan merkezi ki-kare dağılımına uyar: $\chi^2 \sim \chi^2(df)$.
- Kritik değer formülü:
  $$\chi^2_{crit} = \chi^2_{1-\alpha, \, df}$$
  *(Durum: **Doğrulandı** `[REA-CHI2-002]`)*

### 2.3 Merkezsizlik Parametresi (NCP - $\lambda$)
- Alternatif hipotez $H_1$ altında test istatistiği merkezsiz ki-kare dağılımına uyar: $\chi'^2(df, \lambda)$.
- Cohen's $w$ etki büyüklüğü ile merkezsizlik parametresi ilişkisi:
  $$\lambda = w^2 \cdot N$$
  *(Durum: **Doğrulandı** `[REA-CHI2-002]`)*

### 2.4 İstatistiksel Güç (Power)
- Merkezsiz ki-kare dağılımının kümülatif dağılım fonksiyonu $F_{nc\chi^2}(x; df, \lambda)$ olmak üzere, güç formülü:
  $$\text{Power} = P(\chi'^2 \ge \chi^2_{crit}) = 1 - F_{nc\chi^2}(\chi^2_{crit}; df, \lambda)$$
  *(Durum: **Doğrulandı** `[REA-CHI2-002]`)*

---

## 3. Analiz Modlarının Algoritmik Hipotezleri

### 3.1 `post-hoc` Modu
- Girdiler: `w`, `alpha`, `n_total`, `df`
- Algoritma adımları:
  1. $\lambda = w^2 \cdot N$
  2. $\chi^2_{crit} = \text{chi2.ppf}(1 - \alpha, df)$
  3. $\text{power} = \text{ncx2.sf}(\chi^2_{crit}, df, \lambda)$
  *(Durum: **Doğrulandı** `[REA-CHI2-002]`)*

### 3.2 `a-priori` Modu
- Girdiler: `w`, `alpha`, `power`, `df`
- Algoritma adımları:
  1. $\chi^2_{crit} = \text{chi2.ppf}(1 - \alpha, df)$
  2. $\text{ncx2.sf}(\chi^2_{crit}, df, w^2 \cdot n) \ge \text{target\_power}$ şartını sağlayan tamsayı $N$ aranır.
  3. Ulaşılan gerçek güç: $\text{actual\_power} = \text{ncx2.sf}(\chi^2_{crit}, df, w^2 \cdot N)$
  *(Durum: Kısmi Doğrulandı `[REA-CHI2-003]`. Resmî vektör $N=220$ ve kademeli $N=219, 221$ gözlemlendi; evrensel `ceil` kuralı `[UNVERIFIED]`)*
- Minimum örneklem büyüklüğü: $N_{min} = 2$ mi, yoksa $N \ge df + 1$ mi? *(Durum: `[UNVERIFIED]`)*

### 3.3 `sensitivity` Modu
- Girdiler: `alpha`, `power`, `n_total`, `df`
- Algoritma adımları:
  1. $\chi^2_{crit} = \text{chi2.ppf}(1 - \alpha, df)$
  2. $\text{ncx2.sf}(\chi^2_{crit}, df, \lambda) = \text{target\_power}$ denklemini sağlayan $\lambda > 0$ kökü bulunur (SciPy `brentq`).
  3. Saptanabilir etki büyüklüğü: $w = \sqrt{\frac{\lambda}{N}}$
  *(Durum: **Doğrulandı** `[REA-CHI2-006]`. $\alpha=0.05, \text{power}=0.95, N=100, df=5 \implies \lambda=19.7801344, w=0.4447486$)*

### 3.4 `compromise` Modu
- Girdiler: `w`, `beta_alpha_ratio` ($q$), `n_total`, `df`
- Algoritma adımları:
  1. $\lambda = w^2 \cdot N$
  2. $\beta(x) = \text{ncx2.cdf}(x, df, \lambda)$ ve $\alpha(x) = \text{chi2.sf}(x, df)$ olmak üzere:
     $$g(x) = \beta(x) - q \cdot \alpha(x) = 0$$
  3. $g(x) = 0$ kökü olan $\chi^2_{crit}$ sayısal yöntemle çözülür.
  4. $\alpha = \text{chi2.sf}(\chi^2_{crit}, df)$, $\beta = q \cdot \alpha$, $\text{power} = 1 - \beta$
  *(Durum: **Doğrulandı** `[REA-CHI2-004]`. $w=0.3, q=1, N=100, df=5 \implies \alpha=\beta=0.1747455, \chi^2_{crit}=7.6804954, \text{power}=0.8252545$)*

### 3.5 `criterion` Modu
- Girdiler: `w`, `power`, `n_total`, `df`
- Algoritma adımları:
  1. $\lambda = w^2 \cdot N$
  2. Hedef $\beta = 1 - \text{power}$
  3. Merkezsiz ki-kare dağılımında ters kümülatif quantile: $\chi^2_{crit} = \text{ncx2.ppf}(\beta, df, \lambda)$
  4. Merkezi ki-kare dağılımından $\alpha$: $\alpha = \text{chi2.sf}(\chi^2_{crit}, df)$
  *(Durum: **Doğrulandı** `[REA-CHI2-005]`. $w=0.3, \text{power}=0.95, N=100, df=5 \implies \lambda=9.0, \chi^2_{crit}=4.6618452, \alpha=0.4585253$)*

---

## 4. Girdi Doğrulama ve Hata Eşleme Kuralları

| Kontrol Kuralı | Beklenen Hata Kodu | Çıkış Kodu | Durum |
|---|---|---|---|
| Zorunlu parametre eksikliği | `MISSING_PARAM` | 2 | **Doğrulandı (Sözleşme)** |
| `--tails` veya alakasız parametre verilmesi | `UNKNOWN_PARAM` | 2 | **Doğrulandı (Sözleşme)** |
| Tamsayı beklenen yere float verilmesi (`df`, `n_total`) | `INVALID_VALUE` | 2 | **Doğrulandı (Sözleşme)** |
| Aralık dışı girdiler ($w \le 0$, $\alpha \le 0$, $\alpha \ge 1$, $N < 2$, $df < 1$) | `OUT_OF_RANGE` | 2 | **Doğrulandı (Sözleşme)** |
| Mantıksal tutarsızlık ($\text{power} \le \alpha$) | `INCONSISTENT` | 2 | `[UNVERIFIED - REA-CHI2-006 Bekliyor]` |
| Desteklenmeyen test veya mod | `UNSUPPORTED` | 2 | **Doğrulandı (Sözleşme)** |
| Sayısal yakınsama hatası | `NO_SOLUTION` | 1 | `[UNVERIFIED]` |

---

## 5. Doğrulama Durum Takip Matrisi (`chi2-contingency`)

| Kod | İnceleme Konusu | Doğrulama Deneyi | Mevcut Durum |
|---|---|---|---|
| **C-01** | G*Power GUI'sinde testin tam adı ve menü yapısı | `[REA-CHI2-001]` | **Doğrulandı** |
| **C-02** | 5 analiz modunun GUI'de aktif olma durumu | `[REA-CHI2-001]`–`[REA-CHI2-006]` | **Doğrulandı** |
| **C-03** | Merkezsizlik parametresi $\lambda = w^2 N$ formülü | `[REA-CHI2-002]` | **Doğrulandı** |
| **C-04** | Merkezi $\chi^2$ kritik değer hesabı | `[REA-CHI2-002]` | **Doğrulandı** |
| **C-05** | `a-priori` modunda $N$ tavan yuvarlama (`ceil`) davranışı | `[REA-CHI2-003]` | Kısmi (`[REA-CHI2-003]` ile 3 nokta doğrulandı; evrensel `[UNVERIFIED]`) |
| **C-06** | $df$ minimum sınırları ve ondalık reddi | `[REA-CHI2-008]` | `[UNVERIFIED]` |
| **C-07** | $N_{min}$ minimum örneklem büyüklüğü sınırı | `[REA-CHI2-009]` | `[UNVERIFIED]` |
| **C-08** | $\text{power} \le \alpha$ tutarsızlık tepkisi | `[REA-CHI2-007]` | `[UNVERIFIED]` |
| **C-09** | `sensitivity` modu $w$ kök bulma doğrulaması | `[REA-CHI2-006]` | **Doğrulandı** |
| **C-10** | `compromise` modu $\beta/\alpha$ kök bulma doğrulaması | `[REA-CHI2-004]` | **Doğrulandı** |
| **C-11** | `criterion` modu $\alpha$ çözümü doğrulaması | `[REA-CHI2-005]` | **Doğrulandı** |
