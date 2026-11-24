/**
 * SimulatorPlayer - Step-by-Step Simulation Playback Engine & Motion Graphics Controller
 *
 * Provides:
 * - Playback State Machine managing simulation trace steps from POST /api/simulate
 * - Dual execution support for both NFA and Minimal DFA simulation traces
 * - Smooth step-by-step playback loop with dynamic interval timer (0.25x to 4x)
 * - Media controls: play, pause, step-forward, step-backward, reset, seek, speed control
 * - Input String Tape Visualizer with illuminated active cursor, consumed pills, upcoming neutral cells
 * - Epsilon transition handling and graceful empty string (ε / "") visualization
 * - Visual graph canvas coordination with GraphManager (active states neon glow & edge traversal pulses)
 * - Dynamic Scrubber and step counter synchronization
 * - Sleek glassmorphic Step Detail Card updates
 * - Prominent Glowing Verdict Card (neon emerald for ACCEPTED, neon rose for REJECTED)
 * - Seamless view synchronization when toggling between NFA and Minimal DFA tabs
 *
 * Course: CSET302 - Automata Theory & Computability
 */

class SimulatorPlayer {
  /**
   * @param {Object} [options] - Configuration options
   */
  constructor(options = {}) {
    this.options = Object.assign({
      baseInterval: 900,
      graphManager: null,
      onStepChanged: null
    }, options);

    this.graphManager = this.options.graphManager || (typeof window !== 'undefined' ? window.graphManager : null);
    this.onStepChanged = this.options.onStepChanged || null;

    // Simulation Data & Playback State
    this.simulationResult = null; // Payload from /api/simulate
    this.currentView = 'minimal'; // 'nfa' | 'dfa' | 'minimal'
    this.stepIndex = 0;
    this.isPlaying = false;
    this.playbackTimer = null;
    this.speedMultiplier = 1.0;
    this.baseInterval = this.options.baseInterval;

    // Cached DOM element references
    this.elements = {};
    this.isBound = false;
  }

  /**
   * Initialize DOM element bindings and attach event listeners
   * @param {Object} [customElements={}] - Custom element overrides
   */
  init(customElements = {}) {
    if (typeof document === 'undefined') return this;

    this.elements = {
      playBtn: customElements.playBtn || document.getElementById('btn-play') || document.getElementById('btn-playback-play'),
      pauseBtn: customElements.pauseBtn || document.getElementById('btn-pause'),
      stepFwdBtn: customElements.stepFwdBtn || document.getElementById('btn-step-fwd') || document.getElementById('btn-playback-step-fwd'),
      stepBwdBtn: customElements.stepBwdBtn || document.getElementById('btn-step-bwd') || document.getElementById('btn-playback-step-back'),
      resetBtn: customElements.resetBtn || document.getElementById('btn-reset-sim') || document.getElementById('btn-playback-reset'),
      scrubber: customElements.scrubber || document.getElementById('sim-scrubber') || document.getElementById('playback-scrubber'),
      speedSelect: customElements.speedSelect || document.getElementById('sim-speed') || document.getElementById('playback-speed-select'),
      tapeContainer: customElements.tapeContainer || document.getElementById('simulation-tape'),
      stepDetails: customElements.stepDetails || document.getElementById('step-details'),
      verdictContainer: customElements.verdictContainer || document.getElementById('simulation-verdict') || document.getElementById('sim-verdict-container'),
      stepCounter: customElements.stepCounter || document.getElementById('playback-step-counter'),
      dockedControls: customElements.dockedControls || document.getElementById('simulation-playback-controls'),
      playIcon: document.getElementById('play-btn-icon')
    };

    if (!this.isBound) {
      this.bindControls();
    }

    return this;
  }

