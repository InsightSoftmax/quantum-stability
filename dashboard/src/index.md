---
title: Overview
---

# Quantum Platform Stability

Weekly litmus-test circuits run on each platform. We track consistency over time — not a cross-platform ranking. Each platform is benchmarked only against its own prior runs.

```js
const summary = await FileAttachment("data/summary.json").json();
```

```js
// Platform cards
const statusLabel = {active: "Active", historical: "Paused", paused: "Paused"};
const statusClass = {active: "badge-active", historical: "badge-historical", paused: "badge-paused"};
const sortedSummary = [...summary].sort((a, b) => {
  const order = s => s === "active" ? 0 : 1;
  const so = order(a.status) - order(b.status);
  return so !== 0 ? so : a.platform.localeCompare(b.platform);
});
// Consistency score: (1 − avg within-run std dev) × 100%, 4-run rolling average
const consistencyScores = Object.fromEntries(
  summary.map(p => {
    const recent = p.sparkline.slice(-4);
    if (!recent.length) return [p.platform, null];
    const avgStd = recent.reduce((s, d) => s + d.std, 0) / recent.length;
    return [p.platform, (1 - avgStd) * 100];
  })
);
```

<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
${sortedSummary.map(p => html`
  <div class="platform-card">
    <div class="platform-name" style="display:flex;flex-direction:column;align-items:flex-start;gap:0.35rem">
      ${p.platform === "rigetti_cepheus" ? html`<a href="/rigetti-cepheus">Rigetti ${p.backend}</a>` :
        p.platform === "rigetti_ankaa"   ? html`<a href="/rigetti-ankaa">Rigetti ${p.backend}</a>` :
        p.platform === "aqt"             ? html`<a href="/aqt">AQT ${p.backend}</a>` :
        p.platform === "ibm"             ? html`<a href="/ibm">IBM ${p.backend}</a>` :
        p.platform === "ionq_forte"      ? html`<a href="/ionq-forte">IonQ ${p.backend}</a>` :
                                           html`<a href="/ionq">IonQ ${p.backend}</a>`}
      <span class="badge ${statusClass[p.status]}">${statusLabel[p.status]}</span>
    </div>
    ${consistencyScores[p.platform] != null ? html`
      <div class="metric">${consistencyScores[p.platform].toFixed(1)}%</div>
      <div class="metric-label">Consistency score</div>
      <div style="margin-top: 0.75rem; font-size: 0.85rem; color: var(--isc-muted)">
        ${p.n_runs} runs · ${p.n_circuits} circuits<br>last run ${p.latest_run}
      </div>
    ` : html`<div style="color: var(--isc-muted); font-size: 0.9rem">No data yet</div>`}
  </div>
`)}
</div>

## Consistency over time

Within-run consistency score (1 − std dev) per run — higher is more consistent. Bold line is the 4-run rolling average; faded dots are individual runs.

```js
const PLATFORM_LABEL = {
  aqt: "AQT IBEX", ibm: "IBM Brisbane",
  ionq: "IonQ Aria-1", ionq_forte: "IonQ Forte-1",
  rigetti_ankaa: "Rigetti Ankaa-3", rigetti_cepheus: "Rigetti Cepheus-1-108Q",
};
const PLATFORM_COLOR = {
  aqt: "#363D47", ibm: "#1192E8",
  ionq: "#74737B", ionq_forte: "#99979D",
  rigetti_ankaa: "#A07800", rigetti_cepheus: "#CC8A00",
};
const allRuns = summary.flatMap(p =>
  p.sparkline.map(d => ({...d, label: PLATFORM_LABEL[p.platform] ?? p.platform, date: new Date(d.date)}))
);
const colorDomain = Object.values(PLATFORM_LABEL);
const colorRange  = Object.values(PLATFORM_COLOR);

// 4-run rolling averages per platform
function rollingMean(vals, k) {
  return vals.map((_, i) => {
    const slice = vals.slice(Math.max(0, i - k + 1), i + 1);
    return slice.reduce((s, v) => s + v, 0) / slice.length;
  });
}
const byLabel = {};
allRuns.forEach(d => (byLabel[d.label] = byLabel[d.label] || []).push(d));
const maRuns = Object.values(byLabel).flatMap(runs => {
  const sorted = runs.slice().sort((a, b) => a.date - b.date);
  const maStd   = rollingMean(sorted.map(d => d.std),   4);
  const maValue = rollingMean(sorted.map(d => d.value), 4);
  return sorted.map((d, i) => ({...d, maStd: maStd[i], maValue: maValue[i]}));
});
```

