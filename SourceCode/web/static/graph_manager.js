/**
 * GraphManager - Interactive Cytoscape.js & Dagre Automata Visualization Architecture
 * 
 * Provides:
 * - Directed graph layout wrapper with Dagre rankDir 'LR'
 * - Dark glassmorphic theme styling (circular nodes, double-ring accept states, emerald start marker)
 * - Multi-edges (Bézier curves) and self-loops with legible symbol labels
 * - Interactive node dragging, panning, zooming, auto-fit, and relayout
 * - High-resolution PNG (3x scale) and vector SVG exports
 * - Simulation step state neon glows and edge traversal animation pulses
 * - Smooth animated topology morphing between NFA, DFA, and Minimized DFA
 *
 * Course: CSET302 - Automata Theory & Computability
 */

class GraphManager {
  /**
   * @param {string|HTMLElement} container - DOM ID or container element (default: 'canvas')
   * @param {Object} [options] - Configuration overrides
   */
  constructor(container = 'canvas', options = {}) {
    this.container = (typeof document !== 'undefined' && typeof container === 'string')
      ? document.getElementById(container)
      : container;
    this.containerId = typeof container === 'string' ? container : (container && container.id) || 'canvas';
    this.options = Object.assign({
      theme: 'dark',
      animationDuration: 550,
      combineParallelEdges: true,
      showStartMarker: true,
      bg: '#090d16'
    }, options);

    this.cy = null;
    this.currentAutomaton = null;
    this.currentViewType = 'nfa'; // 'nfa' | 'dfa' | 'minimal' | 'minimal_dfa'
    this.isInitialized = false;
  }

  /**
   * Initialize Cytoscape core instance and viewport bindings
   */
  init() {
    if (this.isInitialized && this.cy) {
      return this;
    }

    if (typeof cytoscape === 'undefined') {
      console.error('[GraphManager] Cytoscape.js is not loaded.');
      return this;
    }

    if (!this.container) {
      this.container = document.getElementById(this.containerId) || document.getElementById('canvas') || document.getElementById('cy-container');
    }

    if (!this.container) {
      console.warn(`[GraphManager] Container #${this.containerId} not found in DOM.`);
      return this;
    }

    // Ensure container has relative/absolute positioning
    const computedStyle = window.getComputedStyle ? window.getComputedStyle(this.container) : this.container.style;
    if (computedStyle && computedStyle.position === 'static') {
      this.container.style.position = 'relative';
    }

    // Hide ambient placeholder if present
    const placeholder = this.container.querySelector('.canvas-ambient-placeholder');
    if (placeholder) {
      placeholder.style.display = 'none';
    }

    // Register cytoscape-svg if loaded after cytoscape
    if (typeof cytoscapeSvg !== 'undefined' && typeof cytoscape.use === 'function') {
      try {
        cytoscape.use(cytoscapeSvg);
      } catch (e) {
        // Already registered or handled
      }
    }

    // Initialize Cytoscape core
    this.cy = cytoscape({
      container: this.container,
      elements: [],
      style: this._getStylesheet(),
      layout: { name: 'preset' },
      boxSelectionEnabled: false,
      autoungrabify: false,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      wheelSensitivity: 0.28,
      minZoom: 0.15,
      maxZoom: 3.5
    });

    // Handle container resize
    window.addEventListener('resize', () => {
      if (this.cy) this.cy.resize();
    });

    // Double-click to auto-fit
    this.cy.on('dblclick', () => {
      this.fit();
    });

    this.isInitialized = true;
    return this;
  }

  /**
   * Automatically bind UI export and manipulation buttons in index.html
   */
  bindControls() {
    const btnPng = document.getElementById('btn-export-png');
    if (btnPng) {
      btnPng.onclick = () => this.exportImage('png');
    }

    const btnSvg = document.getElementById('btn-export-svg');
    if (btnSvg) {
      btnSvg.onclick = () => this.exportImage('svg');
    }

    const btnRelayout = document.getElementById('tool-relayout');
    if (btnRelayout) {
      btnRelayout.onclick = () => this.runLayout('dagre');
    }

    const btnFit = document.getElementById('tool-zoom-fit');
    if (btnFit) {
      btnFit.onclick = () => this.fit();
    }

    return this;
  }

