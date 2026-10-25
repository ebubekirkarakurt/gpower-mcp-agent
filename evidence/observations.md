# G*Power 3.1.9.7 Davranış Gözlem Defteri (`chi2-contingency`)

**Referans Kâhin:** G*Power 3.1.9.7 (Windows)  
**Sözleşme Test Kimliği:** `chi2-contingency` (Bölüm 4.4, Kod: K4)  
**Sözleşmedeki G*Power Karşılığı:** `χ² tests – Goodness-of-fit tests: Contingency tables`  

---

## 1. Temiz Oda ve Kanıt Kuralları

1. **Test Vektörleri Kanıt Değildir:** `public_vectors_chi2.jsonl` ve `CONTRACT.md` içindeki değerler doğrulama amaçlıdır. Buradaki hiçbir kayıt referans vektörlerine dayandırılamaz.
2. **Yalnızca Gerçek Gözlem:** Her bir kayıt, G*Power 3.1.9.7 Windows GUI arayüzünde bizzat uygulanan deneylerden, ekrandaki alanlardan ve "Protocol of power analyses" metinlerinden elde edilmelidir.
3. **Uydurma ve Varsayım Yasaktır:** Deneyi yapılmamış hiçbir değer veya davranış buraya "gözlemlendi" olarak yazılamaz.
4. **Kimlik Formatı:** Bu aileye ait her gözlem `[REA-CHI2-xxx]` benzersiz kimliğiyle etiketlenir.
5. **Hedef Dışı Notlar:** Dosyanın sonundaki `t-paired` kayıtları tarihsel amaçla saklanmakta olup `chi2-contingency` için **kesinlikle kanıt sayılmaz**.

---

## 2. G*Power GUI Arayüz Doğrulama Kontrol Listesi

G*Power arayüzü açıldığında ilk olarak aşağıdaki arayüz alanları doğrulanacaktır:

- [x] **Test Family Açılır Menüsü:** `χ² tests` seçeneği mevcut mu? $\rightarrow$ **Mevcut** (`[OBSERVED]`)
- [x] **Statistical Test Açılır Menüsü:** Tam olarak `Goodness-of-fit tests: Contingency tables` mi yazıyor? $\rightarrow$ **Evet, tam eşleşiyor** (`[OBSERVED]`)
- [x] **Type of Power Analysis (Desteklenen Modlar Kontrolü):**
  - [x] `Post hoc: Compute achieved power` $\rightarrow$ **Mevcut ve test edildi** (`[OBSERVED]`)
  - [x] `A priori: Compute required sample size` $\rightarrow$ **Mevcut ve test edildi** (`[OBSERVED]`)
  - [x] `Compromise: Compute implied α & power` $\rightarrow$ **Mevcut ve test edildi** (`[OBSERVED]`)
  - [x] `Criterion: Compute required α` $\rightarrow$ **Mevcut ve test edildi** (`[OBSERVED]`)
  - [x] `Sensitivity: Compute required effect size` $\rightarrow$ **Mevcut ve test edildi** (`[OBSERVED]`)
- [ ] **Girdi Alanları Kontrolü:**
  - [x] `Effect size w` alanı var mı? $\rightarrow$ **Mevcut** (`[OBSERVED]`)
  - [x] `Df` alanı var mı? (Tamsayı mı?) $\rightarrow$ **Mevcut** (`[OBSERVED]`)
  - [x] `Tail(s)` seçeneği **YOK** mu? $\rightarrow$ **Yok** (`[OBSERVED]`)

---

## 3. Gözlem Kayıtları

### 3.1 Grup A: Öncelikli Deneyler (Temel Hesaplama, N Arama, df ve Hatalar)

#### [REA-CHI2-001] GUI Test Seçeneği ve Desteklenen Modların Doğrulanması
- **Durum:** `[OBSERVED]`
- **Kaynak:** G*Power 3.1.9.7 Windows GUI
- **Tarih:** 2026-10-22 23:30:27
- **Gözlenen Arayüz Seçenekleri:**
  - Test family: `χ² tests` `[OBSERVED]`
  - Statistical test: `Goodness-of-fit tests: Contingency tables` `[OBSERVED]`
  - Type of power analysis: `Post hoc: Compute achieved power` `[OBSERVED]`
