// Frontend Application Controller for CSET302 Automata Theory Simulator

const SAMPLE_AUTOMATA = {
  sample_01: {
    name: "Ends_With_01",
    displayName: "Ends with '01'",
    badge: "Binary NFA",
    desc: "Recognizes binary strings ending in '01'. Standard benchmark.",
    states: ["q0", "q1", "q2"],
    alphabet: ["0", "1"],
    start_state: "q0",
    final_states: ["q2"],
    transitions: [
      { from: "q0", symbol: "0", to: ["q0", "q1"] },
      { from: "q0", symbol: "1", to: ["q0"] },
      { from: "q1", symbol: "1", to: ["q2"] }
    ]
  },
  sample_02: {
    name: "Contains_00_or_11_Epsilon",
    displayName: "Contains '00' or '11'",
    badge: "ε-NFA",
    desc: "Uses ε-branches to check for consecutive 00 or 11.",
    states: ["q0", "q1", "q2", "q3", "q4", "q5", "q6"],
    alphabet: ["0", "1"],
    start_state: "q0",
    final_states: ["q6"],
    transitions: [
      { from: "q0", symbol: "ε", to: ["q1", "q3"] },
      { from: "q1", symbol: "0", to: ["q2"] },
      { from: "q2", symbol: "0", to: ["q6"] },
      { from: "q3", symbol: "1", to: ["q4"] },
      { from: "q4", symbol: "1", to: ["q6"] },
      { from: "q6", symbol: "0", to: ["q6"] },
      { from: "q6", symbol: "1", to: ["q6"] }
    ]
  },
  sample_03: {
    name: "Cyclic_Epsilon_NFA",
    displayName: "Cyclic ε-Loops",
    badge: "Cycle-Safe",
    desc: "A → B → C → A loop verifying termination of ε-closure BFS reachability.",
    states: ["A", "B", "C", "D"],
    alphabet: ["0", "1"],
    start_state: "A",
    final_states: ["D"],
    transitions: [
      { from: "A", symbol: "ε", to: ["B"] },
      { from: "B", symbol: "ε", to: ["C"] },
      { from: "C", symbol: "ε", to: ["A"] },
      { from: "B", symbol: "0", to: ["D"] },
      { from: "C", symbol: "1", to: ["D"] }
    ]
  },
  sample_04: {
    name: "Redundant_DFA_Minimization_Candidate",
    displayName: "Redundant States",
    badge: "Minimization",
    desc: "5-state machine that collapses into 4 minimal states via Table-Filling.",
    states: ["A", "B", "C", "D", "E"],
    alphabet: ["0", "1"],
    start_state: "A",
    final_states: ["C", "D"],
    transitions: [
      { from: "A", symbol: "0", to: ["B"] },
      { from: "A", symbol: "1", to: ["A"] },
      { from: "B", symbol: "0", to: ["C"] },
      { from: "B", symbol: "1", to: ["D"] },
      { from: "C", symbol: "0", to: ["E"] },
      { from: "C", symbol: "1", to: ["A"] },
      { from: "D", symbol: "0", to: ["E"] },
      { from: "D", symbol: "1", to: ["A"] },
      { from: "E", symbol: "0", to: ["E"] },
      { from: "E", symbol: "1", to: ["E"] }
    ]
  },
  sample_05: {
    name: "Binary_Divisible_By_3",
    displayName: "Divisible by 3",
    badge: "Arithmetic DFA",
    desc: "States track remainder modulo 3 (accepts 0, 11, 110, 1001, 1100...).",
    states: ["rem0", "rem1", "rem2"],
    alphabet: ["0", "1"],
    start_state: "rem0",
    final_states: ["rem0"],
    transitions: [
      { from: "rem0", symbol: "0", to: ["rem0"] },
      { from: "rem0", symbol: "1", to: ["rem1"] },
      { from: "rem1", symbol: "0", to: ["rem2"] },
      { from: "rem1", symbol: "1", to: ["rem0"] },
      { from: "rem2", symbol: "0", to: ["rem1"] },
      { from: "rem2", symbol: "1", to: ["rem2"] }
    ]
  },
  sample_06: {
    name: "Even_Zeros_and_Even_Ones",
    displayName: "Even 0s & Even 1s",
    badge: "Parity DFA",
    desc: "4 states tracking parity of zeros and ones (accepts ε, 00, 11, 0101...).",
    states: ["ee", "oe", "oo", "eo"],
    alphabet: ["0", "1"],
    start_state: "ee",
    final_states: ["ee"],
    transitions: [
      { from: "ee", symbol: "0", to: ["oe"] },
      { from: "ee", symbol: "1", to: ["eo"] },
      { from: "oe", symbol: "0", to: ["ee"] },
      { from: "oe", symbol: "1", to: ["oo"] },
      { from: "oo", symbol: "0", to: ["eo"] },
      { from: "oo", symbol: "1", to: ["oe"] },
      { from: "eo", symbol: "0", to: ["oo"] },
      { from: "eo", symbol: "1", to: ["ee"] }
    ]
  }
};

