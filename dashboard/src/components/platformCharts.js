import * as Plot from "npm:@observablehq/plot";

const DOMAIN_FLOOR = 0.7;

const INCIDENT_COLOR = {
  platform_offline:   "#E53E3E",
  automation_error:   "#DD6B20",
  planned_transition: "#718096",
  queue_timeout:      "#805AD5",
};

function incidentRules(incidents) {
  if (!incidents?.length) return [];
  return [Plot.ruleX(incidents, {
    x: d => new Date(d.incident_date),
    stroke: d => INCIDENT_COLOR[d.type] ?? "#718096",
    strokeWidth: 1.5,
    strokeDasharray: "4,3",
    tip: true,
    title: d => [
      d.incident_date,
      d.type.replace(/_/g, " "),
      d.notes || d.error_message || "",
    ].filter(Boolean).join("\n"),
  })];
}

// 4-run trailing rolling mean of a numeric field across an already-sorted array.
function addRollingMean(runs, fields, k = 4) {
  return runs.map((d, i) => {
    const slice = runs.slice(Math.max(0, i - k + 1), i + 1);
    const means = Object.fromEntries(
      fields.map(f => [
        `ma_${f}`,
        slice.reduce((s, r) => s + r[f], 0) / slice.length,
      ])
    );
    return {...d, ...means};
  });
}

/**
 * Time series of weekly mean success probability with ±1σ band.
 * Faded line/dots = individual runs; bold line/dots = 4-run rolling average.
 */
export function successTimeSeries(data, {color = "#363D47", width = 900, incidents = data.incidents} = {}) {
  const allRuns = data.runs.map(d => ({...d, date: new Date(d.run_date)}));
  const maRuns  = addRollingMean(allRuns, ["mean_success"]);
  const yMin    = Math.max(DOMAIN_FLOOR, Math.min(...allRuns.map(d => d.mean_success)) - 0.05);

  return Plot.plot({
    width,
    height: 300,
    marginLeft: 55,
    y: {
      domain: [yMin, 1.02],
      label: "Mean success probability",
      tickFormat: d => `${(d * 100).toFixed(0)}%`,
    },
    x: {type: "utc", label: null},
    marks: [
      Plot.ruleY([1], {stroke: "#e2e8f0", strokeDasharray: "4,4"}),
      Plot.areaY(allRuns, {
        x: "date",
        y1: d => Math.max(yMin, d.mean_success - d.std_success),
        y2: d => Math.min(1, d.mean_success + d.std_success),
        fill: color, fillOpacity: 0.08,
      }),
      Plot.line(allRuns, {
        x: "date", y: "mean_success",
        stroke: color, strokeWidth: 1, strokeOpacity: 0.3, curve: "monotone-x",
      }),
      Plot.dot(allRuns, {
        x: "date", y: "mean_success",
        fill: color, r: 2, fillOpacity: 0.3,
      }),
      Plot.line(maRuns, {
        x: "date", y: "ma_mean_success",
        stroke: color, strokeWidth: 2.5, curve: "monotone-x",
      }),
      Plot.dot(maRuns, {
        x: "date", y: "ma_mean_success",
        fill: color, r: 3.5, tip: true,
        title: d => `${d.run_date}\nThis run: ${(d.mean_success * 100).toFixed(1)}% ± ${(d.std_success * 100).toFixed(1)}%\n4-run avg: ${(d.ma_mean_success * 100).toFixed(1)}%\n${d.n_circuits} circuits`,
      }),
      ...incidentRules(incidents),
    ],
  });
}

/**
 * Consistency over time — (1 - within-run std dev), higher is more consistent.
 * Faded line/dots = individual runs; bold line/dots = 4-run rolling average.
 */
export function volatilityTimeSeries(data, {color = "#363D47", width = 900, incidents = data.incidents} = {}) {
  const allRuns = data.runs.map(d => ({
    ...d,
    date: new Date(d.run_date),
    consistency: 1 - d.std_success,
  }));
  const maRuns = addRollingMean(allRuns, ["consistency"]);

  return Plot.plot({
    width,
    height: 220,
    marginLeft: 55,
    y: {
      label: "Consistency score",
      tickFormat: d => `${(d * 100).toFixed(0)}%`,
    },
    x: {type: "utc", label: null},
    marks: [
      Plot.line(allRuns, {
        x: "date", y: "consistency",
        stroke: color, strokeWidth: 1, strokeOpacity: 0.3, curve: "monotone-x",
      }),
      Plot.dot(allRuns, {
        x: "date", y: "consistency",
        fill: color, r: 2, fillOpacity: 0.3,
      }),
      Plot.line(maRuns, {
        x: "date", y: "ma_consistency",
        stroke: color, strokeWidth: 2.5, curve: "monotone-x",
      }),
      Plot.dot(maRuns, {
        x: "date", y: "ma_consistency",
        fill: color, r: 3.5, tip: true,
        title: d => `${d.run_date}\nThis run: ${(d.consistency * 100).toFixed(1)}%\n4-run avg: ${(d.ma_consistency * 100).toFixed(1)}%`,
      }),
      ...incidentRules(incidents),
    ],
  });
}

