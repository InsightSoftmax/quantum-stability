---
title: AQT IBEX (Braket)
---

```js
import {successTimeSeries, volatilityTimeSeries, boxByLength, successByLength, successByInput, successSurface3D} from "./components/platformCharts.js";
const data = await FileAttachment("data/aqt-braket.json").json();
```

# AQT IBEX (Braket)

AQT trapped-ion QPU accessed via AWS Braket (eu-west-2). Weekly runs on Tuesdays, offset from the [direct API path](/aqt) by 30 minutes. At ~$26.50/run this offers a cost comparison point against AQT direct (~$25.07/run).

<div style="display: flex; gap: 2rem; margin: 1rem 0;">
  <div class="platform-card" style="flex: 1">
    <div class="metric">${data.runs.length > 0 ? (data.runs.at(-1)?.mean_success * 100).toFixed(1) + "%" : "—"}</div>
    <div class="metric-label">Latest run success rate</div>
  </div>
  <div class="platform-card" style="flex: 1">
    <div class="metric">${data.runs.length > 0 ? (data.runs.reduce((s, d) => s + d.mean_success, 0) / data.runs.length * 100).toFixed(1) + "%" : "—"}</div>
    <div class="metric-label">All-time mean</div>
  </div>
  <div class="platform-card" style="flex: 1">
    <div class="metric">${data.runs.length}</div>
    <div class="metric-label">Runs</div>
  </div>
  <div class="platform-card" style="flex: 1">
    <div class="metric">${data.circuits.length}</div>
    <div class="metric-label">Total circuits</div>
  </div>
</div>

${data.runs.length === 0 ? html`<div style="color: var(--isc-muted); font-style: italic; margin: 2rem 0;">No data yet — first automated run scheduled for the next Tuesday.</div>` : ""}

## Consistency over time

Within-run consistency score (1 - std dev) — the primary stability metric. Higher is more consistent. Faded line and dots are individual runs; bold line and larger dots are the 4-run rolling average.

```js
volatilityTimeSeries(data, {color: "#5B7FA3"})
```

## Success probability over time

Success probability for a given circuit is the fraction of shots that produced the correct output — where "correct" is the deterministic, noise-free answer computed by classical simulation. Each point is the mean across the circuits sampled that run. The bold line is the 4-run rolling average; faded line and dots are individual runs. The shaded band shows ±1 standard deviation within the run.

```js
successTimeSeries(data, {color: "#5B7FA3"})
```

## Performance breakdown

How success probability varies across circuit depth and input state, aggregated across all runs.

### Success probability by circuit depth and input state

<p style="margin-bottom:0">Each point is one (depth, input state) combination. Point size reflects how many circuits were run with that combination. Drag to rotate.</p>

```js
successSurface3D(data, {color: "#5B7FA3"})
```

### Distribution by circuit depth

```js
boxByLength(data, {color: "#5B7FA3"})
```

### Mean success by circuit depth

Mean success probability for each depth, averaged across all runs. A declining trend confirms that noise accumulates as circuit depth increases.

```js
successByLength(data, {color: "#5B7FA3"})
```

### Mean success by input state

Does the initial qubit state affect results? Ideally it shouldn't — deviations suggest state-preparation or readout asymmetry.

```js
successByInput(data, {color: "#5B7FA3"})
```

## Incidents

```js
data.incidents?.length > 0 ? Inputs.table([...data.incidents].reverse(), {
  select: false,
  columns: ["incident_date", "type", "notes", "error_message"],
  header: {incident_date: "Date", type: "Type", notes: "Notes", error_message: "Error"},
  width: {incident_date: 110, type: 160, notes: 220, error_message: 300},
  format: {
    type: d => {
      const colors = {platform_offline: "#E53E3E", automation_error: "#DD6B20", planned_transition: "#718096", queue_timeout: "#805AD5"};
      return html`<span style="color:${colors[d] ?? "#718096"};font-weight:600">${d.replace(/_/g, " ")}</span>`;
    },
  },
}) : html`<p style="color: var(--isc-muted); font-style: italic">No incidents recorded.</p>`
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