let currentConversionData = null;
let vizInstance = null;
let graphManager = null;
let simulatorPlayer = null;
let graphBuilder = null;
let currentActiveView = "nfa";

// Initialize Viz.js if available
if (typeof Viz !== "undefined") {
  vizInstance = new Viz();
}

document.addEventListener("DOMContentLoaded", () => {
  initGraphManager();
  initSimulatorPlayer();
  setupInputModes();
  setupTemplateCards();
  setupTabs();
  setupSampleSelector();
  setupButtons();
  setupExportButtons();
  setupCanvasControls();
  setupRegexConverter();
  setupRegexChips();
  setupTestStringGenerator();

  // Load sample 1 initially
  loadSample("sample_01");
  convertCurrentNFA();
});

function setupInputModes() {
  const modeButtons = document.querySelectorAll(".mode-tab-btn");
  modeButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      modeButtons.forEach(b => {
        b.classList.remove("active");
        b.setAttribute("aria-selected", "false");
      });
      document.querySelectorAll(".mode-panel").forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
      const mode = btn.getAttribute("data-mode");
      const targetPanel = document.getElementById(`mode-panel-${mode}`);
      if (targetPanel) {
        targetPanel.classList.add("active");
      }

      // If user switches to Draw mode, display the floating builder toolbar
      const builderToolbar = document.getElementById("builder-toolbar");
      if (builderToolbar) {
        builderToolbar.style.display = mode === "builder" ? "flex" : "none";
      }
    });
  });
}

function setupTemplateCards() {
  const cards = document.querySelectorAll(".template-card");
  cards.forEach(card => {
    card.addEventListener("click", async () => {
      cards.forEach(c => c.classList.remove("active"));
      card.classList.add("active");

      const sampleKey = card.getAttribute("data-sample");
      if (sampleKey && SAMPLE_AUTOMATA[sampleKey]) {
        loadSample(sampleKey);
        const sampleSelect = document.getElementById("sample-select");
        if (sampleSelect) {
          sampleSelect.value = sampleKey;
        }
        await convertCurrentNFA();
        showToast(`Loaded template: "${SAMPLE_AUTOMATA[sampleKey].displayName}"`, "info");
      }
    });
  });
}

function setupRegexChips() {
  const chips = document.querySelectorAll(".regex-chip");
  chips.forEach(chip => {
    chip.addEventListener("click", () => {
      const regexVal = chip.getAttribute("data-regex");
      const regexInput = document.getElementById("regex-input");
      if (regexInput && regexVal) {
        regexInput.value = regexVal;
        const buildBtn = document.getElementById("btn-convert-regex");
        if (buildBtn) buildBtn.click();
      }
    });
  });
}

function initGraphManager() {
  const container = document.getElementById("canvas") || document.getElementById("cy-container");
  if (!container) {
    console.warn("Canvas container element not found for GraphManager.");
    return;
  }
  if (typeof GraphManager !== "undefined") {
    try {
      graphManager = new GraphManager(container);
      graphManager.init();
      if (typeof window !== "undefined") {
        window.graphManager = graphManager;
      }
      if (simulatorPlayer && typeof simulatorPlayer.setGraphManager === "function") {
        simulatorPlayer.setGraphManager(graphManager);
      }

      // Initialize Milestone 5 Visual Graph Builder wrapping GraphManager
      if (typeof GraphBuilder !== "undefined") {
        try {
          graphBuilder = new GraphBuilder({
            graphManager: graphManager,
            jsonEditorId: "nfa-json",
            sampleSelectId: "sample-select"
          });
          graphBuilder.init();
          if (typeof window !== "undefined") {
            window.graphBuilder = graphBuilder;
          }
        } catch (builderErr) {
          console.error("Failed to initialize GraphBuilder:", builderErr);
        }
      }
    } catch (err) {
      console.error("Failed to initialize GraphManager:", err);
    }
  } else {
    console.info("GraphManager class not yet loaded.");
  }
}

