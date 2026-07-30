export default {
  root: "src",
  base: "/quantum-stability/",
  cleanUrls: false,
  title: "Quantum Stability Monitor",
  pages: [
    {name: "Overview", path: "/"},
    {
      name: "Active Platforms",
      pages: [
        {name: "AQT IBEX", path: "/aqt"},
        {name: "AQT IBEX (Braket)", path: "/aqt-braket"},
        {name: "IBM Marrakesh", path: "/ibm-marrakesh"},
        {name: "IBM Pittsburgh", path: "/ibm-pittsburgh"},
        {name: "IQM Garnet", path: "/iqm"},
        {name: "IonQ Forte-1 (Braket)", path: "/ionq-forte-braket"},
        {name: "Rigetti Cepheus-1-108Q", path: "/rigetti-cepheus"},
      ]
    },
    {
      name: "Paused Platforms",
      pages: [
        {name: "IBM Brisbane", path: "/ibm-brisbane"},
        {name: "IonQ Aria-1", path: "/ionq"},
        {name: "IonQ Forte-1 (direct)", path: "/ionq-forte-direct"},
        {name: "Rigetti Ankaa-3", path: "/rigetti-ankaa"},
      ]
    },
    {name: "Methodology", path: "/about"},
    {name: "About Insight Softmax", path: "/about-isc"},
    {name: "Contact", path: "/contact"},
  ],
  head: '<link rel="stylesheet" href="theme.css"><link rel="icon" href="favicon.svg" type="image/svg+xml"><link rel="canonical" href="https://insightsoftmax.com/quantum-stability">',
  footer: 'Quantum Stability Monitor — longitudinal QPU benchmarking by <a href="https://insightsoftmax.com/" target="_blank" rel="noopener">Insight Softmax</a>',
};