  /**
   * Load and render an automaton (NFA, DFA, or Minimal DFA) with smooth layout morphing
   * @param {Object} automaton - Normalized automaton object with states, alphabet, start_state, final_states, transitions
   * @param {string} [viewType='nfa'] - 'nfa' | 'dfa' | 'minimal'
   * @param {Object} [options] - Layout & transition overrides
   */
  loadAutomaton(automaton, viewType = 'nfa', options = {}) {
    if (!this.isInitialized) {
      this.init();
    }
    if (!this.cy || !automaton) return;

    this.currentAutomaton = automaton;
    this.currentViewType = viewType;

    // Hide ambient placeholder once an automaton is loaded
    if (this.container) {
      const placeholder = this.container.querySelector('.canvas-ambient-placeholder');
      if (placeholder) {
        placeholder.style.display = 'none';
      }
    }

    // 1. Capture existing node positions to prevent (0,0) pop-in flicker
    const oldPositions = {};
    this.cy.nodes().forEach(node => {
      oldPositions[node.id()] = Object.assign({}, node.position());
    });

    // Calculate canvas center
    const extent = typeof this.cy.extent === 'function' ? this.cy.extent() : null;
    const center = extent ? {
      x: (extent.x1 + extent.x2) / 2 || 250,
      y: (extent.y1 + extent.y2) / 2 || 220
    } : { x: 250, y: 220 };

    // 2. Build new elements
    const elements = this._buildCytoscapeElements(automaton, oldPositions, center);

    // Stop ongoing animations and reset highlights
    this.cy.stop();
    this.clearHighlights();

    // 3. Batch atomic element replacement
    this.cy.batch(() => {
      this.cy.elements().remove();
      this.cy.add(elements);
    });

    // 4. Run animated Dagre layout with smooth cubic-bezier easing
    this.runLayout('dagre', Object.assign({
      animate: options.animate !== false,
      duration: options.duration || this.options.animationDuration
    }, options));
  }