function initSimulatorPlayer() {
  if (typeof SimulatorPlayer !== "undefined") {
    try {
      simulatorPlayer = new SimulatorPlayer({
        graphManager: graphManager
      });
      simulatorPlayer.init();
      if (typeof window !== "undefined") {
        window.simulatorPlayer = simulatorPlayer;
      }
    } catch (err) {
      console.error("Failed to initialize SimulatorPlayer:", err);
    }
  } else {
    console.info("SimulatorPlayer class not yet loaded.");
  }
}

function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetId = tab.getAttribute("data-tab");

      // Synchronize all tab buttons targeting this view
      document.querySelectorAll(`.tab[data-tab="${targetId}"]`).forEach(t => {
        t.classList.add("active");
        t.setAttribute("aria-selected", "true");
      });
      document.querySelectorAll(`.tab:not([data-tab="${targetId}"])`).forEach(t => {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
      });

      document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add("active");
      }

      // Synchronize interactive Cytoscape graph view
      syncGraphWithTab(targetId);
    });
  });
}

function syncGraphWithTab(tabId) {
  if (!graphManager || !currentConversionData) return;

  switch (tabId) {
    case "tab-nfa":
      currentActiveView = "nfa";
      if (currentConversionData.nfa) {
        graphManager.loadAutomaton(currentConversionData.nfa, "nfa");
      }
      break;
    case "tab-dfa":
      currentActiveView = "dfa";
      if (currentConversionData.converted_dfa) {
        graphManager.loadAutomaton(currentConversionData.converted_dfa, "dfa");
      }
      break;
    case "tab-minimal":
      currentActiveView = "minimal";
      if (currentConversionData.minimal_dfa) {
        graphManager.loadAutomaton(currentConversionData.minimal_dfa, "minimal");
      }
      break;
    case "tab-conversion":
      currentActiveView = "dfa";
      if (currentConversionData.converted_dfa) {
        graphManager.loadAutomaton(currentConversionData.converted_dfa, "dfa");
      }
      break;
    case "tab-trace":
      currentActiveView = "minimal";
      if (currentConversionData.minimal_dfa) {
        graphManager.loadAutomaton(currentConversionData.minimal_dfa, "minimal");
      }
      break;
    default:
      if (currentConversionData.nfa) {
        graphManager.loadAutomaton(currentConversionData.nfa, "nfa");
      }
      break;
  }

  // Synchronize simulation playback view
  if (simulatorPlayer && typeof simulatorPlayer.switchView === "function") {
    simulatorPlayer.switchView(currentActiveView);
  }
}

function setupSampleSelector() {
  const select = document.getElementById("sample-select");
  select.addEventListener("change", (e) => {
    if (e.target.value !== "custom") {
      loadSample(e.target.value);
    }
  });
}

function loadSample(key) {
  const sample = SAMPLE_AUTOMATA[key];
  if (sample) {
    document.getElementById("nfa-json").value = JSON.stringify(sample, null, 2);
  }
}

function setupButtons() {
  document.getElementById("btn-convert").addEventListener("click", () => {
    convertCurrentNFA();
  });

  document.getElementById("btn-reset").addEventListener("click", () => {
    loadSample("sample_01");
    document.getElementById("sample-select").value = "sample_01";
    convertCurrentNFA();
  });

  document.getElementById("btn-simulate").addEventListener("click", () => {
    simulateInputString();
  });
}

function setupExportButtons() {
  const btnExportPng = document.getElementById("btn-export-png");
  if (btnExportPng) {
    btnExportPng.addEventListener("click", () => {
      exportGraph("png");
    });
  }

  const btnExportSvg = document.getElementById("btn-export-svg");
  if (btnExportSvg) {
    btnExportSvg.addEventListener("click", () => {
      exportGraph("svg");
    });
  }
}

function exportGraph(format) {
  if (!graphManager) {
    showToast("Graph Manager is not initialized", "warning");
    return;
  }
  if (!currentConversionData) {
    showToast("Please convert an automaton before exporting", "info");
    return;
  }

  try {
    if (typeof graphManager.exportImage === "function") {
      graphManager.exportImage(format);
    }
  } catch (err) {
    console.error(`Export ${format} failed:`, err);
    showToast(`Export failed: ${err.message}`, "error");
  }
}

