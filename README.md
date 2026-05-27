# ABG Interpreter

A Python library for step-by-step interpretation of Arterial Blood Gas (ABG) results.

Given a patient's pH, PaCO2, HCO3 (and optionally PaO2), the library:
- Identifies the primary acid-base disorder
- Calculates the expected compensation using classic formulas
- Checks whether the compensation is appropriate
- Assesses oxygenation and computes the A-a gradient

---

## Installation

```bash
pip install abg-interpreter==0.1
```

---

## Quick Start

```python
from abg_interpreter import ABGInterpreter

interpreter = ABGInterpreter()

result = interpreter.interpret(
    pH    = 7.28,
    PaCO2 = 28,
    HCO3  = 13,
    PaO2  = 90,
    age   = 40,
)

interpreter.print_full_report(result)
```

Output:

```
═══════════════════════════════════════════════════════
  ABG INTERPRETATION
═══════════════════════════════════════════════════════
[Step 1] Classify pH
  → pH = 7.28  ⟹  Acidemia  (< 7.35)

[Step 2] Identify primary disorder
  → HCO3 low + Acidemia  ⟹  Metabolic Acidosis (primary)

[Step 3] Check expected compensation
  → Expected respiratory compensation (Winter's formula):
    PaCO2 = 1.5 × 13 + 8 = 27.5 ±2  →  range 25.5 – 29.5 mmHg
  → ✓ Respiratory compensation is appropriate

[Step 4] Assess oxygenation
  → PaO2 = 90 mmHg  ✓ Normal oxygenation
  → A-a gradient = 24.7 mmHg  ⚠ Elevated (> 14)
    → suggests V/Q mismatch, shunt, or diffusion defect

═══════════════════════════════════════════════════════
  ABG INTERPRETATION SUMMARY
═══════════════════════════════════════════════════════
  pH      : 7.28
  PaCO2   : 28 mmHg
  HCO3    : 13 mEq/L
  PaO2    : 90 mmHg
─────────────────────────────────────────────────────
  Primary disorder : Metabolic Acidosis
  Compensation     : ✓ Respiratory compensation is appropriate
  Oxygenation      : PaO2 = 90 mmHg  ✓ Normal oxygenation
  A-a Gradient     : 24.7 mmHg  ⚠ Elevated (> 14)
═══════════════════════════════════════════════════════
```

---

## Accessing Individual Fields

You don't have to print the full report — you can access any field directly:

```python
print(result.primary_disorder)       # "Metabolic Acidosis"
print(result.compensation_adequacy)  # "✓ Respiratory compensation is appropriate"
print(result.oxygenation_status)     # "PaO2 = 90 mmHg  ✓ Normal oxygenation"
print(result.aa_gradient)            # 24.7
print(result.summary)                # full formatted summary string
```

---

## Normal Reference Ranges

| Parameter | Normal Range         |
|-----------|----------------------|
| pH        | 7.35 – 7.45          |
| PaCO2     | 35 – 45 mmHg         |
| HCO3      | 22 – 26 mEq/L        |
| PaO2      | 80 – 100 mmHg (room air) |

---

## Compensation Formulas

### Metabolic Acidosis → Respiratory Compensation
**Winter's Formula:**
```
Expected PaCO2 = 1.5 × HCO3 + 8  (±2)
```
Example: HCO3 = 13  →  Expected PaCO2 = 27.5 ±2  →  range 25.5 – 29.5 mmHg

---

### Metabolic Alkalosis → Respiratory Compensation
```
Expected PaCO2 = 0.7 × HCO3 + 21  (±2)
```
Example: HCO3 = 38  →  Expected PaCO2 = 47.6 ±2  →  range 45.6 – 49.6 mmHg

---

### Respiratory Acidosis → Metabolic Compensation
```
Acute   → Expected HCO3 = 24 + 0.1  × ΔPCO2
Chronic → Expected HCO3 = 24 + 0.35 × ΔPCO2
```
Example: PaCO2 = 65  →  ΔPCO2 = 25
- Acute   HCO3 = 24 + 0.1  × 25 = **26.5 mEq/L**
- Chronic HCO3 = 24 + 0.35 × 25 = **32.8 mEq/L**

---

### Respiratory Alkalosis → Metabolic Compensation
```
Acute   → Expected HCO3 = 24 - 0.2  × ΔPCO2
Chronic → Expected HCO3 = 24 - 0.5  × ΔPCO2
```
Example: PaCO2 = 28  →  ΔPCO2 = 12
- Acute   HCO3 = 24 - 0.2  × 12 = **21.6 mEq/L**
- Chronic HCO3 = 24 - 0.5  × 12 = **18.0 mEq/L**

---

## A-a Gradient

The Alveolar-arterial gradient measures how well oxygen crosses from the lungs into the blood.

```
PAO2         = FiO2 × (760 - 47) - PaCO2 / 0.8
A-a gradient = PAO2 - PaO2
Normal A-a   = (age / 4) + 4
```

| A-a Gradient | Interpretation |
|---|---|
| ≤ Normal | Normal gas exchange |
| > Normal | V/Q mismatch, shunt, or diffusion defect |

Example: PaO2=90, PaCO2=28, FiO2=0.21, age=40
```
PAO2 = 0.21 × (760-47) - 28/0.8 = 114.7
A-a  = 114.7 - 90 = 24.7 mmHg
Normal for age 40 = 40/4 + 4 = 14
→ 24.7 > 14  ⚠ Elevated
```

---

## Disorders Detected

| Disorder | pH | PaCO2 | HCO3 |
|---|---|---|---|
| Respiratory Acidosis | ↓ | ↑ | normal |
| Respiratory Alkalosis | ↑ | ↓ | normal |
| Metabolic Acidosis | ↓ | normal | ↓ |
| Metabolic Alkalosis | ↑ | normal | ↑ |
| Mixed Resp. + Met. Acidosis | ↓↓ | ↑ | ↓ |
| Mixed Resp. + Met. Alkalosis | ↑↑ | ↓ | ↑ |
| Compensated (any) | normal | abnormal | abnormal |

---

## Requirements

- Python 3.8+
- No external dependencies

---

## License

MIT
