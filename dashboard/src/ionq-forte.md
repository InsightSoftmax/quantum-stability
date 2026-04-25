---
title: IonQ Forte-1
---

```js
import {successTimeSeries, volatilityTimeSeries, boxByLength, successByLength, successByInput, successSurface3D} from "./components/platformCharts.js";
const data = await FileAttachment("data/ionq-forte.json").json();
```

# IonQ Forte-1

Trapped-ion QPU accessed via the IonQ REST API. Historical data from May–June 2025. Runs are currently paused.

<div style="display: flex; gap: 2rem; margin: 1rem 0;">
  <div class="platform-card" style="flex: 1">
    <div class="metric">${(data.runs.reduce((s, d) => s + d.mean_success, 0) / data.runs.length * 100).toFixed(1)}%</div>
    <div class="metric-label">Historical mean</div>
  </div>
  <div class="platform-card" style="flex: 1">
    <div class="metric">${data.runs.length}</div>
    <div class="metric-label">Runs (2025)</div>
  </div>
  <div class="platform-card" style="flex: 1">
    <div class="metric">${data.circuits.length}</div>
    <div class="metric-label">Total circuits</div>
  </div>
</div>

## Consistency over time

Within-run consistency score (1 - std dev) — the primary stability metric. Higher is more consistent. Faded line and dots are individual runs; bold line and larger dots are the 4-run rolling average.

```js
volatilityTimeSeries(data, {color: "#99979D"})
```

## Success probability over time

Success probability for a given circuit is the fraction of shots that produced the correct output — where "correct" is the deterministic, noise-free answer computed by classical simulation. Each point is the mean across the circuits sampled that run. The bold line is the 4-run rolling average; faded line and dots are individual runs. The shaded band shows ±1 standard deviation within the run.

```js
successTimeSeries(data, {color: "#99979D"})
```

## Performance breakdown

How success probability varies across circuit depth and input state, aggregated across all runs.

### Success probability by circuit depth and input state

<p style="margin-bottom:0">Each point is one (depth, input state) combination. Point size reflects how many circuits were run with that combination. Drag to rotate.</p>

```js
successSurface3D(data, {color: "#99979D"})
```

### Distribution by circuit depth

```js
boxByLength(data, {color: "#99979D"})
```

### Mean success by circuit depth

Mean success probability for each depth, averaged across all runs. A declining trend confirms that noise accumulates as circuit depth increases.

```js
successByLength(data, {color: "#99979D"})
```

### Mean success by input state

Does the initial qubit state affect results? Ideally it shouldn't — deviations suggest state-preparation or readout asymmetry.

```js
successByInput(data, {color: "#99979D"})
```

## All runs

```js
Inputs.table(data.runs.slice().reverse(), {
  select: false,
  columns: ["run_date", "mean_success", "std_success", "n_circuits"],
  header: {
    run_date: "Date",
    mean_success: "Mean success",
    std_success: "Std dev",
    n_circuits: "Circuits",
  },
  format: {
    mean_success: d => `${(d * 100).toFixed(1)}%`,
    std_success: d => `±${(d * 100).toFixed(1)}%`,
  },
})
```