function setupCanvasControls() {
  const btnRelayout = document.getElementById("tool-relayout");
  if (btnRelayout) {
    btnRelayout.addEventListener("click", () => {
      if (graphManager && typeof graphManager.runLayout === "function") {
        graphManager.runLayout();
        showToast("Auto-layout recalculated", "info");
      }
    });
  }

  const btnZoomFit = document.getElementById("tool-zoom-fit");
  if (btnZoomFit) {
    btnZoomFit.addEventListener("click", () => {
      if (graphManager && typeof graphManager.fit === "function") {
        graphManager.fit();
      }
    });
  }
}

async function renderDot(containerId, dotString) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = "Rendering diagram...";

  if (vizInstance) {
    try {
      const element = await vizInstance.renderSVGElement(dotString);
      container.innerHTML = "";
      container.appendChild(element);
      return;
    } catch (err) {
      console.warn("Viz.js rendering error:", err);
    }
  }

  // Fallback to formatted text
  container.innerHTML = `<pre style="font-size:12px; text-align:left; padding:10px; max-height:260px; overflow:auto;">${escapeHtml(dotString)}</pre>`;
}

async function convertCurrentNFA() {
  const jsonText = document.getElementById("nfa-json").value;
  let parsedNFA;
  try {
    parsedNFA = JSON.parse(jsonText);
  } catch (err) {
    showToast("Invalid JSON format in NFA definition: " + err.message, "error");
    return;
  }

  try {
    const res = await fetch("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nfa: parsedNFA })
    });
    const data = await res.json();
    if (data.error) {
      showToast("Conversion Error: " + data.error, "error");
      return;
    }

    currentConversionData = data;
    if (simulatorPlayer) {
      simulatorPlayer.pause();
      simulatorPlayer.reset();
    }
    renderNFAView(data);
    renderConversionView(data);
    renderDFAView(data);
    renderMinimalDFAView(data);

    // Synchronize interactive canvas with the currently active tab
    const activeTab = document.querySelector(".tab.active");
    const activeTabId = activeTab ? activeTab.getAttribute("data-tab") : "tab-nfa";
    syncGraphWithTab(activeTabId);

    // Automatically generate sample test cases for quick one-click testing
    if (typeof generateTestStrings === "function") {
      generateTestStrings();
    }

    showToast("Automaton converted and minimized successfully", "success");
  } catch (err) {
    console.error(err);
    showToast("API Request Failed: " + err.message, "error");
  }
}

function renderNFAView(data) {
  renderDot("nfa-diagram", data.nfa_dot);

  // Transition table
  const nfa = data.nfa;
  const symbols = [...nfa.alphabet];
  const hasEps = nfa.transitions.some(t => t.symbol === "ε" || t.symbol === "e");
  if (hasEps) symbols.push("ε");

  let tableHtml = "<table><thead><tr><th>State</th>";
  symbols.forEach(s => tableHtml += `<th>${s}</th>`);
  tableHtml += "</tr></thead><tbody>";

  nfa.states.forEach(st => {
    const isStart = st === nfa.start_state;
    const isFinal = nfa.final_states.includes(st);
    let lbl = (isStart ? "→ " : "") + (isFinal ? "* " : "") + st;
    tableHtml += `<tr><td><strong>${lbl}</strong></td>`;

    symbols.forEach(sym => {
      const trans = nfa.transitions.find(t => t.from === st && t.symbol === sym);
      const targets = trans ? trans.to : [];
      tableHtml += `<td>${targets.length ? "{" + targets.join(", ") + "}" : "∅"}</td>`;
    });
    tableHtml += "</tr>";
  });
  tableHtml += "</tbody></table>";
  document.getElementById("nfa-table-view").innerHTML = tableHtml;

  // Epsilon closures
  let closuresHtml = "<h4>Computed ε-Closures:</h4><ul>";
  for (const [st, closure] of Object.entries(data.epsilon_closures || {})) {
    closuresHtml += `<li><strong>ε-closure(${st})</strong> = { ${closure.join(", ")} }</li>`;
  }
  closuresHtml += "</ul>";
  document.getElementById("epsilon-closures-view").innerHTML = closuresHtml;
}