/**
 * Box plot of success probability by circuit depth.
 * Shows distribution shape (median, IQR, whiskers, outliers) — richer than bar chart.
 *
 * Reading the chart:
 *   - Vertical line  = full range of non-outlier values (whisker: min to max)
 *   - Colored box    = interquartile range (Q1–Q3, middle 50% of circuits)
 *   - Center tick    = median
 *   - Dots below box = outliers (circuits that fell more than 1.5×IQR below Q1)
 */
export function boxByLength(data, {color = "#363D47", width = 560} = {}) {
  // Precompute per-depth stats for tooltips
  const statsByDepth = new Map();
  for (const d of data.circuits) {
    if (!statsByDepth.has(d.circuit_length)) statsByDepth.set(d.circuit_length, []);
    statsByDepth.get(d.circuit_length).push(d.success_probability);
  }
  const pct = (arr, q) => {
    const sorted = [...arr].sort((a, b) => a - b);
    const idx = q * (sorted.length - 1);
    const lo = Math.floor(idx), hi = Math.ceil(idx);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
  };
  const tipData = [...statsByDepth.entries()].map(([length, vals]) => {
    const q1 = pct(vals, 0.25), q3 = pct(vals, 0.75);
    const iqr = q3 - q1;
    const sorted = [...vals].sort((a, b) => a - b);
    // Whisker = range of non-outlier data (within 1.5×IQR of Q1/Q3)
    const whiskerLo = sorted.find(v => v >= q1 - 1.5 * iqr) ?? sorted[0];
    const whiskerHi = [...sorted].reverse().find(v => v <= q3 + 1.5 * iqr) ?? sorted[sorted.length - 1];
    return {length, median: pct(vals, 0.5), q1, q3, whiskerLo, whiskerHi, n: vals.length};
  });

  const chart = Plot.plot({
    width,
    height: 300,
    marginLeft: 55,
    marginBottom: 40,
    x: {label: "Circuit depth (# CNOTs)", tickFormat: d => `${d}`},
    y: {
      domain: [DOMAIN_FLOOR, 1.02],
      label: "Success probability",
      tickFormat: d => `${(d * 100).toFixed(0)}%`,
    },
    color: {range: [color]},
    marks: [
      Plot.ruleY([1], {stroke: "#e2e8f0", strokeDasharray: "4,4"}),
      Plot.boxY(data.circuits, {
        x: "circuit_length",
        y: "success_probability",
        fill: color,
        fillOpacity: 0.6,
        stroke: color,
        clip: "frame",
      }),
      // Invisible dots at median for tooltip
      Plot.dot(tipData, {
        x: "length",
        y: "median",
        r: 8,
        fillOpacity: 0,
        strokeOpacity: 0,
        tip: true,
        title: d =>
          `Depth ${d.length}  (${d.n} circuits)\n` +
          `Median   ${(d.median * 100).toFixed(1)}%\n` +
          `IQR      ${(d.q1 * 100).toFixed(1)}% – ${(d.q3 * 100).toFixed(1)}%\n` +
          `Whisker  ${(d.whiskerLo * 100).toFixed(1)}% – ${(d.whiskerHi * 100).toFixed(1)}%`,
      }),
    ],
  });

  const s = `font-size:0.72rem;color:#74737B;display:flex;gap:1.25rem;flex-wrap:wrap;margin-top:0.4rem;align-items:center`;
  const box = `display:inline-block;width:14px;height:10px;background:${color};opacity:0.6;border:1px solid ${color};vertical-align:middle;margin-right:4px`;
  const line = `display:inline-block;width:1px;height:14px;background:${color};vertical-align:middle;margin-right:6px`;
  const tick = `display:inline-block;width:10px;height:2px;background:${color};vertical-align:middle;margin-right:4px`;
  const dot = `display:inline-block;width:7px;height:7px;border-radius:50%;border:1.5px solid ${color};vertical-align:middle;margin-right:4px`;

  const legend = document.createElement("div");
  legend.style.cssText = s;
  legend.innerHTML =
    `<span><span style="${box}"></span>IQR (middle 50%)</span>` +
    `<span><span style="${line}"></span>Whisker (non-outlier range)</span>` +
    `<span><span style="${tick}"></span>Median</span>` +
    `<span><span style="${dot}"></span>Outlier</span>`;

  const container = document.createElement("div");
  container.appendChild(chart);
  container.appendChild(legend);
  return container;
}

/**
 * Bar chart of mean success probability by circuit depth.
 * Uses y1/y2 to anchor bars at the domain floor (avoids x-axis overlap).
 */