  /**
   * Transform automaton specification into Cytoscape nodes and edges
   * Normalizes transition targets: handles both array (NFA) and string (DFA) formats
   */
  _buildCytoscapeElements(automaton, oldPositions = {}, center = { x: 250, y: 220 }) {
    const elements = [];
    const states = automaton.states || [];
    const stateIdSet = new Set(states.map(String));
    const startState = automaton.start_state !== undefined && automaton.start_state !== null ? String(automaton.start_state) : '';
    const finalStates = new Set((automaton.final_states || []).map(String));
    const transitions = automaton.transitions || [];

    // 1. Start marker dummy node and directed entry arrow
    if (this.options.showStartMarker && startState && stateIdSet.has(startState)) {
      const startPos = oldPositions['__start__'] || { x: center.x - 120, y: center.y };
      elements.push({
        group: 'nodes',
        data: {
          id: '__start__',
          label: '',
          fontSize: '10px'
        },
        position: startPos,
        classes: 'start-marker-node start-indicator'
      });

      elements.push({
        group: 'edges',
        data: {
          id: '__start__arrow',
          source: '__start__',
          target: startState,
          label: 'start'
        },
        classes: 'start-marker-edge start-indicator-edge'
      });
    }

    // 2. State nodes
    states.forEach((st, idx) => {
      const stateId = String(st);
      const isStart = stateId === startState;
      const isFinal = finalStates.has(stateId);

      const classes = ['state-node'];
      if (isStart) classes.push('start-state');
      if (isFinal) {
        classes.push('accept-state');
        classes.push('accept');
        classes.push('final');
      }

      // Check for trap/dead state conventions
      const lower = stateId.toLowerCase();
      if (lower === 'dead' || lower === 'trap' || lower === '∅' || lower === '{empty}' || lower === '{}') {
        classes.push('trap');
        classes.push('dead');
      }

      // Dynamic font size scaling for composite subset labels (e.g., {q0, q1, q2})
      let fontSize = '13px';
      if (stateId.length > 12) fontSize = '9.5px';
      else if (stateId.length > 7) fontSize = '11px';

      // Preserve previous position or spawn near center
      const initialPos = oldPositions[stateId] || {
        x: center.x + (idx - states.length / 2) * 40,
        y: center.y + ((idx % 2 === 0 ? 1 : -1) * 30)
      };

      elements.push({
        group: 'nodes',
        data: {
          id: stateId,
          label: stateId,
          fontSize: fontSize
        },
        position: initialPos,
        classes: classes.join(' ')
      });
    });

    // 3. Directed transitions & parallel edge grouping
    if (this.options.combineParallelEdges) {
      const edgeMap = new Map();

      transitions.forEach(t => {
        if (!t || t.from === undefined || t.from === null) return;
        const from = String(t.from);
        if (!stateIdSet.has(from)) return;

        const rawSym = t.symbol;
        const sym = (rawSym === '' || rawSym === 'eps' || rawSym === 'epsilon' || rawSym === 'e') ? 'ε' : String(rawSym);
        
        // Robust normalization: handles both Array<string> (NFA) and string (DFA)
        const targets = Array.isArray(t.to) 
          ? t.to.map(String) 
          : (t.to !== undefined && t.to !== null ? [String(t.to)] : []);

        targets.forEach(to => {
          if (!stateIdSet.has(to)) return;
          const key = `${from}-->${to}`;
          if (!edgeMap.has(key)) {
            edgeMap.set(key, { from, to, symbols: [] });
          }
          const entry = edgeMap.get(key);
          if (!entry.symbols.includes(sym)) {
            entry.symbols.push(sym);
          }
        });
      });

      edgeMap.forEach(entry => {
        const isSelfLoop = entry.from === entry.to;
        const edgeId = `e_${entry.from}_${entry.to}`;
        const label = entry.symbols.join(', ');

        const classes = ['transition-edge'];
        if (isSelfLoop) classes.push('self-loop');

        elements.push({
          group: 'edges',
          data: {
            id: edgeId,
            source: entry.from,
            target: entry.to,
            label: label,
            symbols: entry.symbols
          },
          classes: classes.join(' ')
        });
      });
    } else {
      let edgeCounter = 0;
      transitions.forEach(t => {
        if (!t || t.from === undefined || t.from === null) return;
        const from = String(t.from);
        if (!stateIdSet.has(from)) return;

        const rawSym = t.symbol;
        const sym = (rawSym === '' || rawSym === 'eps' || rawSym === 'epsilon' || rawSym === 'e') ? 'ε' : String(rawSym);
        const targets = Array.isArray(t.to) 
          ? t.to.map(String) 
          : (t.to !== undefined && t.to !== null ? [String(t.to)] : []);

        targets.forEach(to => {
          if (!stateIdSet.has(to)) return;
          const isSelfLoop = from === to;
          const edgeId = `e_${from}_${to}_${edgeCounter++}`;
          const classes = ['transition-edge'];
          if (isSelfLoop) classes.push('self-loop');

          elements.push({
            group: 'edges',
            data: {
              id: edgeId,
              source: from,
              target: to,
              label: sym,
              symbols: [sym]
            },
            classes: classes.join(' ')
          });
        });
      });
    }

    return elements;
  }

  /**
   * Run Dagre directed layout (or fallback to breadthfirst if dagre is missing)
   * @param {string} [layoutName='dagre'] - Layout algorithm name
   * @param {Object} [customOptions={}] - Custom options overrides
   */
  runLayout(layoutName = 'dagre', customOptions = {}) {
    if (!this.cy) return;

    let hasDagre = false;
    try {
      hasDagre = typeof cytoscape === 'function' && cytoscape('layout', 'dagre') !== undefined;
    } catch (e) {
      hasDagre = false;
    }

    const chosenName = (layoutName === 'dagre' && hasDagre) ? 'dagre' : (hasDagre ? layoutName : 'breadthfirst');

    const layout = this.cy.layout(Object.assign({
      name: chosenName,
      rankDir: 'LR',
      nodeSep: 60,
      rankSep: 85,
      edgeSep: 30,
      padding: 45,
      fit: true,
      animate: customOptions.animate !== false,
      animationDuration: customOptions.duration || this.options.animationDuration,
      animationEasing: 'cubic-bezier(0.16, 1, 0.3, 1)',
      nodeDimensionsIncludeLabels: true
    }, customOptions));

    layout.run();
  }

  /**
   * Fit graph to canvas viewport with easing animation
   * @param {number} [padding=45] - Viewport padding in pixels
   */
  fit(padding = 45) {
    if (!this.cy) return;
    this.cy.animate({
      fit: {
        eles: this.cy.elements(),
        padding: padding
      },
      duration: 350,
      easing: 'cubic-bezier(0.16, 1, 0.3, 1)'
    });
  }

