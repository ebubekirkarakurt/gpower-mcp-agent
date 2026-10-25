import json
import math
import subprocess
from pathlib import Path
from scipy.stats import chi2, ncx2

ROOT = Path("C:/Users/ebuka/Desktop/yazilim_gercekleme_test/gpower-clone")
EXE = ROOT / ".venv/Scripts/gpower-clone.exe"

print("=== 1. CONTRACT VECTOR COMPARISON ===")
contract_path = ROOT / "CONTRACT.md"
chi2_vectors_path = ROOT / "public_vectors_chi2.jsonl"

with open(contract_path, "r", encoding="utf-8") as f:
    contract_lines = [
        l.strip()
        for l in f
        if "chi2-contingency" in l and l.strip().startswith('{"id":"chi2-contingency/')
    ]

with open(chi2_vectors_path, "r", encoding="utf-8") as f:
    file_lines = [l.strip() for l in f if l.strip()]

assert len(contract_lines) == 5, f"Expected 5 vectors in CONTRACT.md, got {len(contract_lines)}"
assert len(file_lines) == 5, f"Expected 5 vectors in public_vectors_chi2.jsonl, got {len(file_lines)}"

for i, (c, fl) in enumerate(zip(contract_lines, file_lines)):
    c_obj = json.loads(c)
    f_obj = json.loads(fl)
    match = (c_obj == f_obj)
    print(f"Vector {i+1} [{c_obj['id']}]: match={match}")
    assert match, f"Mismatch in vector {c_obj['id']}"

print("\n=== 2. VECTOR EXECUTION & REAL OUTPUT COMPARISON ===")
from gpower_clone.engine import calculate

for vec in [json.loads(l) for l in file_lines]:
    inp = vec["input"]
    exp = vec["expected"]
    res = calculate(inp)
    
    # CLI execution test
    cmd = [str(EXE)]
    for k, v in inp.items():
        cmd.extend([f"--{k}", str(v)])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"CLI failed with code {proc.returncode}"
    cli_out = json.loads(proc.stdout.strip())
    
    print(f"\nVector: {vec['id']}")
    print(f"  Inputs:   {inp}")
    print(f"  Expected: {exp}")
    print(f"  Engine:   {res}")
    print(f"  CLI Out:  {cli_out}")
    
    for k, v in exp.items():
        diff = abs(res[k] - v)
        rel = diff / abs(v) if v != 0 else diff
        print(f"    Field '{k}': exp={v}, got={res[k]}, abs_diff={diff:.2e}, rel_diff={rel:.2e}")
        if isinstance(v, int):
            assert res[k] == v
            assert cli_out[k] == v
        else:
            assert diff <= 1e-6 or rel <= 1e-6

print("\n=== 3. A-PRIORI MINIMAL N VERIFICATION (N-1 vs N) ===")
from gpower_clone.engine import compute_a_priori

cases = [
    {"w": 0.3, "alpha": 0.05, "power": 0.95, "df": 5, "name": "Base Vector"},
    {"w": 0.5, "alpha": 0.01, "power": 0.80, "df": 1, "name": "Edge 1 (df=1, alpha=0.01)"},
    {"w": 0.1, "alpha": 0.05, "power": 0.90, "df": 10, "name": "Edge 2 (df=10, w=0.1)"},
    {"w": 0.8, "alpha": 0.001, "power": 0.99, "df": 2, "name": "Edge 3 (alpha=0.001, power=0.99)"},
]

for c in cases:
    res = compute_a_priori(w=c["w"], alpha=c["alpha"], power=c["power"], df=c["df"])
    N = res["n_total"]
    crit = res["critical_chi2"]
    
    # Check N
    p_at_N = float(ncx2.sf(crit, c["df"], c["w"]**2 * N))
    # Check N-1
    if N > 2:
        p_at_prev = float(ncx2.sf(crit, c["df"], c["w"]**2 * (N - 1)))
    else:
        p_at_prev = float(ncx2.sf(crit, c["df"], c["w"]**2 * 1))
        
    print(f"Case: {c['name']} (target_power={c['power']})")
    print(f"  Found N={N}")
    print(f"  Power at N-1 ({N-1}): {p_at_prev:.7f} (< target: {p_at_prev < c['power']})")
    print(f"  Power at N   ({N}):   {p_at_N:.7f} (>= target: {p_at_N >= c['power']})")
    assert p_at_N >= c["power"]
    if N > 2:
        assert p_at_prev < c["power"], f"N is not minimal! Power at N-1 is {p_at_prev} >= {c['power']}"

print("\n=== 4. DIRECTION OF TAILS & CRITICAL VALUES ===")
# Post hoc direction
crit_05 = float(chi2.ppf(0.95, 5))
crit_01 = float(chi2.ppf(0.99, 5))
assert crit_01 > crit_05, "Alpha decreasing must increase critical value"

# Increasing lambda increases power
p_lam9 = float(ncx2.sf(crit_05, 5, 9.0))
p_lam15 = float(ncx2.sf(crit_05, 5, 15.0))
assert p_lam15 > p_lam9, "Increasing noncentrality must increase power"