  /**
   * Attach interactive listeners to UI controls and keyboard shortcuts
   */
  bindControls() {
    if (this.isBound) return this;
    const el = this.elements;

    if (el.playBtn) {
      el.playBtn.addEventListener('click', () => this.togglePlay());
    }

    if (el.pauseBtn) {
      el.pauseBtn.addEventListener('click', () => this.pause());
    }

    if (el.stepFwdBtn) {
      el.stepFwdBtn.addEventListener('click', () => this.stepForward());
    }

    if (el.stepBwdBtn) {
      el.stepBwdBtn.addEventListener('click', () => this.stepBackward());
    }

    if (el.resetBtn) {
      el.resetBtn.addEventListener('click', () => this.reset());
    }

    if (el.scrubber) {
      el.scrubber.addEventListener('input', (e) => {
        const targetStep = parseInt(e.target.value, 10);
        if (!isNaN(targetStep)) {
          this.seek(targetStep);
        }
      });
      el.scrubber.addEventListener('change', (e) => {
        const targetStep = parseInt(e.target.value, 10);
        if (!isNaN(targetStep)) {
          this.seek(targetStep);
        }
      });
    }

    if (el.speedSelect) {
      el.speedSelect.addEventListener('change', (e) => {
        const speed = parseFloat(e.target.value);
        if (!isNaN(speed) && speed > 0) {
          this.setSpeed(speed);
        }
      });
    }

    // Keyboard navigation shortcuts
    if (typeof window !== 'undefined') {
      window.addEventListener('keydown', (e) => {
        // Do not intercept if user is typing inside an input or textarea
        const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
        if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select') {
          return;
        }

        if (e.code === 'Space') {
          e.preventDefault();
          this.togglePlay();
        } else if (e.code === 'ArrowRight' && (e.ctrlKey || e.metaKey || !e.shiftKey)) {
          e.preventDefault();
          this.stepForward();
        } else if (e.code === 'ArrowLeft' && (e.ctrlKey || e.metaKey || !e.shiftKey)) {
          e.preventDefault();
          this.stepBackward();
        } else if (e.code === 'Escape' || e.code === 'Home') {
          e.preventDefault();
          this.reset();
        }
      });
    }