function renderConversionView(data) {
  // Subset construction table
  let tableHtml = `<table><thead><tr>
    <th>Step</th><th>DFA State</th><th>NFA Subset</th><th>Input</th><th>Move(S, a)</th><th>Target Subset (ε-closure)</th><th>Target DFA State</th><th>New State?</th>
  </tr></thead><tbody>`;

  (data.conversion_steps || []).forEach(step => {
    tableHtml += `<tr>
      <td>${step.step_number}</td>
      <td><strong>${step.dfa_state}</strong></td>
      <td>{ ${step.nfa_subset.join(", ")} }</td>
      <td><code>${step.symbol}</code></td>
      <td>{ ${step.union_set.join(", ")} }</td>
      <td>{ ${step.epsilon_closure_set.join(", ")} }</td>
      <td><strong>${step.target_dfa_state}</strong></td>
      <td><span class="status-badge ${step.is_new_state ? 'status-accept' : 'status-info'}">${step.is_new_state ? 'Yes' : 'No'}</span></td>
    </tr>`;
  });
  tableHtml += "</tbody></table>";
  document.getElementById("conversion-table-view").innerHTML = tableHtml;

  // State mapping
  let mappingHtml = "<table><thead><tr><th>DFA State</th><th>Original NFA Subset</th><th>Status</th></tr></thead><tbody>";
  for (const [dfaState, nfaStates] of Object.entries(data.state_mapping || {})) {
    const isFinal = data.converted_dfa.final_states.includes(dfaState);
    const isStart = dfaState === data.converted_dfa.start_state;
    let badge = isStart ? '<span class="status-badge status-info">Start</span> ' : '';
    if (isFinal) badge += '<span class="status-badge status-accept">Accepting</span>';

    mappingHtml += `<tr>
      <td><strong>${dfaState}</strong></td>
      <td>{ ${nfaStates.join(", ")} }</td>
      <td>${badge || '<span class="status-badge">Non-final</span>'}</td>
    </tr>`;
  }
  mappingHtml += "</tbody></table>";
  document.getElementById("state-mapping-view").innerHTML = mappingHtml;
}

function renderDFAView(data) {
  renderDot("dfa-diagram", data.converted_dfa_dot);

  const dfa = data.converted_dfa;
  let tableHtml = "<table><thead><tr><th>State</th>";
  dfa.alphabet.forEach(s => tableHtml += `<th>${s}</th>`);
  tableHtml += "</tr></thead><tbody>";

  dfa.states.forEach(st => {
    const isStart = st === dfa.start_state;
    const isFinal = dfa.final_states.includes(st);
    let lbl = (isStart ? "→ " : "") + (isFinal ? "* " : "") + st;
    tableHtml += `<tr><td><strong>${lbl}</strong></td>`;

    dfa.alphabet.forEach(sym => {
      const trans = dfa.transitions.find(t => t.from === st && t.symbol === sym);
      tableHtml += `<td>${trans ? trans.to : "—"}</td>`;
    });
    tableHtml += "</tr>";
  });
  tableHtml += "</tbody></table>";
  document.getElementById("dfa-table-view").innerHTML = tableHtml;
}

