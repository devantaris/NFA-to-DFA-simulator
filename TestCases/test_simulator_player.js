/**
 * Unit Test Suite for SimulatorPlayer (Milestone 4)
 * Runs under Node.js with a lightweight DOM mock environment.
 */

const assert = require('assert');
const path = require('path');

// Mock browser DOM environment
function createMockElement(id = '', tagName = 'div') {
  const classes = new Set();
  const attributes = {};
  const children = [];
  const eventListeners = {};

  return {
    id: id,
    tagName: tagName.toUpperCase(),
    value: '',
    min: '0',
    max: '0',
    textContent: '',
    innerHTML: '',
    style: {},
    title: '',
    disabled: false,
    classList: {
      add: (...cls) => cls.forEach(c => classes.add(c)),
      remove: (...cls) => cls.forEach(c => classes.delete(c)),
      contains: (c) => classes.has(c),
      toggle: (c) => classes.has(c) ? classes.delete(c) : classes.add(c),
      get length() { return classes.size; }
    },
    className: '',
    setAttribute: (k, v) => { attributes[k] = String(v); },
    getAttribute: (k) => attributes[k] || null,
    appendChild: (child) => { children.push(child); return child; },
    removeChild: (child) => {
      const idx = children.indexOf(child);
      if (idx !== -1) children.splice(idx, 1);
      return child;
    },
    addEventListener: (evt, fn) => {
      if (!eventListeners[evt]) eventListeners[evt] = [];
      eventListeners[evt].push(fn);
    },
    dispatchEvent: (evt) => {
      if (eventListeners[evt]) {
        eventListeners[evt].forEach(fn => fn({ target: this }));
      }
    },
    querySelector: (sel) => {
      if (sel.startsWith('#')) {
        const targetId = sel.slice(1);
        return children.find(c => c.id === targetId) || null;
      }
      if (sel.startsWith('.')) {
        const targetClass = sel.slice(1);
        return children.find(c => c.classList && c.classList.contains(targetClass)) || null;
      }
      return null;
    },
    querySelectorAll: (sel) => {
      if (sel.startsWith('.')) {
        const targetClass = sel.slice(1);
        return children.filter(c => c.classList && c.classList.contains(targetClass));
      }
      return children;
    },
    scrollIntoView: () => {}
  };
}

const mockDocument = {
  elements: {},
  getElementById: function(id) {
    if (!this.elements[id]) {
      this.elements[id] = createMockElement(id);
    }
    return this.elements[id];
  },
  createElement: function(tag) {
    return createMockElement('', tag);
  },
  activeElement: null
};

global.document = mockDocument;
global.window = {
  addEventListener: () => {},
  document: mockDocument
};

const SimulatorPlayer = require('../SourceCode/web/static/simulator_player.js');

// Mock GraphManager
class MockGraphManager {
  constructor() {
    this.calls = [];
  }
  highlightSimulationStep(activeStates, traversedEdges, previousStates) {
    this.calls.push({ activeStates, traversedEdges, previousStates });
  }
  clearHighlights() {
    this.calls.push({ action: 'clear' });
  }
}

// Sample simulation fixture from /api/simulate
const sampleSimResult = {
  input_string: "01",
  nfa_simulation: {
    accepted: true,
    input_string: "01",
    automaton_type: "NFA",
    start_state: "q0",
    final_states_reached: ["q2"],
    trace: [
      {
        step_number: 0,
        current_states: ["q0"],
        symbol_consumed: null,
        remaining_input: "01",
        next_states: ["q0"],
        description: "Initial state: {q0}"
      },
      {
        step_number: 1,
        current_states: ["q0"],
        symbol_consumed: "0",
        remaining_input: "1",
        next_states: ["q0", "q1"],
        description: "Consumed '0': moved to {q0, q1}"
      },
      {
        step_number: 2,
        current_states: ["q0", "q1"],
        symbol_consumed: "1",
        remaining_input: "",
        next_states: ["q0", "q2"],
        description: "Consumed '1': moved to {q0, q2}"
      }
    ],
    message: "ACCEPTED: Reached final state {q2}"
  },
  minimal_dfa_simulation: {
    accepted: true,
    input_string: "01",
    automaton_type: "DFA",
    start_state: "A",
    final_states_reached: ["C"],
    trace: [
      {
        step_number: 0,
        current_states: "A",
        symbol_consumed: null,
        remaining_input: "01",
        next_states: "A",
        description: "Initial state: A"
      },
      {
        step_number: 1,
        current_states: "A",
        symbol_consumed: "0",
        remaining_input: "1",
        next_states: "B",
        description: "Consumed '0': A -> B"
      },
      {
        step_number: 2,
        current_states: "B",
        symbol_consumed: "1",
        remaining_input: "",
        next_states: "C",
        description: "Consumed '1': B -> C"
      }
    ],
    message: "ACCEPTED: Ended in final state C"
  },
  is_equivalent: true
};

console.log("===============================================================================");
console.log("          SIMULATOR PLAYER: TEST SUITE EXECUTION");
console.log("===============================================================================");

// Test 1: Instantiation & Defaults
{
  const gm = new MockGraphManager();
  const player = new SimulatorPlayer({ graphManager: gm });
  assert.strictEqual(player.stepIndex, 0);
  assert.strictEqual(player.isPlaying, false);
  assert.strictEqual(player.speedMultiplier, 1.0);
  assert.strictEqual(player.currentView, 'minimal');
  assert.strictEqual(player.graphManager, gm);
  console.log("✓ Test 1: Instantiation and default properties verified.");
}