    this.isBound = true;
    return this;
  }

  /**
   * Set or update GraphManager instance reference
   * @param {Object} gm - GraphManager instance
   */
  setGraphManager(gm) {
    this.graphManager = gm;
    return this;
  }

  /**
   * Load simulation payload from POST /api/simulate into playback engine
   * @param {Object} simulationResult - Result payload containing nfa_simulation, minimal_dfa_simulation, input_string
   * @param {string} [initialView='minimal'] - Initial view model ('nfa' | 'dfa' | 'minimal')
   */
  loadSimulation(simulationResult, initialView = 'minimal') {
    if (!simulationResult) {
      console.warn('[SimulatorPlayer] No simulation data provided to loadSimulation.');
      return;
    }

    this.init();
    this.simulationResult = simulationResult;
    this.currentView = this._normalizeView(initialView);
    this.pause();
    this.stepIndex = 0;

    // Ensure playback controller is visible
    if (this.elements.dockedControls) {
      this.elements.dockedControls.style.display = 'flex';
    }

    // Initialize tape ticker
    this._renderTape();

    // Update scrubber bounds
    const maxSteps = this.getMaxSteps();
    if (this.elements.scrubber) {
      this.elements.scrubber.min = '0';
      this.elements.scrubber.max = String(Math.max(0, maxSteps - 1));
      this.elements.scrubber.value = '0';
      this.elements.scrubber.disabled = maxSteps <= 1;
    }

    // Render initial step (step 0)
    this._renderStep(0);
  }

  /**
   * Start or resume animated playback loop
   */
  play() {
    if (!this.simulationResult) return;
    const maxSteps = this.getMaxSteps();
    if (maxSteps <= 0) return;

    // If at end, loop back to start
    if (this.stepIndex >= maxSteps - 1) {
      this.seek(0);
    }

    this.isPlaying = true;
    this._updatePlayPauseButtonUI();

    clearInterval(this.playbackTimer);
    const interval = Math.max(75, Math.round(this.baseInterval / this.speedMultiplier));
    this.playbackTimer = setInterval(() => this._onTick(), interval);
  }

  /**
   * Pause animated playback
   */
  pause() {
    this.isPlaying = false;
    clearInterval(this.playbackTimer);
    this.playbackTimer = null;
    this._updatePlayPauseButtonUI();
  }

  /**
   * Toggle between play and pause states
   */
  togglePlay() {
    if (this.isPlaying) {
      this.pause();
    } else {
      this.play();
    }
  }

  /**
   * Advance simulation forward by one step
   */
  stepForward() {
    this.pause();
    const maxSteps = this.getMaxSteps();
    if (this.stepIndex < maxSteps - 1) {
      this.seek(this.stepIndex + 1);
    }
  }

  /**
   * Step simulation backward by one step
   */
  stepBackward() {
    this.pause();
    if (this.stepIndex > 0) {
      this.seek(this.stepIndex - 1);
    }
  }

  /**
   * Reset simulation back to step 0
   */
  reset() {
    this.pause();
    this.seek(0);
  }

  /**
   * Seek directly to an arbitrary step index
   * @param {number} targetIndex - Target step index (0 <= targetIndex < maxSteps)
   */
  seek(targetIndex) {
    const maxSteps = this.getMaxSteps();
    if (maxSteps <= 0) return;

    const clampedIndex = Math.max(0, Math.min(targetIndex, maxSteps - 1));
    this.stepIndex = clampedIndex;

    this._renderStep(this.stepIndex);

    // If reached last step during auto playback, pause cleanly
    if (this.stepIndex >= maxSteps - 1 && this.isPlaying) {
      this.pause();
    }
  }

  /**
   * Update playback speed multiplier and adjust timer seamlessly
   * @param {number|string} speed - Multiplier (e.g., 0.25, 0.5, 1.0, 2.0, 4.0)
   */
  setSpeed(speed) {
    const val = parseFloat(speed);
    if (isNaN(val) || val <= 0) return;

    this.speedMultiplier = val;

    if (this.elements.speedSelect && this.elements.speedSelect.value !== String(val)) {
      this.elements.speedSelect.value = String(val);
    }

    // Restart timer seamlessly if currently playing
    if (this.isPlaying) {
      clearInterval(this.playbackTimer);
      const interval = Math.max(75, Math.round(this.baseInterval / this.speedMultiplier));
      this.playbackTimer = setInterval(() => this._onTick(), interval);
    }
  }

  /**
   * Synchronize view model when user switches between NFA and Minimal DFA tabs
   * @param {string} viewType - Target view ('nfa' | 'dfa' | 'minimal')
   */
  switchView(viewType) {
    const normalized = this._normalizeView(viewType);
    if (!this.simulationResult) {
      this.currentView = normalized;
      return;
    }

    this.currentView = normalized;
    const maxSteps = this.getMaxSteps();

    // Clamp step index if new model trace has fewer steps
    if (this.stepIndex >= maxSteps) {
      this.stepIndex = Math.max(0, maxSteps - 1);
    }

    // Update scrubber max attribute
    if (this.elements.scrubber) {
      this.elements.scrubber.max = String(Math.max(0, maxSteps - 1));
      this.elements.scrubber.value = String(this.stepIndex);
      this.elements.scrubber.disabled = maxSteps <= 1;
    }

    // Re-render current step on active graph canvas
    this._renderStep(this.stepIndex);
  }

  /**
   * Get active simulation trace array for the currently selected view
   * @returns {Array<Object>}
   */
  getActiveTrace() {
    if (!this.simulationResult) return [];

    const res = this.getActiveSimulationResult();
    if (res && Array.isArray(res.trace)) {
      return res.trace;
    }

    // Fallbacks
    if (this.simulationResult.minimal_dfa_simulation && this.simulationResult.minimal_dfa_simulation.trace) {
      return this.simulationResult.minimal_dfa_simulation.trace;
    }
    if (this.simulationResult.nfa_simulation && this.simulationResult.nfa_simulation.trace) {
      return this.simulationResult.nfa_simulation.trace;
    }

    return [];
  }

  /**
   * Get active simulation result object for the currently selected view
   * @returns {Object|null}
   */
  getActiveSimulationResult() {
    if (!this.simulationResult) return null;

    if (this.currentView === 'nfa') {
      return this.simulationResult.nfa_simulation || null;
    }
    if (this.currentView === 'dfa') {
      return this.simulationResult.converted_dfa_simulation || this.simulationResult.dfa_simulation || null;
    }
    // Default to minimal DFA
    return this.simulationResult.minimal_dfa_simulation || this.simulationResult.min_dfa_simulation || this.simulationResult.converted_dfa_simulation || null;
  }

  /**
   * Get total number of steps in active simulation trace
   * @returns {number}
   */
  getMaxSteps() {
    return this.getActiveTrace().length;
  }

  /**
   * Internal playback interval tick
   * @private
   */
  _onTick() {
    const maxSteps = this.getMaxSteps();
    if (this.stepIndex < maxSteps - 1) {
      this.seek(this.stepIndex + 1);
    } else {
      this.pause();
    }
  }

  /**
   * Render all UI elements for a specific step index
   * @private
   */
  _renderStep(stepIndex) {
    const trace = this.getActiveTrace();
    const maxSteps = trace.length;
    const currentStep = trace[stepIndex] || null;

    // 1. Update Scrubber & Step Counter
    if (this.elements.scrubber) {
      this.elements.scrubber.value = String(stepIndex);
    }
    if (this.elements.stepCounter) {
      const totalDisplay = Math.max(0, maxSteps - 1);
      this.elements.stepCounter.textContent = `Step ${stepIndex} / ${totalDisplay}`;
    }

    // 2. Update Input String Tape Visualizer
    this._updateTape(stepIndex, currentStep);

    // 3. Update Canvas Graph Visual Highlighting
    this._updateGraphHighlighting(stepIndex, currentStep, trace);

    // 4. Update Glassmorphic Step Detail Card
    this._updateStepDetails(stepIndex, currentStep, maxSteps);

    // 5. Update Glowing Verdict Card
    this._updateVerdict(stepIndex, maxSteps);

    // 6. Fire optional onStepChanged hook
    if (typeof this.onStepChanged === 'function') {
      try {
        this.onStepChanged(stepIndex, currentStep, this.currentView);
      } catch (err) {
        console.error('[SimulatorPlayer] onStepChanged error:', err);
      }
    }
  }

  /**
   * Render full input string tape cells into #simulation-tape
   * @private
   */
  _renderTape() {
    const container = this.elements.tapeContainer;
    if (!container) return;

    const inputStr = (this.simulationResult && this.simulationResult.input_string !== undefined)
      ? String(this.simulationResult.input_string)
      : '';

    container.innerHTML = '';

    // Handle empty string ε
    if (inputStr === '' || inputStr === 'ε' || inputStr === 'eps') {
      const cell = document.createElement('span');
      cell.className = 'tape-cell tape-empty tape-epsilon active';
      cell.setAttribute('data-tape-index', '0');
      cell.textContent = 'ε';
      cell.title = 'Empty String (ε)';
      container.appendChild(cell);
      return;
    }

    // Render sequential glass pill cells for each character
    for (let i = 0; i < inputStr.length; i++) {
      const char = inputStr[i];
      const cell = document.createElement('span');
      cell.className = 'tape-cell upcoming';
      cell.setAttribute('data-tape-index', String(i));
      cell.textContent = char;
      cell.title = `Symbol [${i}]: '${char}'`;

      // Check for explicit epsilon symbol
      if (char === 'ε' || char === 'e') {
        cell.classList.add('tape-epsilon');
      }

      container.appendChild(cell);
    }
  }

  /**
   * Update active, consumed, and upcoming states of tape cells for current step
   * @private
   */
  _updateTape(stepIndex, currentStep) {
    const container = this.elements.tapeContainer;
    if (!container) return;

    const cells = container.querySelectorAll('.tape-cell');
    if (cells.length === 0) return;

    const inputStr = (this.simulationResult && this.simulationResult.input_string !== undefined)
      ? String(this.simulationResult.input_string)
      : '';

    // Empty string handling
    if (inputStr === '' || inputStr === 'ε' || inputStr === 'eps') {
      cells.forEach(cell => {
        cell.className = 'tape-cell tape-empty tape-epsilon active';
      });
      return;
    }

    // In automata simulation:
    // Step 0 = initial state (before consuming symbols)
    // Step k = state reached after consuming inputStr[k - 1]
    const activeCharIndex = stepIndex > 0 ? (stepIndex - 1) : -1;

    cells.forEach((cell, idx) => {
      cell.classList.remove('active', 'consumed', 'upcoming');

      if (idx < activeCharIndex) {
        cell.classList.add('consumed');
      } else if (idx === activeCharIndex) {
        cell.classList.add('active');
        // Scroll active cell smoothly into view if tape overflows
        try {
          cell.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        } catch (e) {
          // Ignore unsupported scroll options in test environments
        }
      } else {
        cell.classList.add('upcoming');
      }
    });
  }

  /**
   * Coordinate with GraphManager to highlight active states and traversed edges
   * @private
   */
  _updateGraphHighlighting(stepIndex, currentStep, trace) {
    const gm = this.graphManager || (typeof window !== 'undefined' ? window.graphManager : null);
    if (!gm || typeof gm.highlightSimulationStep !== 'function') return;

    if (!currentStep) {
      if (typeof gm.clearHighlights === 'function') gm.clearHighlights();
      return;
    }

    // Target states reached at current step
    const activeStates = currentStep.next_states !== undefined
      ? currentStep.next_states
      : currentStep.current_states;

    let previousStates = [];
    const traversedEdges = [];

    if (stepIndex > 0 && trace[stepIndex - 1]) {
      const prevStep = trace[stepIndex - 1];
      previousStates = prevStep.next_states !== undefined
        ? prevStep.next_states
        : prevStep.current_states;

      const sym = currentStep.symbol_consumed;
      if (sym !== null && sym !== undefined) {
        const fromList = this._normalizeStates(previousStates);
        const toList = this._normalizeStates(activeStates);

        fromList.forEach(fromState => {
          toList.forEach(toState => {
            traversedEdges.push({
              from: fromState,
              to: toState,
              symbol: String(sym)
            });
          });
        });
      }
    }

    try {
      gm.highlightSimulationStep(activeStates, traversedEdges, previousStates);
    } catch (err) {
      console.warn('[SimulatorPlayer] Error in highlightSimulationStep:', err);
    }
  }

  /**
   * Update contents of sleek glassmorphic Step Detail Card (#step-details)
   * @private
   */
  _updateStepDetails(stepIndex, currentStep, maxSteps) {
    const card = this.elements.stepDetails;
    if (!card) return;

    if (!currentStep) {
      card.style.display = 'none';
      return;
    }

    card.style.display = 'flex';

    const infoBadge = card.querySelector('#step-info-badge') || card.querySelector('.step-badge');
    const symbolBadge = card.querySelector('#step-symbol-badge') || card.querySelector('.symbol-badge');
    const statesBadge = card.querySelector('#step-states-badge') || card.querySelector('.states-badge');
    const descText = card.querySelector('#step-description-text') || card.querySelector('.step-description');
    const remText = card.querySelector('#step-remaining-text') || card.querySelector('.step-remaining');
    const modelTag = card.querySelector('#step-model-tag') || card.querySelector('.step-view-tag');

    const totalDisplay = Math.max(0, maxSteps - 1);
    const sym = currentStep.symbol_consumed;
    const activeList = this._normalizeStates(
      currentStep.next_states !== undefined ? currentStep.next_states : currentStep.current_states
    );

    if (infoBadge) {
      infoBadge.textContent = `Step ${stepIndex} / ${totalDisplay}`;
    }

    if (symbolBadge) {
      if (sym !== null && sym !== undefined && sym !== '') {
        symbolBadge.innerHTML = `Consumed: <strong>'${this._escapeHtml(String(sym))}'</strong>`;
        symbolBadge.className = 'symbol-badge symbol-consumed';
      } else {
        symbolBadge.textContent = stepIndex === 0 ? 'Initial State' : 'No Symbol (ε)';
        symbolBadge.className = 'symbol-badge symbol-initial';
      }
    }

    if (statesBadge) {
      statesBadge.innerHTML = `Active: <strong>{ ${activeList.join(', ')} }</strong>`;
    }

    if (descText) {
      descText.textContent = currentStep.description || 'Evaluating transition...';
    }

    if (remText) {
      const rem = currentStep.remaining_input !== undefined && currentStep.remaining_input !== ''
        ? currentStep.remaining_input
        : 'ε';
      remText.innerHTML = `Remaining w: <code>${this._escapeHtml(rem)}</code>`;
    }

    if (modelTag) {
      const modelLabels = {
        'nfa': 'Original NFA',
        'dfa': 'Converted DFA',
        'minimal': 'Minimal DFA'
      };
      modelTag.innerHTML = `Model: <strong>${modelLabels[this.currentView] || 'Minimal DFA'}</strong>`;
    }
  }

  /**
   * Update prominent Glowing Verdict Card on simulation completion
   * @private
   */
  _updateVerdict(stepIndex, maxSteps) {
    const verdictEl = this.elements.verdictContainer;
    if (!verdictEl) return;

    // Display verdict card ONLY when simulation has reached the final step
    if (maxSteps <= 0 || stepIndex < maxSteps - 1) {
      verdictEl.style.display = 'none';
      return;
    }

    const simRes = this.getActiveSimulationResult();
    if (!simRes) {
      verdictEl.style.display = 'none';
      return;
    }

    const isAccepted = Boolean(simRes.accepted);
    const finalStates = this._normalizeStates(simRes.final_states_reached);
    const inputDisplay = simRes.input_string === '' ? 'ε (empty string)' : `"${simRes.input_string}"`;
    const viewLabel = this.currentView === 'nfa' ? 'NFA' : 'Minimal DFA';

    verdictEl.style.display = 'block';
    verdictEl.className = `simulation-verdict-card ${isAccepted ? 'verdict-accepted' : 'verdict-rejected'}`;

    verdictEl.innerHTML = `
      <div class="verdict-banner">
        <div class="verdict-icon">${isAccepted ? '✓' : '✕'}</div>
        <div class="verdict-info">
          <div class="verdict-title">${isAccepted ? 'String Accepted' : 'String Rejected'}</div>
          <div class="verdict-subtitle">
            Input ${this._escapeHtml(inputDisplay)} ${isAccepted ? 'reached accepting state(s)' : 'halted in non-accepting state(s)'}: 
            <strong>{ ${finalStates.join(', ')} }</strong> on ${viewLabel}.
          </div>
        </div>
        <span class="verdict-badge ${isAccepted ? 'badge-accepted' : 'badge-rejected'}">
          ${isAccepted ? 'ACCEPTED' : 'REJECTED'}
        </span>
      </div>
    `;
  }

  /**
   * Update play/pause button state and icon
   * @private
   */
  _updatePlayPauseButtonUI() {
    const el = this.elements;

    if (el.playBtn) {
      if (this.isPlaying) {
        el.playBtn.classList.add('playing');
        el.playBtn.title = 'Pause Simulation (Space)';
        el.playBtn.setAttribute('aria-label', 'Pause Simulation');
      } else {
        el.playBtn.classList.remove('playing');
        el.playBtn.title = 'Play Simulation (Space)';
        el.playBtn.setAttribute('aria-label', 'Play Simulation');
      }
    }

    // Toggle icon
    if (el.playIcon) {
      el.playIcon.textContent = this.isPlaying ? '⏸' : '▶';
    } else if (el.playBtn) {
      const iconSpan = el.playBtn.querySelector('.ctrl-icon');
      if (iconSpan) {
        iconSpan.textContent = this.isPlaying ? '⏸' : '▶';
      }
    }

    // Secondary discrete pause button support
    if (el.pauseBtn) {
      el.pauseBtn.style.display = this.isPlaying ? 'inline-flex' : 'none';
    }
  }

  /**
   * Normalize view string to 'nfa' | 'dfa' | 'minimal'
   * @private
   */
  _normalizeView(view) {
    if (!view) return 'minimal';
    const v = String(view).toLowerCase();
    if (v.includes('nfa')) return 'nfa';
    if (v.includes('min')) return 'minimal';
    if (v.includes('dfa')) return 'dfa';
    return 'minimal';
  }

  /**
   * Normalize state value to Array<string>
   * @private
   */
  _normalizeStates(states) {
    if (!states) return [];
    if (typeof states === 'string') return [states];
    if (Array.isArray(states)) return states.map(String);
    if (states instanceof Set) return Array.from(states).map(String);
    return [];
  }

  /**
   * Sanitize HTML text to prevent XSS injection
   * @private
   */
  _escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, m => map[m]);
  }
}

// Attach SimulatorPlayer to window for global access across app.js and script execution
if (typeof window !== 'undefined') {
  window.SimulatorPlayer = SimulatorPlayer;
}

// Support CommonJS / Node.js testing environments
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SimulatorPlayer;
}