  /**
   * Highlight simulation step with glowing states and pulsing edges
   * @param {Array<string>|Set<string>|string} activeStates - Active state ID(s)
   * @param {Array<Object>|Array<string>} [traversedEdges=[]] - Traversed edge IDs or {from, to, symbol} descriptors
   * @param {Array<string>|Set<string>|string} [previousStates=[]] - Previous step state ID(s)
   */
  highlightSimulationStep(activeStates = [], traversedEdges = [], previousStates = []) {
    if (!this.cy) return;

    const activeList = this._normalizeStateList(activeStates);
    const prevList = this._normalizeStateList(previousStates);

    this.cy.batch(() => {
      // 1. Reset highlights
      this.clearHighlights();

      // 2. Mark previous states (violet trail aura)
      prevList.forEach(id => {
        const node = this.cy.getElementById(id);
        if (node && node.nonempty()) {
          node.addClass('previous-state sim-previous');
        }
      });

      // 3. Mark active states (cyan neon aura or emerald double-ring aura)
      const activeNodes = [];
      activeList.forEach(id => {
        const node = this.cy.getElementById(id);
        if (node && node.nonempty()) {
          const isAccept = node.hasClass('accept-state') || node.hasClass('accept') || node.hasClass('final');
          if (isAccept) {
            node.addClass('active-accept-state sim-active-accept');
          } else {
            node.addClass('active-state sim-active');
          }
          activeNodes.push(node);
        }
      });

      // 4. Mark traversed edges
      const matchedEdges = this._resolveTraversedEdges(traversedEdges, prevList, activeList);
      matchedEdges.forEach(edge => {
        edge.addClass('traversed-edge edge-pulse sim-traversed');
        const label = edge.data('label') || '';
        if (label.includes('ε') || label.includes('e')) {
          edge.addClass('sim-epsilon');
        }
      });

      // 5. Trigger spring pulse animation on traversed edges
      matchedEdges.forEach(edge => {
        edge.animate({
          style: { 'width': 5.5, 'underlay-padding': 9, 'underlay-opacity': 0.7 }
        }, {
          duration: 180,
          complete: () => {
            edge.animate({
              style: { 'width': 4.5, 'underlay-padding': 6, 'underlay-opacity': 0.45 }
            }, { duration: 220 });
          }
        });
      });

      // 6. Trigger spring pulse animation on active nodes
      activeNodes.forEach(node => {
        const isAccept = node.hasClass('active-accept-state') || node.hasClass('sim-active-accept');
        const targetPadding = isAccept ? 18 : 15;
        const basePadding = isAccept ? 15 : 12;
        node.animate({
          style: { 'underlay-padding': targetPadding, 'underlay-opacity': 0.8 }
        }, {
          duration: 200,
          complete: () => {
            node.animate({
              style: { 'underlay-padding': basePadding, 'underlay-opacity': isAccept ? 0.65 : 0.55 }
            }, { duration: 250 });
          }
        });
      });
    });
  }

  /**
   * Clear all simulation glows and traversal pulses
   */
  clearHighlights() {
    if (!this.cy) return;
    this.cy.batch(() => {
      this.cy.elements().removeClass(
        'active-state active-accept-state traversed-edge edge-pulse previous-state ' +
        'sim-active sim-active-accept sim-previous sim-traversed sim-epsilon'
      );
    });
  }

  /**
   * Normalize state parameter to Array<string>
   * @private
   */
  _normalizeStateList(states) {
    if (!states) return [];
    if (typeof states === 'string') return [states];
    if (Array.isArray(states)) return states.map(s => String(s));
    if (states instanceof Set) return Array.from(states).map(s => String(s));
    return [];
  }