function renderMinimalDFAView(data) {
  renderDot("min-dfa-diagram", data.minimal_dfa_dot);

  // Triangular table
  const dist = data.distinguishable_table;
  if (dist && dist.ordered_states && dist.ordered_states.length > 1) {
    const ordered = dist.ordered_states;
    const n = ordered.length;
    let triHtml = "<table><thead><tr><th>State</th>";
    for (let i = 0; i < n - 1; i++) {
      triHtml += `<th>${ordered[i]}</th>`;
    }
    triHtml += "</tr></thead><tbody>";

    for (let i = 1; i < n; i++) {
      triHtml += `<tr><td><strong>${ordered[i]}</strong></td>`;
      for (let j = 0; j < i; j++) {
        const key = `${ordered[j]},${ordered[i]}`;
        const entry = dist.pairs[key];
        const isDist = entry && entry.distinguishable;
        triHtml += `<td style="text-align:center;">${isDist ? '<span style="color:var(--danger); font-weight:bold;">X</span>' : '<span style="color:var(--success); font-weight:bold;">=</span>'}</td>`;
      }
      for (let k = i; k < n - 1; k++) {
        triHtml += `<td style="background:#f1f3f4; text-align:center;">—</td>`;
      }
      triHtml += "</tr>";
    }
    triHtml += "</tbody></table>";
    document.getElementById("min-triangular-view").innerHTML = triHtml;
  } else {
    document.getElementById("min-triangular-view").innerHTML = "<p>DFA is already minimal (≤ 1 state).</p>";
  }

  // Minimal DFA Transition Table
  const minDfa = data.minimal_dfa;
  let tableHtml = "<table><thead><tr><th>Minimal State</th>";
  minDfa.alphabet.forEach(s => tableHtml += `<th>${s}</th>`);
  tableHtml += "<th>Equivalent Original DFA States</th></tr></thead><tbody>";

  minDfa.states.forEach(st => {
    const isStart = st === minDfa.start_state;
    const isFinal = minDfa.final_states.includes(st);
    let lbl = (isStart ? "→ " : "") + (isFinal ? "* " : "") + st;
    tableHtml += `<tr><td><strong>${lbl}</strong></td>`;

    minDfa.alphabet.forEach(sym => {
      const trans = minDfa.transitions.find(t => t.from === st && t.symbol === sym);
      tableHtml += `<td>${trans ? trans.to : "—"}</td>`;
    });
    const origStates = (data.min_state_mapping && data.min_state_mapping[st]) || [st];
    tableHtml += `<td>{ ${origStates.join(", ")} }</td></tr>`;
  });
  tableHtml += "</tbody></table>";
  document.getElementById("min-dfa-table-view").innerHTML = tableHtml;
}

async function simulateInputString() {
  const jsonText = document.getElementById("nfa-json").value;
  const inputStr = document.getElementById("sim-input").value;
  let parsedNFA;
  try {
    parsedNFA = JSON.parse(jsonText);
  } catch (err) {
    showToast("Invalid JSON: " + err.message, "error");
    return;
  }

  try {
    const res = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nfa: parsedNFA, input_string: inputStr })
    });
    const data = await res.json();
    if (data.error) {
      showToast("Simulation Error: " + data.error, "error");
      return;
    }

    renderSimulationTrace(data);

    // Switch to trace tab automatically
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));
    const traceTab = document.querySelector('[data-tab="tab-trace"]');
    if (traceTab) traceTab.classList.add("active");
    const traceContent = document.getElementById("tab-trace");
    if (traceContent) traceContent.classList.add("active");

    // Sync graph with trace tab
    syncGraphWithTab("tab-trace");

    // Initialize SimulatorPlayer with trace data
    if (simulatorPlayer) {
      simulatorPlayer.loadSimulation(data, currentActiveView);
    }

    showToast("Simulation trace generated successfully", "success");
  } catch (err) {
    showToast("Simulation request failed: " + err.message, "error");
  }
}

