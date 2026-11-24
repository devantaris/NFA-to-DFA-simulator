// Frontend Application Controller for CSET302 Automata Theory Simulator

const SAMPLE_AUTOMATA = {
  sample_01: {
    name: "Ends_With_01",
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
  }
};

let currentConversionData = null;
let vizInstance = null;
let graphManager = null;
let currentActiveView = "nfa";

// Initialize Viz.js if available
if (typeof Viz !== "undefined") {
  vizInstance = new Viz();
}

document.addEventListener("DOMContentLoaded", () => {
  initGraphManager();
  setupTabs();
  setupSampleSelector();
  setupButtons();
  setupExportButtons();
  setupCanvasControls();

  // Load sample 1 initially
  loadSample("sample_01");
  convertCurrentNFA();
});

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
    } catch (err) {
      console.error("Failed to initialize GraphManager:", err);
    }
  } else {
    console.info("GraphManager class not yet loaded.");
  }
}

function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));

      tab.classList.add("active");
      const targetId = tab.getAttribute("data-tab");
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
    renderNFAView(data);
    renderConversionView(data);
    renderDFAView(data);
    renderMinimalDFAView(data);

    // Synchronize interactive canvas with the currently active tab
    const activeTab = document.querySelector(".tab.active");
    const activeTabId = activeTab ? activeTab.getAttribute("data-tab") : "tab-nfa";
    syncGraphWithTab(activeTabId);

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

  // Highlight simulation final state on active graph canvas if available
  if (graphManager && dfaSim && dfaSim.trace && dfaSim.trace.length > 0) {
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
