"""
Author: Abdallah Elsokary
ABG Interpreter - Arterial Blood Gas Analysis
==============================================
A step-by-step interpreter for Arterial Blood Gas results.

Normal Reference Ranges:
  pH    : 7.35 - 7.45
  PaCO2 : 35   - 45  mmHg
  HCO3  : 22   - 26  mEq/L
  PaO2  : 80   - 100 mmHg  (on room air)

Compensation Formulas Used:
  Metabolic Acidosis   → Winter's formula : Expected PaCO2 = 1.5 × HCO3 + 8  (±2)
  Metabolic Alkalosis  →                  : Expected PaCO2 = 0.7 × HCO3 + 21 (±2)
  Respiratory Acidosis → Acute            : Expected HCO3  = 24 + 0.1  × ΔPCO2
                       → Chronic          : Expected HCO3  = 24 + 0.35 × ΔPCO2
  Respiratory Alkalosis→ Acute            : Expected HCO3  = 24 - 0.2  × ΔPCO2
                       → Chronic          : Expected HCO3  = 24 - 0.5  × ΔPCO2

A-a Gradient Formula:
  PAO2         = FiO2 × (760 - 47) - PaCO2 / 0.8
  A-a gradient = PAO2 - PaO2
  Normal A-a   = (age / 4) + 4   →  ~10 mmHg for a young adult on room air

Examples (solved manually):
  ── Example 1: Metabolic Acidosis ──────────────────────────────────────────
  pH=7.28, PaCO2=28, HCO3=13
    Step 1 → pH < 7.35               → Acidemia
    Step 2 → HCO3 low, CO2 normal    → Metabolic Acidosis (primary)
    Step 3 → Winter: 1.5×13 + 8 = 27.5 ±2  → range 25.5–29.5
             PaCO2=28 is inside range → Appropriate respiratory compensation ✓

  ── Example 2: Acute Respiratory Acidosis ──────────────────────────────────
  pH=7.20, PaCO2=65, HCO3=25
    Step 1 → pH < 7.35               → Acidemia
    Step 2 → CO2 high                → Respiratory Acidosis (primary)
    Step 3 → delta_CO2 = 65-40 = 25
             Acute   HCO3 = 24 + 0.1  × 25 = 26.5
             Chronic HCO3 = 24 + 0.35 × 25 = 32.8
             Actual HCO3=25 ≈ 26.5   → Acute compensation ✓

  ── Example 3: Metabolic Alkalosis ─────────────────────────────────────────
  pH=7.52, PaCO2=48, HCO3=38
    Step 1 → pH > 7.45               → Alkalemia
    Step 2 → HCO3 high               → Metabolic Alkalosis (primary)
    Step 3 → 0.7×38 + 21 = 47.6 ±2  → range 45.6–49.6
             PaCO2=48 is inside range → Appropriate respiratory compensation ✓

  ── Example 4: Acute Respiratory Alkalosis ─────────────────────────────────
  pH=7.50, PaCO2=28, HCO3=21
    Step 1 → pH > 7.45               → Alkalemia
    Step 2 → CO2 low                 → Respiratory Alkalosis (primary)
    Step 3 → delta_CO2 = 40-28 = 12
             Acute   HCO3 = 24 - 0.2  × 12 = 21.6
             Chronic HCO3 = 24 - 0.5  × 12 = 18
             Actual HCO3=21 ≈ 21.6   → Acute compensation ✓

  ── Example 5: A-a Gradient ────────────────────────────────────────────────
  PaO2=90, PaCO2=28, FiO2=0.21, age=40
    PAO2 = 0.21 × (760-47) - 28/0.8
         = 0.21 × 713 - 35
         = 149.7 - 35 = 114.7
    A-a  = 114.7 - 90 = 24.7 mmHg
    Normal for age 40 = 40/4 + 4 = 14
    24.7 > 14  →  Elevated A-a gradient ⚠  (V/Q mismatch / shunt / diffusion defect)
"""