- **Çıkarılan Kural ve Doğrulanan Davranış:**
  - Sözleşmedeki `χ² tests` ve `Goodness-of-fit tests: Contingency tables` adlandırmasının G*Power GUI'siyle tam ve birebir eşleştiği doğrulanmıştır (`[OBSERVED]`).
  - `Post hoc: Compute achieved power` modunun bu test için aktif ve kullanılabilir olduğu doğrulanmıştır (`[OBSERVED]`). (Diğer 4 mod henüz test edilmemiş olup `[UNVERIFIED]` statüsündedir).

---

#### [REA-CHI2-002] `post-hoc` Modu Temel Hesaplama ve Çıktı Alanları
- **Durum:** `[OBSERVED]`
- **Kaynak:** G*Power 3.1.9.7 Windows GUI
- **Tarih:** 2026-10-22 23:30:27
- **Analiz Modu:** Post hoc: Compute achieved power
- **G*Power Girdi Parametreleri:**
  - Effect size w: `0.3` `[OBSERVED]`
  - α err prob: `0.05` `[OBSERVED]`
  - Total sample size: `100` `[OBSERVED]`
  - Df: `5` `[OBSERVED]`
- **Gözlenen Çıktı Değerleri:**
  - Noncentrality parameter λ: `9.0000000` `[OBSERVED]`
  - Critical χ²: `11.0704977` `[OBSERVED]`
  - Power (1-β err prob): `0.6235846` `[OBSERVED]`