export function successByLength(data, {color = "#363D47", width = 560} = {}) {
  return Plot.plot({
    width,
    height: 260,
    marginLeft: 55,
    x: {label: "Circuit depth (# CNOTs)", tickFormat: d => `${d}`},
    y: {
      domain: [DOMAIN_FLOOR, 1.02],
      label: "Mean success probability",
      tickFormat: d => `${(d * 100).toFixed(0)}%`,
    },
    marks: [
      Plot.ruleY([1], {stroke: "#e2e8f0", strokeDasharray: "4,4"}),
      Plot.ruleY([DOMAIN_FLOOR], {stroke: "#ccc"}),
      Plot.barY(data.by_length, {
        x: "length",
        y1: DOMAIN_FLOOR,
        y2: "mean_success",
        fill: color,
        fillOpacity: 0.8,
        tip: true,
        title: d => `Depth ${d.length}\n${(d.mean_success * 100).toFixed(1)}% mean\n${d.n} circuits`,
      }),
    ],
  });
}

/**
 * Bar chart of mean success probability by input state.
 * Uses y1/y2 to anchor bars at the domain floor (avoids x-axis overlap).
 */
export function successByInput(data, {color = "#363D47", width = 400} = {}) {
  return Plot.plot({
    width,
    height: 260,
    marginLeft: 55,
    x: {label: "Input state", domain: ["00", "01", "10", "11"]},
    y: {
      domain: [DOMAIN_FLOOR, 1.02],
      label: "Mean success probability",
      tickFormat: d => `${(d * 100).toFixed(0)}%`,
    },
    marks: [
      Plot.ruleY([1], {stroke: "#e2e8f0", strokeDasharray: "4,4"}),
      Plot.ruleY([DOMAIN_FLOOR], {stroke: "#ccc"}),
      Plot.barY(data.by_input, {
        x: "input_bits",
        y1: DOMAIN_FLOOR,
        y2: "mean_success",
        fill: color,
        fillOpacity: 0.8,
        tip: true,
        title: d => `|${d.input_bits}⟩\n${(d.mean_success * 100).toFixed(1)}% mean\n${d.n} circuits`,
      }),
    ],
  });
}

/**
 * Rotatable 3D scatter — success probability as a function of circuit depth
 * and input state. Point size encodes circuit count. Uses Plotly.js.
 */
export async function successSurface3D(data, {height = 520, color = "#CC8A00"} = {}) {
  const Plotly = (await import("plotly.js-dist-min")).default;

  const lengths = [1, 2, 3, 4, 5, 6];
  const inputs = ["00", "01", "10", "11"];

  // Aggregate mean success and count by (circuit_length, input_bits) across all runs
  const sums = new Map();
  const counts = new Map();
  for (const d of data.circuits) {
    const key = `${d.circuit_length},${d.input_bits}`;
    sums.set(key, (sums.get(key) ?? 0) + d.success_probability);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  const xs = [], ys = [], zs = [], ns = [];
  for (const ib of inputs) {
    for (const l of lengths) {
      const key = `${l},${ib}`;
      const n = counts.get(key) ?? 0;
      if (n > 0) {
        xs.push(l);
        ys.push(ib);
        zs.push(sums.get(key) / n);
        ns.push(n);
      }
    }
  }

  const minN = Math.min(...ns);
  const maxN = Math.max(...ns);
  // Scale relative to actual min/max to maximise visible contrast
  const sizes = ns.map(n => 5 + ((n - minN) / (maxN - minN || 1)) * 23);

  const div = document.createElement("div");

  await Plotly.newPlot(div, [{
    type: "scatter3d",
    mode: "markers",
    x: xs,
    y: ys,
    z: zs,
    text: ns.map(String),
    marker: {
      size: sizes,
      color: zs,
      colorscale: [[0, "#cccccc"], [1, color]],
      cmin: 0.7,
      cmax: 1.0,
      colorbar: {
        title: {text: "Success probability"},
        tickformat: ".0%",
        len: 0.6,
      },
      line: {width: 0},
    },
    hovertemplate: "Depth %{x}<br>Input |%{y}⟩<br>Success %{z:.1%}<br>%{text} circuits<extra></extra>",
  }], {
    scene: {
      xaxis: {title: {text: "Depth (# CNOTs)"}, dtick: 1},
      yaxis: {title: {text: "Input state"}, type: "category", categoryorder: "array", categoryarray: ["00", "01", "10", "11"]},
      zaxis: {title: {text: "Success probability"}, range: [0.7, 1.0], tickformat: ".0%"},
      camera: {eye: {x: 1.6, y: -1.6, z: 0.8}},
    },
    margin: {l: 0, r: 0, b: 0, t: 0},
    height,
  }, {responsive: true, displayModeBar: false, scrollZoom: false});

  const clip = 80;
  const outer = document.createElement("div");
  outer.style.cssText = `overflow: hidden; height: ${height - clip}px;`;
  div.style.marginTop = `-${clip}px`;
  outer.appendChild(div);
  return outer;
}