function renderSimulationTrace(data) {
  const nfaSim = data.nfa_simulation;
  const dfaSim = data.minimal_dfa_simulation;
  const isEquiv = data.is_equivalent;

  const verdictDiv = document.getElementById("sim-verdict-container");
  verdictDiv.style.display = "block";
  verdictDiv.innerHTML = `
    <div style="padding:12px; border-radius:6px; background:${isEquiv ? '#e6f4ea' : '#fce8e6'}; border:1px solid ${isEquiv ? '#ceead6' : '#fad2cf'};">
      <strong>Equivalence Verdict:</strong> ${isEquiv ? 'PASS (NFA and DFA agree)' : 'FAIL (Verdict mismatch)'}<br/>
      <small>NFA Result: <strong>${nfaSim.accepted ? 'ACCEPTED' : 'REJECTED'}</strong> | Minimal DFA Result: <strong>${dfaSim.accepted ? 'ACCEPTED' : 'REJECTED'}</strong></small>
    </div>
  `;

  let html = `
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-top:16px;">
      <div>
        <h4>NFA Step-by-Step Trace</h4>
        <p style="font-size:12px; margin-bottom:10px;">${nfaSim.message}</p>
        <div>
          ${nfaSim.trace.map(s => `
            <div class="trace-step">
              <span class="badge" style="background:#eee; color:#333;">Step ${s.step_number}</span>
              <div>
                <div>Active: <strong>{ ${Array.isArray(s.current_states) ? s.current_states.join(", ") : s.current_states} }</strong></div>
                <small style="color:var(--text-muted);">${s.description}</small>
              </div>
            </div>
          `).join("")}
        </div>
      </div>

      <div>
        <h4>Minimal DFA Step-by-Step Trace</h4>
        <p style="font-size:12px; margin-bottom:10px;">${dfaSim.message}</p>
        <div>
          ${dfaSim.trace.map(s => `
            <div class="trace-step" style="border-left-color:var(--success);">
              <span class="badge" style="background:#e6f4ea; color:var(--success);">Step ${s.step_number}</span>
              <div>
                <div>State: <strong>${s.current_states}</strong></div>
                <small style="color:var(--text-muted);">${s.description}</small>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    </div>
  `;

  document.getElementById("trace-comparison-view").innerHTML = html;

  // Enable click-to-seek on trace step cards
  document.querySelectorAll(".trace-step").forEach(stepCard => {
    stepCard.style.cursor = "pointer";
    stepCard.title = "Click to jump playback to this step";
    stepCard.addEventListener("click", () => {
      const stepBadge = stepCard.querySelector(".badge");
      if (stepBadge && simulatorPlayer) {
        const match = stepBadge.textContent.match(/Step\s+(\d+)/i);
        if (match) {
          const stepIdx = parseInt(match[1], 10);
          simulatorPlayer.seek(stepIdx);
          showToast(`Jumped to Step ${stepIdx}`, "info", 1500);
        }
      }
    });
  });

  // Highlight fallback if SimulatorPlayer is not active
  if (!simulatorPlayer && graphManager && dfaSim && dfaSim.trace && dfaSim.trace.length > 0) {
    const lastStep = dfaSim.trace[dfaSim.trace.length - 1];
    const prevStep = dfaSim.trace.length > 1 ? dfaSim.trace[dfaSim.trace.length - 2] : null;
    const traversed = (prevStep && lastStep.symbol_consumed !== null) ? [{
      from: prevStep.current_states,
      to: lastStep.current_states,
      symbol: lastStep.symbol_consumed
    }] : [];
    graphManager.highlightSimulationStep(
      lastStep.current_states,
      traversed,
      prevStep ? prevStep.current_states : []
    );
  }
}

function showToast(message, type = "info", duration = 4000) {
  const container = document.getElementById("toast-container");
  if (!container) {
    console.log(`[Toast ${type}]: ${message}`);
    return;
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  const icons = {
    success: "✓",
    error: "✕",
    warning: "⚠",
    info: "ℹ"
  };

  const titles = {
    success: "Success",
    error: "Error",
    warning: "Warning",
    info: "Notification"
  };

  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || "ℹ"}</span>
    <div class="toast-body">
      <div class="toast-title">${titles[type] || "Notification"}</div>
      <div class="toast-message">${escapeHtml(message)}</div>
    </div>
    <button class="toast-close" type="button" aria-label="Close">&times;</button>
  `;

  const closeBtn = toast.querySelector(".toast-close");
  const dismiss = () => {
    toast.classList.add("toast-hiding");
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  };

  closeBtn.addEventListener("click", dismiss);
  container.appendChild(toast);

  if (duration > 0) {
    setTimeout(dismiss, duration);
  }
}

// Expose showToast to window for global access
if (typeof window !== "undefined") {
  window.showToast = showToast;
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}

// ---------------------------------------------------------------------------
// Milestone 5: Regex-to-NFA UI Integration
// ---------------------------------------------------------------------------

function setupRegexConverter() {
  const btn = document.getElementById("btn-convert-regex") || document.getElementById("btn-regex-convert");
  const input = document.getElementById("regex-input");

  if (btn) {
    btn.addEventListener("click", () => {
      convertRegexToNFA();
    });
  }

  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        convertRegexToNFA();
      }
    });
  }
}