  /**
   * Resolve traversed edges from explicit IDs, descriptors, or endpoint inference
   * @private
   */
  _resolveTraversedEdges(traversedEdges, prevList, activeList) {
    const matched = [];
    const list = Array.isArray(traversedEdges) ? traversedEdges : (traversedEdges ? [traversedEdges] : []);

    if (list.length > 0) {
      list.forEach(item => {
        if (typeof item === 'string') {
          const edge = this.cy.getElementById(item);
          if (edge && edge.nonempty()) matched.push(edge);
        } else if (item && typeof item === 'object') {
          const from = String(item.from || item.source || '');
          const to = String(item.to || item.target || '');
          const sym = item.symbol !== undefined ? String(item.symbol) : null;

          this.cy.edges().forEach(edge => {
            if (edge.data('source') === from && edge.data('target') === to) {
              if (sym === null) {
                matched.push(edge);
              } else {
                const symbols = edge.data('symbols');
                const label = edge.data('label') || '';
                if ((Array.isArray(symbols) && symbols.includes(sym)) || label.includes(sym)) {
                  matched.push(edge);
                }
              }
            }
          });
        }
      });
    }

    // Automatic fallback: match edges between previous and active states
    if (matched.length === 0 && prevList.length > 0 && activeList.length > 0) {
      this.cy.edges().forEach(edge => {
        if (prevList.includes(edge.data('source')) && activeList.includes(edge.data('target'))) {
          matched.push(edge);
        }
      });
    }

    return matched;
  }

  /**
   * Export high-resolution PNG or vector SVG image
   * @param {'png'|'svg'} [format='png'] - Export format
   * @param {string} [customName=null] - Base filename override
   * @returns {string|Blob|null}
   */
  exportImage(format = 'png', customName = null) {
    if (!this.cy || this.cy.elements().length === 0) {
      this._notify('No automaton graph to export', 'warning');
      return null;
    }

    const cleanFormat = String(format).toLowerCase();
    const filename = customName || this._getExportFilename(cleanFormat);

    if (cleanFormat === 'svg') {
      return this.exportSVG(filename);
    } else {
      return this.exportPNG(filename);
    }
  }

  /**
   * Export crisp 3x scale PNG and trigger file download
   * @param {string} [filename] - Target filename
   * @returns {Blob|string|null}
   */
  exportPNG(filename) {
    if (!this.cy) return null;
    const targetFilename = filename || this._getExportFilename('png');

    try {
      // 1. Try Blob output (avoids URI length limitations on big graphs)
      let blob = null;
      try {
        blob = this.cy.png({
          full: true,
          scale: 3,
          bg: this.options.bg,
          output: 'blob'
        });
      } catch (e) {
        blob = null;
      }

      if (blob instanceof Blob) {
        this._triggerBlobDownload(blob, targetFilename);
        this._notify(`Exported High-Resolution PNG (3x): ${targetFilename}`, 'success');
        return blob;
      }

      // 2. Base64 URI fallback
      const dataUri = this.cy.png({
        full: true,
        scale: 3,
        bg: this.options.bg,
        output: 'base64uri'
      });

      this._triggerDataUrlDownload(dataUri, targetFilename);
      this._notify(`Exported High-Resolution PNG (3x): ${targetFilename}`, 'success');
      return dataUri;
    } catch (err) {
      console.error('[GraphManager] PNG export error:', err);
      this._notify(`PNG Export failed: ${err.message}`, 'error');
      return null;
    }
  }

  /**
   * Export vector SVG and trigger file download
   * @param {string} [filename] - Target filename
   * @returns {string|null}
   */
  exportSVG(filename) {
    if (!this.cy) return null;
    const targetFilename = filename || this._getExportFilename('svg');

    if (typeof this.cy.svg !== 'function') {
      console.warn('[GraphManager] cytoscape-svg plugin is not available. Falling back to PNG export.');
      this._notify('Vector SVG plugin not loaded, falling back to 3x PNG', 'warning');
      return this.exportPNG(targetFilename.replace(/\.svg$/, '.png'));
    }

    try {
      const svgString = this.cy.svg({
        full: true,
        scale: 1,
        bg: this.options.bg
      });

      const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
      this._triggerBlobDownload(blob, targetFilename);
      this._notify(`Exported Vector SVG: ${targetFilename}`, 'success');
      return svgString;
    } catch (err) {
      console.error('[GraphManager] SVG export error:', err);
      this._notify(`SVG Export failed: ${err.message}`, 'error');
      return null;
    }
  }

  /**
   * Helper to compute sanitized export filename: <automaton_name>_<viewType>.<ext>
   * @private
   */
  _getExportFilename(ext) {
    const rawName = (this.currentAutomaton && this.currentAutomaton.name) || 'automaton';
    const cleanName = rawName.replace(/[^a-zA-Z0-9_-]/g, '_');
    const rawView = this.currentViewType || 'graph';
    const cleanView = rawView.toLowerCase().replace(/[^a-zA-Z0-9_-]/g, '_');
    return `${cleanName}_${cleanView}.${ext}`;
  }