from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# Data container
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ABGResult:
    """
    Holds the raw ABG values and all interpreted results.

    Raw inputs are set at creation time.
    Interpreted fields start empty and are filled by ABGInterpreter.interpret().

    Think of it as a result sheet:
      - You hand it in blank (raw values only).
      - The interpreter fills in the diagnosis fields.
      - You get back the completed sheet.
    """

    # ── Raw inputs ────────────────────────────────────────────────────────────
    pH: float
    PaCO2: float          # mmHg
    HCO3: float           # mEq/L
    PaO2: Optional[float] = None   # mmHg  (optional)
    FiO2: Optional[float] = None   # fraction 0–1, e.g. 0.21 = room air

    # ── Interpreted fields (filled by ABGInterpreter) ─────────────────────────
    primary_disorder: str = ""          # e.g. "Metabolic Acidosis"
    compensation: str = ""              # expected compensation formula + range
    compensation_adequacy: str = ""     # whether actual compensation matches expected
    oxygenation_status: str = ""        # Normal / Mild / Moderate / Severe hypoxemia
    aa_gradient: Optional[float] = None # calculated A-a gradient value
    aa_gradient_interpretation: str = ""# normal vs elevated + clinical meaning
    summary: str = ""                   # final formatted report string
    steps: list = field(default_factory=list)  # step-by-step reasoning log
    # NOTE: field(default_factory=list) is used instead of steps: list = []
    # because a plain mutable default (=[]) is shared across ALL instances in
    # Python. default_factory creates a brand-new list for each object.


# ──────────────────────────────────────────────────────────────────────────────
# Interpreter
# ──────────────────────────────────────────────────────────────────────────────