async function convertRegexToNFA() {
  const input = document.getElementById("regex-input");
  if (!input) return;

  const regexStr = input.value.trim();
  if (!regexStr) {
    showToast("Please enter a regular expression to convert", "warning");
    input.focus();
    return;
  }

  const btn = document.getElementById("btn-convert-regex") || document.getElementById("btn-regex-convert");
  const origText = btn ? btn.textContent : "Build NFA";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Building...";
  }

  try {
    const res = await fetch("/api/regex-to-nfa", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ regex: regexStr })
    });
    const data = await res.json();

    if (!data.success || data.error) {
      showToast("Regex Conversion Error: " + (data.error || "Failed to convert regex"), "error");
      return;
    }

    const nfa = data.nfa;

    // 1. Update NFA JSON textarea
    const jsonArea = document.getElementById("nfa-json");
    if (jsonArea) {
      jsonArea.value = JSON.stringify(nfa, null, 2);
    }

    // 2. Set sample select to custom
    const sampleSelect = document.getElementById("sample-select");
    if (sampleSelect) {
      sampleSelect.value = "custom";
    }

    // 3. Switch active view tab to Original NFA tab
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));
    const nfaTab = document.querySelector('[data-tab="tab-nfa"]');
    if (nfaTab) nfaTab.classList.add("active");
    const nfaContent = document.getElementById("tab-nfa");
    if (nfaContent) nfaContent.classList.add("active");

    // 4. Run conversion pipeline (updates DFA, Minimal DFA, and Cytoscape canvas)
    await convertCurrentNFA();

    showToast(`Converted regex "${regexStr}" to Thompson NFA successfully`, "success");
  } catch (err) {
    console.error("Regex conversion failed:", err);
    showToast("Regex conversion request failed: " + err.message, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = origText;
    }
  }
}

// ---------------------------------------------------------------------------
// Milestone 5: Automated Test String Generator UI Integration
// ---------------------------------------------------------------------------

function setupTestStringGenerator() {
  const btn = document.getElementById("btn-generate-strings");
  if (btn) {
    btn.addEventListener("click", () => {
      generateTestStrings();
    });
  }
}

async function generateTestStrings() {
  const jsonText = document.getElementById("nfa-json")?.value;
  if (!jsonText) {
    showToast("No automaton definition found in editor", "warning");
    return;
  }

  let parsedNFA;
  try {
    parsedNFA = JSON.parse(jsonText);
  } catch (err) {
    showToast("Invalid JSON in automaton definition: " + err.message, "error");
    return;
  }

  const btn = document.getElementById("btn-generate-strings");
  const origText = btn ? btn.textContent : "Generate Cases";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Generating...";
  }

  try {
    const res = await fetch("/api/generate-strings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nfa: parsedNFA,
        max_accepted: 3,
        max_rejected: 3
      })
    });
    const data = await res.json();

    if (!data.success || data.error) {
      showToast("String Generation Error: " + (data.error || "Failed to generate strings"), "error");
      return;
    }

    renderTestPills(data.accepted_strings || [], data.rejected_strings || []);
    showToast(`Generated ${(data.accepted_strings || []).length} accepted and ${(data.rejected_strings || []).length} rejected test cases`, "success");
  } catch (err) {
    console.error("Test string generation failed:", err);
    showToast("Failed to generate test strings: " + err.message, "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = origText;
    }
  }
}

function renderTestPills(acceptedStrings, rejectedStrings) {
  const acceptedContainer = document.getElementById("accepted-pills");
  const rejectedContainer = document.getElementById("rejected-pills");

  if (acceptedContainer) {
    acceptedContainer.innerHTML = "";
    if (acceptedStrings.length === 0) {
      acceptedContainer.innerHTML = '<span class="placeholder-pill">No accepted strings (empty language)</span>';
    } else {
      acceptedStrings.forEach(str => {
        const pill = createTestPill(str, "accepted");
        acceptedContainer.appendChild(pill);
      });
    }
  }

  if (rejectedContainer) {
    rejectedContainer.innerHTML = "";
    if (rejectedStrings.length === 0) {
      rejectedContainer.innerHTML = '<span class="placeholder-pill">No rejected strings (universal language)</span>';
    } else {
      rejectedStrings.forEach(str => {
        const pill = createTestPill(str, "rejected");
        rejectedContainer.appendChild(pill);
      });
    }
  }
}

function createTestPill(str, type) {
  const pill = document.createElement("button");
  pill.type = "button";
  pill.className = `string-pill ${type} pill-${type}`;
  pill.textContent = str === "" ? "ε" : str;
  pill.title = str === "" ? "Empty string (ε) — click to test" : `Test string: "${str}" — click to simulate`;
  pill.dataset.value = str;

  pill.addEventListener("click", () => {
    // Highlight clicked pill
    document.querySelectorAll(".string-pill").forEach(p => p.classList.remove("active", "pill-active"));
    pill.classList.add("active", "pill-active");

    // Populate sim-input
    const simInput = document.getElementById("sim-input");
    if (simInput) {
      simInput.value = str;
    }

    // Trigger simulation playback
    simulateInputString();
  });

  return pill;
}