  /**
   * Trigger native browser file download from Blob
   * @private
   */
  _triggerBlobDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.style.display = 'none';
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  /**
   * Trigger native browser file download from Data URL
   * @private
   */
  _triggerDataUrlDownload(dataUrl, filename) {
    const link = document.createElement('a');
    link.style.display = 'none';
    link.href = dataUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  /**
   * Notification / Toast helper
   * @private
   */
  _notify(message, type = 'info') {
    if (typeof window !== 'undefined' && typeof window.showToast === 'function') {
      window.showToast(message, type);
    } else {
      console.log(`[GraphManager ${type.toUpperCase()}] ${message}`);
    }
  }

  /**
   * Dark Glassmorphic Cytoscape Stylesheet Specification
   * Supports native canvas underlay-* neon halos and double border concentric rings
   * @private
   */
  _getStylesheet() {
    return [
      // 1. Base State Node: Dark Glassmorphic Pill with Cyan Accent
      {
        selector: 'node.state-node, node',
        style: {
          'shape': 'ellipse',
          'width': 52,
          'height': 52,
          'background-color': '#0d1527',
          'background-opacity': 0.92,
          'border-width': 2.5,
          'border-color': '#06b6d4', // Cyan neon border
          'border-opacity': 0.95,
          'label': 'data(label)',
          'color': '#f1f5f9',
          'font-family': 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          'font-size': 'data(fontSize)',
          'font-weight': 'bold',
          'text-valign': 'center',
          'text-halign': 'center',
          'text-outline-color': '#090d16',
          'text-outline-width': 1.5,
          'text-outline-opacity': 0.9,
          'underlay-color': '#06b6d4',
          'underlay-padding': 0,
          'underlay-opacity': 0,
          'underlay-shape': 'ellipse',
          'transition-property': 'background-color, border-color, border-width, underlay-opacity, underlay-padding, line-color, target-arrow-color, width',
          'transition-duration': '0.25s'
        }
      },

      // 2. Start State: Emerald Neon Border
      {
        selector: 'node.start-state',
        style: {
          'border-color': '#10b981', // Emerald neon
          'border-width': 3.5,
          'background-color': 'rgba(16, 185, 129, 0.15)',
          'underlay-color': '#10b981',
          'underlay-padding': 4,
          'underlay-opacity': 0.25
        }
      },

      // 3. Accept / Final State: Concentric Double Ring
      {
        selector: 'node.accept-state, node.accept, node.final',
        style: {
          'border-style': 'double',
          'border-width': 7,
          'border-color': '#8b5cf6', // Violet neon
          'background-color': 'rgba(139, 92, 246, 0.18)',
          'underlay-color': '#8b5cf6',
          'underlay-padding': 4,
          'underlay-opacity': 0.25
        }
      },

      // 4. Combined Start & Accept State
      {
        selector: 'node.start-state.accept-state, node.start-state.accept, node.start-state.final',
        style: {
          'border-style': 'double',
          'border-width': 7,
          'border-color': '#10b981', // Emerald start priority
          'background-color': 'rgba(16, 185, 129, 0.22)',
          'underlay-color': '#10b981',
          'underlay-padding': 6,
          'underlay-opacity': 0.35
        }
      },

      // 5. Trap / Dead State
      {
        selector: 'node.trap, node.dead',
        style: {
          'border-color': '#64748b',
          'border-style': 'dashed',
          'background-color': 'rgba(30, 41, 59, 0.5)',
          'color': '#94a3b8'
        }
      },

      // 6. Start Marker Phantom Node (invisible anchor)
      {
        selector: 'node.start-marker-node, node.start-indicator',
        style: {
          'width': 1,
          'height': 1,
          'opacity': 0,
          'events': 'no'
        }
      },

      // 7. Start Marker Directed Entry Arrow
      {
        selector: 'edge.start-marker-edge, edge.start-indicator-edge',
        style: {
          'width': 2.5,
          'line-color': '#10b981',
          'target-arrow-shape': 'triangle',
          'target-arrow-color': '#10b981',
          'arrow-scale': 1.3,
          'curve-style': 'straight',
          'label': 'start',
          'color': '#10b981',
          'font-family': 'Inter, system-ui, sans-serif',
          'font-size': '11px',
          'font-weight': 'bold',
          'text-background-color': '#090d16',
          'text-background-opacity': 0.94,
          'text-background-padding': 3,
          'text-background-shape': 'roundrectangle',
          'text-margin-y': -8,
          'events': 'no'
        }
      },

      // 8. Directed Transition Edges: Bézier multi-edges
      {
        selector: 'edge.transition-edge, edge',
        style: {
          'curve-style': 'bezier',
          'target-arrow-shape': 'triangle',
          'target-arrow-color': '#38bdf8',
          'arrow-scale': 1.2,
          'line-color': 'rgba(71, 85, 105, 0.75)',
          'width': 2.2,
          'label': 'data(label)',
          'color': '#7dd3fc',
          'font-family': '"JetBrains Mono", Consolas, monospace',
          'font-size': '12px',
          'font-weight': 'bold',
          'text-background-color': '#090d16',
          'text-background-opacity': 0.94,
          'text-background-padding': 3.5,
          'text-background-shape': 'roundrectangle',
          'text-border-color': 'rgba(56, 189, 248, 0.35)',
          'text-border-width': 1,
          'text-border-opacity': 0.8,
          'text-rotation': 'autorotate',
          'text-margin-y': -8,
          'transition-property': 'line-color, target-arrow-color, width, underlay-opacity, underlay-padding',
          'transition-duration': '0.25s'
        }
      },

      // 9. Self-Loops
      {
        selector: 'edge.self-loop, edge:loop',
        style: {
          'loop-direction': '-45deg',
          'loop-sweep': '-90deg',
          'control-point-step-size': 45,
          'text-margin-y': -10
        }
      },

      // 10. Interactive User Selection & Hover
      {
        selector: 'node:selected, node:grabbed',
        style: {
          'border-color': '#22d3ee',
          'border-width': 3.5,
          'underlay-color': '#06b6d4',
          'underlay-padding': 8,
          'underlay-opacity': 0.45
        }
      },
      {
        selector: 'edge:selected',
        style: {
          'line-color': '#06b6d4',
          'target-arrow-color': '#06b6d4',
          'width': 3.2
        }
      },

      // ----------------------------------------------------
      // Simulation Highlighting (Underlay Neon Glow)
      // ----------------------------------------------------
      {
        selector: 'node.active-state, node.sim-active',
        style: {
          'background-color': '#0284c7',
          'border-color': '#38bdf8',
          'border-width': 4,
          'color': '#ffffff',
          'underlay-color': '#06b6d4',
          'underlay-padding': 12,
          'underlay-opacity': 0.55,
          'underlay-shape': 'ellipse',
          'z-index': 999
        }
      },
      {
        selector: 'node.active-accept-state, node.sim-active-accept',
        style: {
          'background-color': '#059669',
          'border-color': '#34d399',
          'border-width': 7,
          'border-style': 'double',
          'color': '#ffffff',
          'underlay-color': '#10b981',
          'underlay-padding': 15,
          'underlay-opacity': 0.65,
          'underlay-shape': 'ellipse',
          'z-index': 999
        }
      },
      {
        selector: 'node.previous-state, node.sim-previous',
        style: {
          'border-color': '#8b5cf6',
          'border-width': 3,
          'background-color': 'rgba(139, 92, 246, 0.22)',
          'underlay-color': '#8b5cf6',
          'underlay-padding': 8,
          'underlay-opacity': 0.35,
          'underlay-shape': 'ellipse'
        }
      },
      {
        selector: 'edge.traversed-edge, edge.sim-traversed',
        style: {
          'line-color': '#f59e0b',
          'target-arrow-color': '#f59e0b',
          'width': 4.5,
          'color': '#fbbf24',
          'text-border-color': '#f59e0b',
          'underlay-color': '#f59e0b',
          'underlay-padding': 6,
          'underlay-opacity': 0.45,
          'z-index': 999
        }
      },
      {
        selector: 'edge.sim-epsilon',
        style: {
          'line-color': '#8b5cf6',
          'target-arrow-color': '#8b5cf6',
          'line-style': 'dashed',
          'underlay-color': '#8b5cf6'
        }
      }
    ];
  }
}

// Attach GraphManager to window for global access across app.js and playback modules
if (typeof window !== 'undefined') {
  window.GraphManager = GraphManager;
}

// Support CommonJS / Node.js testing environments
if (typeof module !== 'undefined' && module.exports) {
  module.exports = GraphManager;
}