class ABGInterpreter:
    """
    Interprets Arterial Blood Gas results step by step.

    Usage:
        interpreter = ABGInterpreter()
        result = interpreter.interpret(pH=7.28, PaCO2=28, HCO3=13, PaO2=90, age=40)
        interpreter.print_full_report(result)
        # or access individual fields:
        print(result.primary_disorder)
        print(result.compensation_adequacy)
    """

    # ── Normal reference ranges (class-level constants) ───────────────────────
    PH_NORMAL    = (7.35, 7.45)
    PACO2_NORMAL = (35,   45)     # mmHg
    HCO3_NORMAL  = (22,   26)     # mEq/L
    PAO2_NORMAL  = (80,   100)    # mmHg on room air

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def interpret(
        self,
        pH: float,
        PaCO2: float,
        HCO3: float,
        PaO2: Optional[float] = None,
        FiO2: float = 0.21,
        age: Optional[int] = None,
    ) -> ABGResult:
        """
        Run the full 4-step ABG interpretation and return a completed ABGResult.

        Parameters
        ----------
        pH    : arterial pH
        PaCO2 : arterial CO2 partial pressure (mmHg)
        HCO3  : serum bicarbonate (mEq/L)
        PaO2  : arterial O2 partial pressure (mmHg)  — optional
        FiO2  : fraction of inspired oxygen (0.21 = room air)
        age   : patient age in years — used to calculate normal A-a gradient
        """

        # Create a blank result sheet and an empty step log
        result = ABGResult(pH=pH, PaCO2=PaCO2, HCO3=HCO3, PaO2=PaO2, FiO2=FiO2)
        steps  = []

        # ── Step 1: Classify pH ───────────────────────────────────────────────
        # Determine whether the patient is acidemic, alkalemic, or normal.
        steps.append("[Step 1] Classify pH")
        if pH < self.PH_NORMAL[0]:
            ph_status = "acidemia"
            steps.append(f"  → pH = {pH}  ⟹  Acidemia  (< 7.35)")
        elif pH > self.PH_NORMAL[1]:
            ph_status = "alkalemia"
            steps.append(f"  → pH = {pH}  ⟹  Alkalemia  (> 7.45)")
        else:
            ph_status = "normal"
            steps.append(f"  → pH = {pH}  ⟹  Normal pH  (7.35 – 7.45)")

        # ── Step 2: Identify primary disorder ────────────────────────────────
        # Compare CO2 and HCO3 against normal ranges to find the culprit.
        steps.append("\n[Step 2] Identify primary disorder")
        primary_disorder, _ = self._get_primary_disorder(ph_status, PaCO2, HCO3, steps)
        result.primary_disorder = primary_disorder

        # ── Step 3: Check compensation ────────────────────────────────────────
        # Apply the appropriate compensation formula and see if the body's
        # response matches expectations.
        steps.append("\n[Step 3] Check expected compensation")
        compensation, adequacy = self._check_compensation(primary_disorder, PaCO2, HCO3, steps)
        result.compensation          = compensation
        result.compensation_adequacy = adequacy

        # ── Step 4: Assess oxygenation (only if PaO2 was provided) ───────────
        if PaO2 is not None:
            steps.append("\n[Step 4] Assess oxygenation")

            # 4a. Classify hypoxemia severity
            result.oxygenation_status = self._assess_oxygenation(PaO2, steps)

            # 4b. Calculate A-a gradient
            #     A high gradient means O2 reaches the alveoli but struggles
            #     to cross into the blood  (V/Q mismatch, shunt, diffusion defect).
            aa        = self._calc_aa_gradient(PaO2, PaCO2, FiO2)
            normal_aa = self._normal_aa_gradient(age)
            result.aa_gradient = round(aa, 1)

            if aa <= normal_aa:
                result.aa_gradient_interpretation = (
                    f"A-a gradient = {aa:.1f} mmHg  ✓ Normal (≤ {normal_aa:.0f})"
                )
            else:
                result.aa_gradient_interpretation = (
                    f"A-a gradient = {aa:.1f} mmHg  ⚠ Elevated (> {normal_aa:.0f})  "
                    "→ suggests V/Q mismatch, shunt, or diffusion defect"
                )
            steps.append(f"  → {result.aa_gradient_interpretation}")

        # ── Step 5: Build summary ─────────────────────────────────────────────
        result.steps   = steps
        result.summary = self._build_summary(result)
        return result

    def print_full_report(self, result: ABGResult) -> None:
        """Print the full step-by-step report to stdout."""
        print("\n" + "═" * 55)
        print("  ABG INTERPRETATION")
        print("═" * 55)
        for step in result.steps:
            print(step)
        print()
        print(result.summary)

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers  (prefixed with _ by convention = internal use only)
    # ──────────────────────────────────────────────────────────────────────────

    def _get_primary_disorder(
        self, ph_status: str, PaCO2: float, HCO3: float, steps: list
    ):
        """
        Identify the primary acid-base disorder by comparing CO2 and HCO3
        against their normal ranges, guided by the pH direction.

        Returns (disorder_name, compensation_type)
        """

        # Boolean flags — easier to read than repeated comparisons below
        co2_high  = PaCO2 > self.PACO2_NORMAL[1]   # CO2 > 45
        co2_low   = PaCO2 < self.PACO2_NORMAL[0]   # CO2 < 35
        hco3_high = HCO3  > self.HCO3_NORMAL[1]    # HCO3 > 26
        hco3_low  = HCO3  < self.HCO3_NORMAL[0]    # HCO3 < 22

        if ph_status == "acidemia":
            if co2_high and not hco3_high:
                # CO2 is the culprit → respiratory problem
                steps.append("  → PaCO2 high + Acidemia  ⟹  Respiratory Acidosis (primary)")
                return "Respiratory Acidosis", "metabolic"
            elif hco3_low and not co2_high:
                # HCO3 is the culprit → metabolic problem
                steps.append("  → HCO3 low + Acidemia  ⟹  Metabolic Acidosis (primary)")
                return "Metabolic Acidosis", "respiratory"
            elif co2_high and hco3_low:
                # Both are abnormal in the same direction → mixed disorder
                steps.append("  → PaCO2 high + HCO3 low  ⟹  Mixed Respiratory & Metabolic Acidosis")
                return "Mixed Respiratory & Metabolic Acidosis", "none"
            else:
                steps.append("  → Acidemia with no clear CO2/HCO3 change — review values")
                return "Acidemia (unspecified)", "none"

        elif ph_status == "alkalemia":
            if co2_low and not hco3_low:
                steps.append("  → PaCO2 low + Alkalemia  ⟹  Respiratory Alkalosis (primary)")
                return "Respiratory Alkalosis", "metabolic"
            elif hco3_high and not co2_low:
                steps.append("  → HCO3 high + Alkalemia  ⟹  Metabolic Alkalosis (primary)")
                return "Metabolic Alkalosis", "respiratory"
            elif co2_low and hco3_high:
                steps.append("  → PaCO2 low + HCO3 high  ⟹  Mixed Respiratory & Metabolic Alkalosis")
                return "Mixed Respiratory & Metabolic Alkalosis", "none"
            else:
                steps.append("  → Alkalemia with no clear CO2/HCO3 change — review values")
                return "Alkalemia (unspecified)", "none"

        else:  # normal pH
            # A normal pH with abnormal CO2 and HCO3 means full compensation
            # or a mixed disorder that happens to cancel out.
            if co2_high and hco3_high:
                steps.append("  → Normal pH + CO2 high + HCO3 high  ⟹  Compensated Respiratory Acidosis (or Mixed)")
                return "Compensated Respiratory Acidosis (or Mixed Resp. Acidosis + Met. Alkalosis)", "none"
            elif co2_low and hco3_low:
                steps.append("  → Normal pH + CO2 low + HCO3 low  ⟹  Compensated Respiratory Alkalosis (or Mixed)")
                return "Compensated Respiratory Alkalosis (or Mixed Resp. Alkalosis + Met. Acidosis)", "none"
            else:
                steps.append("  → All values within normal range  ⟹  Normal ABG")
                return "Normal ABG", "none"

    def _check_compensation(
        self, disorder: str, PaCO2: float, HCO3: float, steps: list
    ):
        """
        Apply the classic compensation formulas and compare with actual values.

        Each formula answers: "Given the primary disorder, what should the
        compensating parameter be?"  If the actual value matches → appropriate
        compensation.  If it doesn't → suspect a second concurrent disorder.
        """

        adequacy     = ""
        compensation = ""

        # ── Metabolic Acidosis → Respiratory compensation ─────────────────────
        # The body hyperventilates to blow off CO2 and raise pH.
        # Winter's formula predicts how far CO2 should drop.
        #
        # Formula : Expected PaCO2 = 1.5 × HCO3 + 8  (±2)
        # Example : HCO3=13  →  1.5×13 + 8 = 27.5  →  range 25.5–29.5
        if disorder == "Metabolic Acidosis":
            expected_co2 = 1.5 * HCO3 + 8
            low  = expected_co2 - 2
            high = expected_co2 + 2
            compensation = (
                f"Expected respiratory compensation (Winter's formula): "
                f"PaCO2 = 1.5 × {HCO3} + 8 = {expected_co2:.1f} ±2  "
                f"→  range {low:.1f} – {high:.1f} mmHg"
            )
            steps.append(f"  → {compensation}")

            if low <= PaCO2 <= high:
                adequacy = "✓ Respiratory compensation is appropriate"
            elif PaCO2 < low:
                adequacy = "⚠ Over-compensation → possible concurrent Respiratory Alkalosis"
            else:
                adequacy = "⚠ Under-compensation → possible concurrent Respiratory Acidosis"

        # ── Metabolic Alkalosis → Respiratory compensation ────────────────────
        # The body hypoventilates to retain CO2 and lower pH.
        #
        # Formula : Expected PaCO2 = 0.7 × HCO3 + 21  (±2)
        # Example : HCO3=38  →  0.7×38 + 21 = 47.6  →  range 45.6–49.6
        elif disorder == "Metabolic Alkalosis":
            expected_co2 = 0.7 * HCO3 + 21
            low  = expected_co2 - 2
            high = expected_co2 + 2
            compensation = (
                f"Expected respiratory compensation: "
                f"PaCO2 = 0.7 × {HCO3} + 21 = {expected_co2:.1f} ±2  "
                f"→  range {low:.1f} – {high:.1f} mmHg"
            )
            steps.append(f"  → {compensation}")

            if low <= PaCO2 <= high:
                adequacy = "✓ Respiratory compensation is appropriate"
            elif PaCO2 > high:
                adequacy = "⚠ Under-compensation → possible concurrent Respiratory Acidosis"
            else:
                adequacy = "⚠ Over-compensation → possible concurrent Respiratory Alkalosis"

        # ── Respiratory Acidosis → Metabolic compensation ─────────────────────
        # The kidneys retain HCO3 to buffer the excess acid.
        # Kidneys take days, so we distinguish Acute vs Chronic.
        #
        # Acute   (hours): ΔHCO3 = 0.1  × ΔCO2   (kidneys haven't kicked in yet)
        # Chronic (days) : ΔHCO3 = 0.35 × ΔCO2   (kidneys fully compensating)
        #
        # Example: PaCO2=65  →  delta=25
        #   Acute   HCO3 = 24 + 0.1  × 25 = 26.5
        #   Chronic HCO3 = 24 + 0.35 × 25 = 32.8
        elif disorder == "Respiratory Acidosis":
            delta_co2    = PaCO2 - 40
            acute_hco3   = 24 + 0.1  * delta_co2
            chronic_hco3 = 24 + 0.35 * delta_co2
            compensation = (
                f"Expected metabolic compensation  (ΔPCO2 = {PaCO2} - 40 = {delta_co2:.0f}):\n"
                f"    Acute   → HCO3 = 24 + 0.1  × {delta_co2:.0f} = {acute_hco3:.1f} mEq/L\n"
                f"    Chronic → HCO3 = 24 + 0.35 × {delta_co2:.0f} = {chronic_hco3:.1f} mEq/L"
            )
            steps.append(f"  → {compensation}")

            if abs(HCO3 - acute_hco3) < 2:
                adequacy = "✓ Compensation matches Acute pattern"
            elif abs(HCO3 - chronic_hco3) < 3:
                adequacy = "✓ Compensation matches Chronic pattern"
            elif HCO3 > chronic_hco3 + 3:
                adequacy = "⚠ HCO3 higher than expected → possible concurrent Metabolic Alkalosis"
            elif HCO3 < acute_hco3 - 2:
                adequacy = "⚠ HCO3 lower than expected → possible concurrent Metabolic Acidosis"
            else:
                adequacy = "Compensation is within acceptable range"

        # ── Respiratory Alkalosis → Metabolic compensation ────────────────────
        # The kidneys excrete HCO3 to lower pH back toward normal.
        #
        # Acute   : ΔHCO3 = 0.2  × ΔCO2
        # Chronic : ΔHCO3 = 0.5  × ΔCO2
        #
        # Example: PaCO2=28  →  delta=12
        #   Acute   HCO3 = 24 - 0.2  × 12 = 21.6
        #   Chronic HCO3 = 24 - 0.5  × 12 = 18
        elif disorder == "Respiratory Alkalosis":
            delta_co2    = 40 - PaCO2
            acute_hco3   = 24 - 0.2  * delta_co2
            chronic_hco3 = 24 - 0.5  * delta_co2
            compensation = (
                f"Expected metabolic compensation  (ΔPCO2 = 40 - {PaCO2} = {delta_co2:.0f}):\n"
                f"    Acute   → HCO3 = 24 - 0.2  × {delta_co2:.0f} = {acute_hco3:.1f} mEq/L\n"
                f"    Chronic → HCO3 = 24 - 0.5  × {delta_co2:.0f} = {chronic_hco3:.1f} mEq/L"
            )
            steps.append(f"  → {compensation}")

            if abs(HCO3 - acute_hco3) < 2:
                adequacy = "✓ Compensation matches Acute pattern"
            elif abs(HCO3 - chronic_hco3) < 3:
                adequacy = "✓ Compensation matches Chronic pattern"
            elif HCO3 < chronic_hco3 - 3:
                adequacy = "⚠ HCO3 lower than expected → possible concurrent Metabolic Acidosis"
            elif HCO3 > acute_hco3 + 2:
                adequacy = "⚠ HCO3 higher than expected → possible concurrent Metabolic Alkalosis"
            else:
                adequacy = "Compensation is within acceptable range"

        else:
            # Mixed disorders or Normal ABG — no single compensation formula applies
            compensation = "No single compensation formula applies (mixed or normal ABG)"
            adequacy     = ""
            steps.append(f"  → {compensation}")

        if adequacy:
            steps.append(f"  → {adequacy}")

        return compensation, adequacy

    def _assess_oxygenation(self, PaO2: float, steps: list) -> str:
        """
        Classify hypoxemia severity based on PaO2 on room air.

        Normal  : PaO2 ≥ 80 mmHg
        Mild    : 60 – 79 mmHg
        Moderate: 40 – 59 mmHg
        Severe  : < 40 mmHg
        """
        if PaO2 >= 80:
            status = f"PaO2 = {PaO2} mmHg  ✓ Normal oxygenation"
        elif PaO2 >= 60:
            status = f"PaO2 = {PaO2} mmHg  ⚠ Mild Hypoxemia"
        elif PaO2 >= 40:
            status = f"PaO2 = {PaO2} mmHg  ⚠⚠ Moderate Hypoxemia"
        else:
            status = f"PaO2 = {PaO2} mmHg  🔴 Severe Hypoxemia"
        steps.append(f"  → {status}")
        return status

    def _calc_aa_gradient(self, PaO2: float, PaCO2: float, FiO2: float) -> float:
        """
        Calculate the Alveolar-arterial (A-a) oxygen gradient.

        Formula:
            PAO2         = FiO2 × (Patm - PH2O) - PaCO2 / RQ
                         = FiO2 × (760  - 47)   - PaCO2 / 0.8
            A-a gradient = PAO2 - PaO2

        Constants:
            760 mmHg = atmospheric pressure at sea level
            47  mmHg = water vapour pressure in the alveoli at 37°C
            0.8      = respiratory quotient (RQ) — ratio of CO2 produced to O2 consumed

        A high A-a gradient means O2 successfully enters the alveoli but
        fails to cross into the blood, indicating:
            • V/Q mismatch  (e.g. PE, pneumonia)
            • Shunt         (e.g. ASD, hepatopulmonary syndrome)
            • Diffusion defect (e.g. pulmonary fibrosis)
        """
        PAO2 = FiO2 * (760 - 47) - PaCO2 / 0.8
        return PAO2 - PaO2

    def _normal_aa_gradient(self, age: Optional[int]) -> float:
        """
        Return the expected normal A-a gradient for the patient's age.

        Formula : Normal A-a = (age / 4) + 4
        Example : age 40  →  40/4 + 4 = 14 mmHg
        Example : age 60  →  60/4 + 4 = 19 mmHg

        If age is not provided, returns 10 mmHg (typical young adult value).
        """
        if age:
            return age / 4 + 4
        return 10

    def _build_summary(self, r: ABGResult) -> str:
        """
        Assemble a formatted summary string from the completed ABGResult.
        Uses str.join() on a list of lines to avoid repeated string concatenation.
        """
        lines = [
            "═" * 55,
            "  ABG INTERPRETATION SUMMARY",
            "═" * 55,
            f"  pH      : {r.pH}",
            f"  PaCO2   : {r.PaCO2} mmHg",
            f"  HCO3    : {r.HCO3} mEq/L",
        ]
        if r.PaO2 is not None:
            lines.append(f"  PaO2    : {r.PaO2} mmHg")
        lines += [
            "─" * 55,
            f"  Primary disorder : {r.primary_disorder}",
            f"  Compensation     : {r.compensation_adequacy or r.compensation}",
        ]
        if r.oxygenation_status:
            lines.append(f"  Oxygenation      : {r.oxygenation_status}")
        if r.aa_gradient is not None:
            lines.append(f"  A-a Gradient     : {r.aa_gradient_interpretation}")
        lines.append("═" * 55)
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Demo — run with:  python abg_interpreter.py
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    interpreter = ABGInterpreter()

    cases = [
        {
            "label"  : "Example 1 — Metabolic Acidosis with respiratory compensation",
            "pH"     : 7.28, "PaCO2": 28,  "HCO3": 13,
            "PaO2"   : 90,   "FiO2" : 0.21, "age": 40,
        },
        {
            "label"  : "Example 2 — Acute Respiratory Acidosis",
            "pH"     : 7.20, "PaCO2": 65,  "HCO3": 25,
            "PaO2"   : 55,   "FiO2" : 0.21, "age": 60,
        },
        {
            "label"  : "Example 3 — Metabolic Alkalosis",
            "pH"     : 7.52, "PaCO2": 48,  "HCO3": 38,
            "PaO2"   : 88,   "FiO2" : 0.21, "age": 35,
        },
        {
            "label"  : "Example 4 — Acute Respiratory Alkalosis",
            "pH"     : 7.50, "PaCO2": 28,  "HCO3": 21,
            "PaO2"   : 95,   "FiO2" : 0.21,
        },
        {
            "label"  : "Example 5 — Normal ABG",
            "pH"     : 7.40, "PaCO2": 40,  "HCO3": 24,
            "PaO2"   : 95,   "FiO2" : 0.21,
        },
    ]

    for case in cases:
        print(f"\n{'#' * 60}")
        print(f"  {case['label']}")
        print(f"{'#' * 60}")
        result = interpreter.interpret(
            pH    = case["pH"],
            PaCO2 = case["PaCO2"],
            HCO3  = case["HCO3"],
            PaO2  = case.get("PaO2"),
            FiO2  = case.get("FiO2", 0.21),
            age   = case.get("age"),
        )
        interpreter.print_full_report(result)