- **Çıkarılan Kural ve Doğrulanan Davranış:**
  - **NCP (Merkezsizlik Parametresi):** Gözlenen $\lambda = 9.0000000$ değeri, bu parametre setinde $\lambda = w^2 \cdot N = 0.3^2 \times 100 = 9.0$ formülüyle tam eşleşmektedir (`[OBSERVED]`).
  - **Kritik $\chi^2$:** Gözlenen $11.0704977$ değeri, serbestlik derecesi $df=5$ olan merkezi ki-kare dağılımının $1-\alpha = 0.95$ kuantili ile ($\chi^2_{0.95, 5} \approx 11.07049769$) tam eşleşmektedir (`[OBSERVED]`).
  - **Ulaşılan Güç:** Gözlenen $0.6235846$ değeri, serbestlik derecesi $df=5$ ve merkezsizlik parametresi $\lambda=9.0$ olan merkezsiz ki-kare dağılımında $P(\chi'^2 \ge 11.0704977) = 0.6235846$ teorik değeriyle tam örtüşmektedir (`[OBSERVED]`).
  - **Vektör Eşleşmesi:** Resmî sözleşme vektörü `chi2-contingency/post-hoc` ile gerçek G*Power çıktısı tam olarak doğrulanmıştır.

---

#### [REA-CHI2-003] `a-priori` Modunda Kademeli Güç ve Örneklem Büyüklüğü ($N$) Gözlemi
- **Durum:** `[OBSERVED]`
- **Kaynak:** G*Power 3.1.9.7 Windows GUI
- **Tarih:** 2026-10-22
- **Test:** `χ² tests - Goodness-of-fit tests: Contingency tables` `[OBSERVED]`
- **Analiz Modu:** `A priori: Compute required sample size` `[OBSERVED]`
- **Ortak Girdiler:**
  - Effect size w: `0.3` `[OBSERVED]`
  - α err prob: `0.05` `[OBSERVED]`
  - Df: `5` `[OBSERVED]`

- **Gözlenen Kademeli Sonuçlar:**
  1. **Hedef Power = 0.949:**
     - Noncentrality parameter λ: `19.7100000` `[OBSERVED]`
     - Critical χ²: `11.0704977` `[OBSERVED]`
     - Total sample size N: `219` `[OBSERVED]`
     - Actual power: `[NOT RECORDED]` *(Protokol çıktısında yer almadığı için kaydedilmedi; kural gereği hesaplanmadı veya tahmin edilmedi)*
  2. **Hedef Power = 0.950:**
     - Noncentrality parameter λ: `19.8000000` `[OBSERVED]`
     - Critical χ²: `11.0704977` `[OBSERVED]`
     - Total sample size N: `220` `[OBSERVED]`
     - Actual power: `0.9502155` `[OBSERVED]`
  3. **Hedef Power = 0.951:**
     - Noncentrality parameter λ: `19.8900000` `[OBSERVED]`
     - Critical χ²: `11.0704977` `[OBSERVED]`
     - Total sample size N: `221` `[OBSERVED]`
     - Actual power: `0.9511813` `[OBSERVED]`

- **Çıkarılan Kural ve Yorum Sınırları:**
  - Bu değerler gerçek GUI gözlemleridir (`[OBSERVED]`).
  - Gözlemler, bu üç hedef güç değeri ($0.949$, $0.950$, $0.951$) için $N$'nin sırasıyla $219$, $220$ ve $221$ olduğunu doğrular (`[OBSERVED]`).
  - $\lambda = w^2 \cdot N$ bağıntısı her üç kademeyle de tam uyumludur ($0.3^2 \times 219 = 19.71$, $0.3^2 \times 220 = 19.80$, $0.3^2 \times 221 = 19.89$) (`[OBSERVED]`).
  - Resmî sözleşme vektörü `chi2-contingency/a-priori` ($w=0.3, \alpha=0.05, \text{power}=0.95, df=5 \implies N=220, \lambda=19.8, \chi^2_{crit}=11.0704977, \text{actual\_power}=0.9502155$) gerçek GUI gözlemiyle birebir doğrulanmıştır.
  - **Kritik Kısıt:** Bu üç gözlem tek başına algoritmanın her durumda kesin olarak `ceil` kullandığını kanıtlamaz; dolayısıyla evrensel `ceil` davranışı genel kural olarak kesinleştirilmemiş, araştırılan bir hipotez olarak bırakılmıştır (`[UNVERIFIED - Evrensel kural doğrulanmadı]`).

---

#### [REA-CHI2-004] `compromise` Modu Temel Hesaplama ve $\beta/\alpha$ Dengelemesi
- **Durum:** `[OBSERVED]`
- **Kaynak:** G*Power 3.1.9.7 Windows GUI
- **Tarih:** 2026-10-22
- **Test:** `χ² tests - Goodness-of-fit tests: Contingency tables` `[OBSERVED]`
- **Analiz Modu:** `Compromise: Compute implied α & power` `[OBSERVED]`
- **Girdiler:**
  - Effect size w: `0.3` `[OBSERVED]`
  - β/α ratio: `1` `[OBSERVED]`
  - Total sample size: `100` `[OBSERVED]`
  - Df: `5` `[OBSERVED]`
- **Gözlenen Çıktılar:**
  - Noncentrality parameter λ: `9.0000000` `[OBSERVED]`
  - Critical χ²: `7.6804954` `[OBSERVED]`
  - α err prob: `0.1747455` `[OBSERVED]`
  - β err prob: `0.1747455` `[OBSERVED]`
  - Power (1-β err prob): `0.8252545` `[OBSERVED]`
- **Çıkarılan Kural ve Yorum Sınırları:**
  - Bu değerler gerçek GUI gözlemleridir (`[OBSERVED]`).
  - $\alpha$ ve $\beta$ değerlerinin tam olarak eşit çıkması ($0.1747455$), bu gözlemdeki `β/α ratio = 1` girdisiyle uyumludur (`[OBSERVED]`).
  - Güç $= 1 - \beta = 1 - 0.1747455 = 0.8252545$ ilişkisi doğrulanmıştır (`[OBSERVED]`).
  - Resmî sözleşme vektörü `chi2-contingency/compromise` ile GUI çıktısı 7 ondalık basamakta tam olarak eşleşmektedir.
  - Gözlem dışında kalan genel davranışlar hakkında kesin evrensel kurallar iddia edilmemiştir (`[UNVERIFIED - Genel kurallar doğrulanmadı]`).

---

#### [REA-CHI2-005] `criterion` Modu Temel Hesaplama ve Gereken $\alpha$ Çıktısı
- **Durum:** `[OBSERVED]`
- **Kaynak:** G*Power 3.1.9.7 Windows GUI
- **Tarih:** 2026-10-22
- **Test:** `χ² tests - Goodness-of-fit tests: Contingency tables` `[OBSERVED]`
- **Analiz Modu:** `Criterion: Compute required α` `[OBSERVED]`
- **Girdiler:**
  - Effect size w: `0.3` `[OBSERVED]`
  - Power (1-β err prob): `0.95` `[OBSERVED]`
  - Total sample size: `100` `[OBSERVED]`
  - Df: `5` `[OBSERVED]`
- **Gözlenen Çıktılar:**
  - Noncentrality parameter λ: `9.0000000` `[OBSERVED]`
  - Critical χ²: `4.6618452` `[OBSERVED]`
  - α err prob: `0.4585253` `[OBSERVED]`
- **Çıkarılan Kural ve Yorum Sınırları:**
  - Bu değerler gerçek GUI gözlemleridir (`[OBSERVED]`).
  - Resmî sözleşme vektörü `chi2-contingency/criterion` ile GUI çıktısı 7 ondalık basamakta tam olarak eşleşmektedir.
  - Yalnızca gerçekten gözlenen bu değerler kaydedilmiş, genelleştirilmiş evrensel kurallar çıkarılmamıştır (`[UNVERIFIED - Genelleştirilmedi]`).

---

#### [REA-CHI2-006] `sensitivity` Modu (Saptanabilir En Küçük $w$)
- **Durum:** `[OBSERVED]`
- **Kaynak:** G*Power 3.1.9.7 Windows GUI
- **Tarih:** 2026-10-22
- **Test:** `χ² tests - Goodness-of-fit tests: Contingency tables` `[OBSERVED]`
- **Analiz Modu:** `Sensitivity: Compute required effect size` `[OBSERVED]`
- **Girdiler:**
  - α err prob: `0.05` `[OBSERVED]`
  - Power (1-β err prob): `0.95` `[OBSERVED]`
  - Total sample size: `100` `[OBSERVED]`
  - Df: `5` `[OBSERVED]`
- **Gözlenen Çıktılar:**
  - Noncentrality parameter λ: `19.7801344` `[OBSERVED]`
  - Critical χ²: `11.0704977` `[OBSERVED]`
  - Effect size w: `0.4447486` `[OBSERVED]`
- **Çıkarılan Kural ve Yorum Sınırları:**
  - Bu değerler gerçek GUI gözlemleridir (`[OBSERVED]`).
  - Resmî sözleşme vektörü `chi2-contingency/sensitivity` ile GUI çıktısı 7 ondalık basamakta tam olarak eşleşmektedir.
  - $\lambda$ parametresinden $w$ etki büyüklüğüne geçişte $w = \sqrt{\lambda / N} = \sqrt{19.7801344 / 100} = \sqrt{0.197801344} \approx 0.4447486$ bağıntısı doğrulanmıştır (`[OBSERVED]`).
  - Değerler yuvarlanmadan veya değiştirilmeden birebir kaydedilmiştir.

---

### 3.2 Grup B: İkincil Deneyler ve Sınır Davranışları

#### [REA-CHI2-007] Geçersiz Girdiler ve Tutarsızlık Kontrolleri
- **Durum:** `[BEKLEMEDE / PENDING EXPERIMENT]`
- **Tarih:** 
- **Test Edilen Durumlar:**
  1. $w = 0$ veya $w = -0.3$
  2. $\alpha \le 0$ veya $\alpha \ge 1$
  3. $\text{power} \le \alpha$ (Örn: A priori modunda $\alpha=0.80$, $\text{power}=0.20$)
  4. Total sample size $N = 1$ (Post hoc modunda)
- **G*Power Ekran / Hata Diyaloğu:**
  ```text
  [Hata mesajları buraya yazılacak]
  ```
- **Çıkarılan Kural ve Doğrulanan Davranış:**
  - G*Power bu durumları hesaplıyor mu, yoksa hata diyaloğu mu açıyor?
  - Sözleşmedeki `OUT_OF_RANGE` ve `INCONSISTENT` kuralları doğrulanıyor mu?

---

#### [REA-CHI2-008] Serbestlik Derecesi ($df$) Girdi Davranışları ve Sınırları
- **Durum:** `[BEKLEMEDE / PENDING EXPERIMENT]`
- **Tarih:** 
- **Amaç:** `df` girdisinin minimum sınırını ve ondalık/sıfır girdi tepkisini saptamak.
- **Test Edilen Girdiler (Post hoc modunda):**
  1. $df = 1$ ($2 \times 2$ tablosu): $w=0.3, \alpha=0.05, N=100$
  2. $df = 0$: Calculate butonuna basıldığında GUI tepkisi
  3. $df = -1$: Calculate butonuna basıldığında GUI tepkisi
  4. $df = 2.5$ (Ondalık serbestlik derecesi): GUI tepkisi
- **G*Power Arayüz Tepkisi / Hata Pencereleri:**
  ```text
  [Hata mesaj kutusu metinlerini buraya yazın]
  ```
- **Çıkarılan Kural ve Doğrulanan Davranış:**
  - Minimum $df$ değeri kaçtır? ($df \ge 1$).
  - Ondalık $df$ kabul ediliyor mu, reddediliyor mu?

---

#### [REA-CHI2-009] Minimum Örneklem Büyüklüğü Sınırı ($N_{min}$)
- **Durum:** `[BEKLEMEDE / PENDING EXPERIMENT]`
- **Tarih:** 
- **Analiz Modu:** A priori: Compute required sample size
- **G*Power Girdi Parametreleri:**
  - Effect size w: `5.0` (Aşırı büyük etki)
  - α err prob: `0.05`
  - Power: `0.99`
  - Df: `1` ve `5`
- **G*Power Protokol Çıktısı:**
  ```text
  [Çıktıyı buraya yapıştırın]
  ```
- **Çıkarılan Kural ve Doğrulanan Davranış:**
  - $N$ minimum kaça inebiliyor? ($N = 2$ mi, yoksa $N \ge df + 1$ kısıtı var mı?)

---

## 4. Ek: Tarihsel Notlar (Geçersiz Kılınan `t-paired` Gözlemleri)

> [!WARNING]
> Aşağıdaki kayıtlar daha önce yanlış hedef aile (`t-paired`) üzerinde yapılan gözlemleri içermektedir. Bu kayıtlar tarihsel doğruluk adına saklanmakta olup, **`chi2-contingency` test ailesi için KESİNLİKLE kanıt teşkil etmez**.

### [ARCHIVE-REA-001] (t-paired) Çift Kuyruk Post-hoc Gözlemi
- **Tarih:** 2026-10-22
- **Test:** t tests -> Difference between two dependent means (matched pairs)
- **Girdiler:** Tail(s): Two, dz: 0.5, alpha: 0.05, n_total: 45
- **Çıktılar:** δ: 3.3541020, Critical t: 2.0153676, Df: 44, Power: 0.9065953
- **Durum:** `[GEÇERSİZ - HEDEF DIŞI AİLE]`

### [ARCHIVE-REA-011] (t-paired) Tek Kuyruk Post-hoc Protokol Gözlemi
- **Tarih:** 2026-10-22
- **Test:** t tests -> Difference between two dependent means (matched pairs)
- **Girdiler:** Tail(s): One, dz: 0.5, alpha: 0.05, n_total: 45
- **Çıktılar:** δ: 3.3541020, Critical t: 1.6802300, Df: 44, Power: Paylaşılmadı
- **Durum:** `[GEÇERSİZ - HEDEF DIŞI AİLE]`
