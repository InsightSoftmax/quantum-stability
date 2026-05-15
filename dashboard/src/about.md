---
title: Methodology
---

# Methodology

## What we measure

The Quantum Stability Monitor tracks **longitudinal stability** of quantum computing platforms — not a cross-platform performance ranking. We run the same simple circuits on each platform every week and ask: *how consistent are the results over time?*

Each platform is analyzed only against its own prior runs. Drift, volatility, and predictability are the signals we care about.

## The circuit family

We use a family of **24 circuits**: 6 circuit depths (1–6 CNOT gates) × 4 input states (|00⟩, |01⟩, |10⟩, |11⟩).

Each circuit is an alternating CNOT sequence. Both qubits start in a computational basis state, then the circuit applies CNOTs that alternate which qubit is the control:

```
Gate 1: CNOT(q₀ → q₁)   [q₀ is control, q₁ is target]
Gate 2: CNOT(q₁ → q₀)   [q₁ is control, q₀ is target]
Gate 3: CNOT(q₀ → q₁)
Gate 4: CNOT(q₁ → q₀)
...
```

These are deliberately simple — no superposition, no measurement mid-circuit. The goal is a litmus test that any functioning QPU should handle cleanly, not a stress test of the hardware.

### Example: input |01⟩, depth 3

Starting state: q₀ = 0, q₁ = 1.

```
        Gate 1          Gate 2          Gate 3
      CNOT(0→1)       CNOT(1→0)       CNOT(0→1)

q₀:  |0⟩──── ● ──────── X ──────── ● ────  → 1
              │          │          │
q₁:  |1⟩──── X ──────── ● ──────── X ────  → 0
```

Stepping through the logic:

| After | q₀ | q₁ | Notes |
|---|---|---|---|
| Start | 0 | 1 | input |01⟩ |
| Gate 1 CNOT(0→1) | 0 | 1 | q₁ ← q₁ ⊕ q₀ = 1 ⊕ 0 = 1 (unchanged) |
| Gate 2 CNOT(1→0) | 1 | 1 | q₀ ← q₀ ⊕ q₁ = 0 ⊕ 1 = 1 |
| Gate 3 CNOT(0→1) | 1 | 0 | q₁ ← q₁ ⊕ q₀ = 1 ⊕ 1 = 0 |

**Reference output: |10⟩.** On a noise-free device, every shot of this circuit should produce `10`. Success probability = (shots returning `10`) / (total shots).

### Full reference table

```
         depth 1  depth 2  depth 3  depth 4  depth 5  depth 6
  |00⟩     00       00       00       00       00       00
  |01⟩     01       11       10       10       11       01
  |10⟩     11       01       01       11       10       10
  |11⟩     10       10       11       01       01       11
```

The |00⟩ input is a trivial fixed point — every CNOT leaves it unchanged. The other three inputs cycle through the remaining states before returning to the start at depth 6.

## Each weekly run

- **10 circuits** sampled from the 24, stratified so every depth appears at least once
- **100 shots** per circuit
- Results compared against the reference output to compute **success probability**

## Success probability

For each circuit execution:

```
success_probability = (shots matching reference output) / (total shots)
```

A perfect QPU would score 1.0 on every circuit. Real hardware scores lower due to gate errors, decoherence, readout errors, and crosstalk. The mean across the 10 circuits in a run is the primary metric reported on each platform page.

## Consistency score

The within-run consistency score is:

```
consistency = 1 − (standard deviation of success probabilities across the 10 circuits)
```

Higher is more consistent. The 4-run rolling average smooths week-to-week fluctuation. A platform that reliably scores 0.85 on every circuit has a higher consistency score than one that alternates between 0.95 and 0.75, even if the means are equal.

## What the charts show

- **Success over time**: each weekly run produces one data point — the mean success probability across the 10 sampled circuits, with ±1σ band
- **Consistency over time**: within-run standard deviation per week — a downward trend indicates growing variability
- **Distribution by circuit depth**: box plots (median, IQR, outliers) show how fidelity degrades with circuit complexity
- **Success probability by circuit depth and input state**: a 3D scatter aggregating all runs — each point is one (depth, input state) combination, dot size reflects how many circuits have been sampled at that combination. Lets you see whether certain input states perform worse at specific depths, which would point to a structured noise source rather than uniform degradation.
- **Mean success by circuit depth**: average success rate at each depth level
- **Mean success by input state**: ideally results should not depend on the input — deviations suggest state-preparation or readout asymmetry

## Data

All raw results are stored as CSV files committed to the [GitHub repository](https://github.com/InsightSoftmax/quantum-stability). One row per circuit execution, including the full shot histogram (`counts_json`), timestamps, and SDK version.

This project is maintained by [Insight Softmax](https://insightsoftmax.com/).