```js
Plot.plot({
  width: 900,
  height: 220,
  marginLeft: 55,
  y: {label: "Consistency score", tickFormat: d => `${(d * 100).toFixed(0)}%`},
  x: {type: "utc", label: null},
  color: {domain: colorDomain, range: colorRange, legend: true},
  marks: [
    Plot.dot(allRuns, {
      x: "date", y: d => 1 - d.std, fill: "label",
      r: 2, fillOpacity: 0.2,
    }),
    Plot.line(maRuns, {
      x: "date", y: d => 1 - d.maStd, stroke: "label",
      strokeWidth: 2.5, curve: "monotone-x",
    }),
    Plot.dot(maRuns, {
      x: "date", y: d => 1 - d.maStd, fill: "label",
      r: 3.5, tip: true,
      title: d => `${d.label}\n${d.date.toLocaleDateString()}\n${((1 - d.maStd) * 100).toFixed(1)}% (4-run avg)`,
    }),
  ],
})
```

## Success probability over time

Bold line is the 4-run rolling average; faded dots are individual runs.

```js
Plot.plot({
  width: 900,
  height: 280,
  marginLeft: 55,
  y: {domain: [0.7, 1.02], label: "Mean success probability", tickFormat: d => `${(d*100).toFixed(0)}%`},
  x: {type: "utc", label: null},
  color: {domain: colorDomain, range: colorRange, legend: true},
  marks: [
    Plot.ruleY([1], {stroke: "#e2e8f0"}),
    Plot.dot(allRuns, {
      x: "date", y: "value", fill: "label",
      r: 2, fillOpacity: 0.2,
    }),
    Plot.line(maRuns, {
      x: "date", y: "maValue", stroke: "label",
      strokeWidth: 2.5, curve: "monotone-x",
    }),
    Plot.dot(maRuns, {
      x: "date", y: "maValue", fill: "label",
      r: 3.5, tip: true,
      title: d => `${d.label}\n${d.date.toLocaleDateString()}\n${(d.maValue * 100).toFixed(1)}% (4-run avg)`,
    }),
  ],
})
```

## Cost per benchmark run

10 circuits × 100 shots. Pricing as of April 2026.

```js
const PLATFORM_NAME = {
  aqt: "AQT IBEX (direct)", ibm: "IBM Brisbane",
  ionq: "IonQ Aria-1", ionq_forte: "IonQ Forte-1",
  rigetti_ankaa: "Rigetti Ankaa-3", rigetti_cepheus: "Rigetti Cepheus-1-108Q",
};
const ACCESS = {
  aqt: "qiskit-aqt-provider", ibm: "Qiskit Runtime (historical)",
  ionq: "AWS Braket (historical)", ionq_forte: "IonQ REST API (historical)",
  rigetti_ankaa: "AWS Braket (historical)", rigetti_cepheus: "AWS Braket",
};
const costRows = [
  ...summary.filter(p => p.cost_per_run_usd != null).map(p => ({
    platform: PLATFORM_NAME[p.platform] ?? p.platform,
    access: ACCESS[p.platform] ?? "—",
    status: p.status,
    cost_per_run: p.cost_per_run_usd,
    annual_52: p.cost_per_run_usd * 52,
  })),
  {platform: "AQT IBEX (via Braket)", access: "AWS Braket", status: "alternative",
   cost_per_run: 26.50, annual_52: 26.50 * 52},
];
const sortedCostRows = [...costRows].sort((a, b) => {
  const order = s => s === "active" ? 0 : 1;
  const so = order(a.status) - order(b.status);
  return so !== 0 ? so : a.platform.localeCompare(b.platform);
});
```

```js
Inputs.table(sortedCostRows, {
  select: false,
  columns: ["platform", "access", "status", "cost_per_run", "annual_52"],
  header: {platform: "Platform", access: "Access", status: "Status", cost_per_run: "Per run", annual_52: "Annual (52×)"},
  format: {
    status: d => html`<span class="badge ${d === "active" ? "badge-active" : "badge-historical"}">${d === "active" ? "Active" : "Paused"}</span>`,
    cost_per_run: d => `$${d.toFixed(2)}`,
    annual_52: d => `$${d.toFixed(0)}`,
  },
})
```

*AQT pricing from quotation Q2511001 (Nov 2025), converted at EUR/USD ≈ 1.09. IonQ figure is historical (Aria-1 at $0.03/shot); current Forte would be ~$83/run.*

---

*Benchmarks run weekly. Each run samples 10 circuits from a family of 24 (6 circuit depths × 4 input states), 100 shots each.*

<a href="/about" style="display:inline-block;margin-top:0.25rem;font-size:0.9rem;color:var(--isc-gold);font-weight:600;text-decoration:none;border-bottom:1.5px solid var(--isc-gold)">Learn more about the methodology →</a>