# Compromise direction
from gpower_clone.engine import compute_compromise
comp_q1 = compute_compromise(w=0.3, beta_alpha_ratio=1.0, n_total=100, df=5)
comp_q2 = compute_compromise(w=0.3, beta_alpha_ratio=2.0, n_total=100, df=5)
comp_q05 = compute_compromise(w=0.3, beta_alpha_ratio=0.5, n_total=100, df=5)
print(f"Compromise q=0.5: alpha={comp_q05['alpha']:.5f}, beta={comp_q05['beta']:.5f}, ratio={comp_q05['beta']/comp_q05['alpha']:.4f}")
print(f"Compromise q=1.0: alpha={comp_q1['alpha']:.5f}, beta={comp_q1['beta']:.5f}, ratio={comp_q1['beta']/comp_q1['alpha']:.4f}")
print(f"Compromise q=2.0: alpha={comp_q2['alpha']:.5f}, beta={comp_q2['beta']:.5f}, ratio={comp_q2['beta']/comp_q2['alpha']:.4f}")
assert abs(comp_q1['beta'] / comp_q1['alpha'] - 1.0) < 1e-6
assert abs(comp_q2['beta'] / comp_q2['alpha'] - 2.0) < 1e-6
assert abs(comp_q05['beta'] / comp_q05['alpha'] - 0.5) < 1e-6

print("\n=== 5. CLI ERROR SCENARIOS AUDIT ===")
errors_to_test = [
    (["--test", "chi2-contingency", "--mode", "post-hoc", "--w", "0.3", "--alpha", "0.05", "--n_total", "100", "--df", "0"], "OUT_OF_RANGE", "df", 2),
    (["--test", "chi2-contingency", "--mode", "post-hoc", "--w", "0.3", "--alpha", "0.05", "--n_total", "100", "--df", "-3"], "OUT_OF_RANGE", "df", 2),
    (["--test", "chi2-contingency", "--mode", "post-hoc", "--w", "0.3", "--alpha", "0.05", "--n_total", "100", "--df", "2.5"], "INVALID_VALUE", "df", 2),
    (["--test", "chi2-contingency", "--mode", "post-hoc", "--w", "0.3", "--alpha", "1.2", "--n_total", "100", "--df", "5"], "OUT_OF_RANGE", "alpha", 2),
    (["--test", "chi2-contingency", "--mode", "post-hoc", "--w", "0.3", "--alpha", "0.0", "--n_total", "100", "--df", "5"], "OUT_OF_RANGE", "alpha", 2),
    (["--test", "chi2-contingency", "--mode", "post-hoc", "--w", "0.0", "--alpha", "0.05", "--n_total", "100", "--df", "5"], "OUT_OF_RANGE", "w", 2),
    (["--test", "chi2-contingency", "--mode", "post-hoc", "--w", "-0.5", "--alpha", "0.05", "--n_total", "100", "--df", "5"], "OUT_OF_RANGE", "w", 2),
    (["--test", "chi2-contingency", "--mode", "a-priori", "--w", "0.3", "--alpha", "0.05", "--power", "0.0", "--df", "5"], "OUT_OF_RANGE", "power", 2),
    (["--test", "chi2-contingency", "--mode", "a-priori", "--w", "0.3", "--alpha", "0.05", "--power", "1.0", "--df", "5"], "OUT_OF_RANGE", "power", 2),
    (["--test", "chi2-contingency", "--mode", "post-hoc", "--w", "0.3", "--alpha", "0.05", "--df", "5"], "MISSING_PARAM", "n_total", 2),
    (["--test", "chi2-contingency", "--mode", "post-hoc", "--w", "0.3", "--alpha", "0.05", "--n_total", "100", "--df", "5", "--unknown", "99"], "UNKNOWN_PARAM", "unknown", 2),
    (["--test", "chi2-contingency", "--mode", "post-hoc", "--w", "0.3", "--alpha", "0.05", "--n_total", "100", "--df", "5", "--tails", "2"], "UNKNOWN_PARAM", "tails", 2),
    (["--test", "chi2-contingency", "--mode", "post-hoc", "--w", "0.3", "--alpha", "0.05", "--n_total", "100", "--df", "5", "--power", "0.95"], "UNKNOWN_PARAM", "power", 2),
    (["--test", "chi2-contingency", "--mode", "a-priori", "--w", "0.3", "--alpha", "0.7", "--power", "0.3", "--df", "5"], "INCONSISTENT", "power", 2),
    (["--test", "unknown-test", "--mode", "post-hoc", "--w", "0.3", "--alpha", "0.05", "--n_total", "100", "--df", "5"], "UNSUPPORTED", "test", 2),
]

for args, exp_code, exp_field, exp_exit in errors_to_test:
    proc = subprocess.run([str(EXE)] + args, capture_output=True, text=True)
    assert proc.returncode == exp_exit, f"Expected exit {exp_exit}, got {proc.returncode} for {args}"
    out_obj = json.loads(proc.stdout.strip())
    assert out_obj["code"] == exp_code, f"Expected code {exp_code}, got {out_obj.get('code')} for {args}"
    assert out_obj["field"] == exp_field, f"Expected field {exp_field}, got {out_obj.get('field')} for {args}"
    print(f"Error test PASS: {exp_code} (field={exp_field}, exit={exp_exit}) for {args[-2:] if len(args)>=2 else args}")

print("\nALL AUDIT VERIFICATIONS PASSED SUCCESSFULLY!")