// Test 2: Loading Simulation Data
{
  const gm = new MockGraphManager();
  const player = new SimulatorPlayer({ graphManager: gm });
  player.loadSimulation(sampleSimResult, 'minimal');

  assert.strictEqual(player.getMaxSteps(), 3);
  assert.strictEqual(player.stepIndex, 0);
  assert.strictEqual(player.isPlaying, false);
  assert.strictEqual(gm.calls.length, 1);
  assert.deepStrictEqual(gm.calls[0].activeStates, "A");
  console.log("✓ Test 2: loadSimulation sets stepIndex=0 and highlights initial state on GraphManager.");
}

// Test 3: Stepping Forward and Backward
{
  const gm = new MockGraphManager();
  const player = new SimulatorPlayer({ graphManager: gm });
  player.loadSimulation(sampleSimResult, 'minimal');

  // Step 1
  player.stepForward();
  assert.strictEqual(player.stepIndex, 1);
  assert.strictEqual(gm.calls[1].activeStates, "B");
  assert.deepStrictEqual(gm.calls[1].traversedEdges, [{ from: "A", to: "B", symbol: "0" }]);

  // Step 2 (End)
  player.stepForward();
  assert.strictEqual(player.stepIndex, 2);
  assert.strictEqual(gm.calls[2].activeStates, "C");
  assert.deepStrictEqual(gm.calls[2].traversedEdges, [{ from: "B", to: "C", symbol: "1" }]);

  // Cannot step forward past end
  player.stepForward();
  assert.strictEqual(player.stepIndex, 2);

  // Step backward to Step 1
  player.stepBackward();
  assert.strictEqual(player.stepIndex, 1);
  assert.strictEqual(gm.calls[3].activeStates, "B");

  // Step backward to Step 0
  player.stepBackward();
  assert.strictEqual(player.stepIndex, 0);

  // Cannot step backward past 0
  player.stepBackward();
  assert.strictEqual(player.stepIndex, 0);

  console.log("✓ Test 3: stepForward and stepBackward boundaries and highlighting verified.");
}

// Test 4: Reset and Seek
{
  const gm = new MockGraphManager();
  const player = new SimulatorPlayer({ graphManager: gm });
  player.loadSimulation(sampleSimResult, 'minimal');

  player.seek(2);
  assert.strictEqual(player.stepIndex, 2);

  // Clamping
  player.seek(999);
  assert.strictEqual(player.stepIndex, 2);

  player.seek(-5);
  assert.strictEqual(player.stepIndex, 0);

  player.seek(2);
  player.reset();
  assert.strictEqual(player.stepIndex, 0);
  assert.strictEqual(player.isPlaying, false);

  console.log("✓ Test 4: seek() clamping and reset() verified.");
}

// Test 5: Speed Adjustment
{
  const player = new SimulatorPlayer();
  player.setSpeed(2.0);
  assert.strictEqual(player.speedMultiplier, 2.0);

  player.setSpeed(0.5);
  assert.strictEqual(player.speedMultiplier, 0.5);

  player.setSpeed("4.0");
  assert.strictEqual(player.speedMultiplier, 4.0);

  console.log("✓ Test 5: Speed multiplier adjustment verified.");
}

// Test 6: View Switching (Minimal DFA <-> NFA)
{
  const gm = new MockGraphManager();
  const player = new SimulatorPlayer({ graphManager: gm });
  player.loadSimulation(sampleSimResult, 'minimal');

  player.seek(1);
  assert.strictEqual(player.stepIndex, 1);
  assert.strictEqual(player.currentView, 'minimal');

  // Switch to NFA
  player.switchView('nfa');
  assert.strictEqual(player.currentView, 'nfa');
  assert.strictEqual(player.stepIndex, 1); // Preserves step index

  const lastCall = gm.calls[gm.calls.length - 1];
  assert.deepStrictEqual(lastCall.activeStates, ["q0", "q1"]); // NFA active states at step 1
  console.log("✓ Test 6: switchView synchronizes current step position with NFA trace.");
}

// Test 7: Empty String (ε) Handling
{
  const emptySimResult = {
    input_string: "",
    minimal_dfa_simulation: {
      accepted: false,
      input_string: "",
      automaton_type: "DFA",
      start_state: "q0",
      final_states_reached: "q0",
      trace: [
        {
          step_number: 0,
          current_states: "q0",
          symbol_consumed: null,
          remaining_input: "",
          next_states: "q0",
          description: "Initial state: q0"
        }
      ],
      message: "REJECTED: Initial state is not final"
    }
  };

  const gm = new MockGraphManager();
  const player = new SimulatorPlayer({ graphManager: gm });
  player.loadSimulation(emptySimResult, 'minimal');

  assert.strictEqual(player.getMaxSteps(), 1);
  assert.strictEqual(player.stepIndex, 0);
  console.log("✓ Test 7: Empty string (ε) simulation loaded cleanly with 1 initial step.");
}

console.log("===============================================================================");
console.log("✓ ALL SIMULATOR PLAYER UNIT TESTS PASSED (7/7)");
console.log("===============================================================================");
