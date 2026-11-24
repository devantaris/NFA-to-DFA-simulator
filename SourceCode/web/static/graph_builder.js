// =============================================================================
// CSET302 Automata Theory Simulator — Milestone 5: Visual Graph Builder
// Interactive Canvas State & Transition Editing, Popovers, Hotkeys, Two-Way Sync
// =============================================================================

class GraphBuilder {
  /**
   * @param {Object} options Configuration options
   * @param {GraphManager} [options.graphManager] Active GraphManager instance
   * @param {string} [options.jsonEditorId='nfa-json'] Textarea ID for NFA JSON
   * @param {string} [options.sampleSelectId='sample-select'] Preset selector ID
   * @param {Function} [options.onModelChanged] Callback invoked when model is serialized
   */
  constructor(options = {}) {
    this.graphManager = options.graphManager || (typeof window !== 'undefined' ? window.graphManager : null);
    this.jsonEditorId = options.jsonEditorId || 'nfa-json';
    this.sampleSelectId = options.sampleSelectId || 'sample-select';
    this.onModelChanged = options.onModelChanged || null;

    this.currentMode = 'select'; // 'select' | 'add-state' | 'add-transition'
    this.transitionSourceNode = null;
    this.isSyncing = false;
    this.popoverElement = null;
    this.isInitialized = false;
    this._debounceTimer = null;
  }

  get cy() {
    return this.graphManager ? this.graphManager.cy : (typeof window !== 'undefined' && window.graphManager ? window.graphManager.cy : null);
  }

  get jsonEditor() {
    return document.getElementById(this.jsonEditorId);
  }

  get sampleSelect() {
    return document.getElementById(this.sampleSelectId);
  }

  /**
   * Initialize toolbar bindings, canvas listeners, hotkeys, and popover markup
   */
  init() {
    if (this.isInitialized) return this;

    this._createPopoverDOM();
    this._attachToolbarListeners();
    this._attachCanvasListeners();
    this._setupKeyboardShortcuts();
    this._injectStyles();
    this._setupEditorSync();

    this.isInitialized = true;
    return this;
  }

  /**
   * Switch interaction mode: 'select' | 'add-state' | 'add-transition'
   * @param {string} mode
   */
  setMode(mode) {
    if (this.transitionSourceNode) {
      this.transitionSourceNode.removeClass('transition-source');
      this.transitionSourceNode = null;
    }
    this.hidePopover();

    // Pause simulation if running so user edits don't clash with playback
    if (typeof window !== 'undefined' && window.simulatorPlayer && typeof window.simulatorPlayer.pause === 'function') {
      window.simulatorPlayer.pause();
    }

    this.currentMode = mode;

    // Update toolbar button active states
    const btnSelect = document.getElementById('tool-select');
    const btnAddState = document.getElementById('tool-add-state');
    const btnAddTransition = document.getElementById('tool-add-transition');

    if (btnSelect) btnSelect.classList.toggle('active', mode === 'select');
    if (btnAddState) btnAddState.classList.toggle('active', mode === 'add-state');
    if (btnAddTransition) btnAddTransition.classList.toggle('active', mode === 'add-transition');

    // Update canvas cursor class
    const canvasContainer = document.getElementById('canvas') || document.getElementById('cy-container');
    if (canvasContainer) {
      canvasContainer.classList.toggle('mode-add-state', mode === 'add-state');
      canvasContainer.classList.toggle('mode-add-transition', mode === 'add-transition');
    }

    // Unselect edges and nodes when changing modes
    if (this.cy) {
      this.cy.$(':selected').unselect();
    }

    if (typeof showToast === 'function') {
      if (mode === 'add-state') {
        showToast('Add State: click canvas to place state', 'info');
      } else if (mode === 'add-transition') {
        showToast('Add Transition: click source state, then target state', 'info');
      }
    }
  }

  /**
   * Attach event listeners to Visual Graph Builder toolbar buttons
   */
  _attachToolbarListeners() {
    const btnSelect = document.getElementById('tool-select');
    if (btnSelect) {
      btnSelect.addEventListener('click', () => this.setMode('select'));
    }

    const btnAddState = document.getElementById('tool-add-state');
    if (btnAddState) {
      btnAddState.addEventListener('click', () => this.setMode('add-state'));
    }

    const btnAddTransition = document.getElementById('tool-add-transition');
    if (btnAddTransition) {
      btnAddTransition.addEventListener('click', () => this.setMode('add-transition'));
    }

    const btnToggleStart = document.getElementById('tool-toggle-start');
    if (btnToggleStart) {
      btnToggleStart.addEventListener('click', () => this.toggleStartState());
    }

    const btnToggleAccept = document.getElementById('tool-toggle-accept');
    if (btnToggleAccept) {
      btnToggleAccept.addEventListener('click', () => this.toggleAcceptState());
    }

    const btnDelete = document.getElementById('tool-delete');
    if (btnDelete) {
      btnDelete.addEventListener('click', () => this.deleteSelected());
    }
  }

  /**
   * Attach Cytoscape canvas event handlers for tapping, hovering, and connecting
   */
  _attachCanvasListeners() {
    const cy = this.cy;
    if (!cy) return;

    // Canvas background tap
    cy.on('tap', (evt) => {
      // If clicking background
      if (evt.target === cy) {
        if (this.currentMode === 'add-state') {
          const pos = evt.position || { x: 200, y: 200 };
          this.addStateAt(pos.x, pos.y);
        } else if (this.currentMode === 'add-transition') {
          if (this.transitionSourceNode) {
            this.transitionSourceNode.removeClass('transition-source');
            this.transitionSourceNode = null;
          }
        }
        this.hidePopover();
      }
    });

    // Node tap
    cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      if (node.id() === '__start__') return; // Ignore start dummy anchor

      if (this.currentMode === 'add-transition') {
        evt.originalEvent?.stopPropagation?.();
        if (!this.transitionSourceNode) {
          // Select source state
          this.transitionSourceNode = node;
          node.addClass('transition-source');
          if (typeof showToast === 'function') {
            showToast(`Source state "${node.id()}" selected. Now click target state.`, 'info');
          }
        } else {
          // Connect to target state
          const sourceNode = this.transitionSourceNode;
          const targetNode = node;
          sourceNode.removeClass('transition-source');
          this.transitionSourceNode = null;

          this.openTransitionPopover(sourceNode, targetNode);
        }
      }
    });

    // Hover candidate target highlight when in add-transition mode
    cy.on('mouseover', 'node', (evt) => {
      if (this.currentMode === 'add-transition' && this.transitionSourceNode) {
        if (evt.target.id() !== '__start__') {
          evt.target.addClass('candidate-target');
        }
      }
    });

    cy.on('mouseout', 'node', (evt) => {
      evt.target.removeClass('candidate-target');
    });
  }

  /**
   * Keyboard shortcuts with bulletproof input and modifier guarding
   */
  _setupKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      // 1. Guard against modifier keys (Ctrl+C, Ctrl+V, Alt+Tab, Cmd+...)
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      // 2. Guard against active text inputs, textareas, selects, and contenteditables
      const target = e.target;
      const targetTag = target && target.tagName ? target.tagName.toLowerCase() : '';
      const activeEl = document.activeElement;
      const activeTag = activeEl && activeEl.tagName ? activeEl.tagName.toLowerCase() : '';

      if (
        targetTag === 'input' || targetTag === 'textarea' || targetTag === 'select' ||
        activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select' ||
        (target && target.isContentEditable) ||
        (activeEl && activeEl.isContentEditable) ||
        (target && target.closest && target.closest('.builder-popover, .glass-textarea, .glass-input'))
      ) {
        // If Escape pressed while typing inside the popover input, close popover
        if (e.key === 'Escape' && this.popoverElement && this.popoverElement.style.display !== 'none') {
          this.hidePopover();
        }
        return;
      }

      // 3. Guard against active tab: only active when viewing NFA tab
      const activeTab = document.querySelector('.tab.active');
      if (activeTab && activeTab.getAttribute('data-tab') !== 'tab-nfa') {
        return;
      }

      const key = e.key.toUpperCase();
      if (key === 'V') {
        e.preventDefault();
        this.setMode('select');
      } else if (key === 'S') {
        e.preventDefault();
        this.setMode('add-state');
      } else if (key === 'T') {
        e.preventDefault();
        this.setMode('add-transition');
      } else if (key === 'D' || e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        this.deleteSelected();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        this.hidePopover();
        if (this.transitionSourceNode) {
          this.transitionSourceNode.removeClass('transition-source');
          this.transitionSourceNode = null;
        }
        this.setMode('select');
      }
    });
  }

  /**
   * Listen for changes on #nfa-json and synchronize canvas
   */
  _setupEditorSync() {
    if (this.jsonEditor) {
      this.jsonEditor.addEventListener('input', () => {
        if (this.isSyncing) return;
        clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(() => {
          this.syncModelToCanvas();
        }, 300);
      });
    }

    if (this.sampleSelect) {
      this.sampleSelect.addEventListener('change', () => {
        if (this.isSyncing) return;
        setTimeout(() => {
          this.syncModelToCanvas();
        }, 50);
      });
    }
  }

  /**
   * Inject Cytoscape CSS styles for transition-source and candidate-target
   */
  _injectStyles() {
    const cy = this.cy;
    if (!cy) return;

    try {
      cy.style()
        .selector('node.transition-source')
        .style({
          'border-color': '#f59e0b',
          'border-width': 4.5,
          'underlay-color': '#f59e0b',
          'underlay-padding': 10,
          'underlay-opacity': 0.65,
          'underlay-shape': 'ellipse'
        })
        .selector('node.candidate-target')
        .style({
          'border-color': '#10b981',
          'border-width': 4,
          'underlay-color': '#10b981',
          'underlay-padding': 8,
          'underlay-opacity': 0.55
        })
        .update();
    } catch (e) {
      console.warn('Could not inject dynamic builder styles into Cytoscape:', e);
    }
  }

  /**
   * Construct the DOM container for the glassmorphic transition popover
   */
  _createPopoverDOM() {
    if (document.getElementById('builder-transition-popover')) {
      this.popoverElement = document.getElementById('builder-transition-popover');
      return;
    }

    const popover = document.createElement('div');
    popover.id = 'builder-transition-popover';
    popover.className = 'builder-popover';
    popover.style.display = 'none';

    popover.innerHTML = `
      <div class="builder-popover-header">
        <div class="builder-popover-title">
          <span>Add Transition</span>
          <span id="popover-endpoints-badge" class="badge badge-accent">q0 ➔ q1</span>
        </div>
        <button type="button" id="popover-close-btn" class="popover-close-btn" aria-label="Close Popover">&times;</button>
      </div>
      <div class="builder-popover-label">Quick Symbol:</div>
      <div class="builder-popover-pills">
        <button type="button" class="quick-sym-btn" data-sym="0">0</button>
        <button type="button" class="quick-sym-btn" data-sym="1">1</button>
        <button type="button" class="quick-sym-btn" data-sym="ε">ε</button>
      </div>
      <div class="builder-popover-label">Or Custom Symbol:</div>
      <div class="builder-popover-input-row">
        <input type="text" id="popover-sym-input" class="form-control glass-input popover-sym-input" placeholder="e.g. a" maxlength="15" />
        <button type="button" id="popover-add-btn" class="btn btn-accent popover-add-btn">Add</button>
      </div>
    `;

    document.body.appendChild(popover);
    this.popoverElement = popover;

    // Attach listeners inside popover
    const closeBtn = popover.querySelector('#popover-close-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.hidePopover());
    }

    const quickBtns = popover.querySelectorAll('.quick-sym-btn');
    quickBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const sym = btn.getAttribute('data-sym');
        if (this._currentSourceId && this._currentTargetId) {
          this.addTransition(this._currentSourceId, this._currentTargetId, sym);
          this.hidePopover();
        }
      });
    });

    const addBtn = popover.querySelector('#popover-add-btn');
    const input = popover.querySelector('#popover-sym-input');

    const submitCustom = () => {
      let val = (input ? input.value : '').trim();
      if (!val) val = '0';
      if (val === 'eps' || val === 'epsilon' || val === 'e' || val === '') val = 'ε';
      if (this._currentSourceId && this._currentTargetId) {
        this.addTransition(this._currentSourceId, this._currentTargetId, val);
        this.hidePopover();
      }
    };

    if (addBtn) addBtn.addEventListener('click', submitCustom);
    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          submitCustom();
        } else if (e.key === 'Escape') {
          e.preventDefault();
          this.hidePopover();
        }
      });
    }
  }

  /**
   * Open transition symbol popover anchored near target node
   * @param {cytoscape.NodeSingular} sourceNode
   * @param {cytoscape.NodeSingular} targetNode
   */
  openTransitionPopover(sourceNode, targetNode) {
    if (!this.popoverElement) {
      this._createPopoverDOM();
    }

    this._currentSourceId = sourceNode.id();
    this._currentTargetId = targetNode.id();

    const badge = this.popoverElement.querySelector('#popover-endpoints-badge');
    if (badge) {
      badge.textContent = `${sourceNode.id()} ➔ ${targetNode.id()}`;
    }

    const input = this.popoverElement.querySelector('#popover-sym-input');
    if (input) {
      input.value = '';
    }

    // Position popover near target node
    const cy = this.cy;
    if (cy && cy.container()) {
      const renderedPos = targetNode.renderedPosition();
      const containerRect = cy.container().getBoundingClientRect();

      let left = containerRect.left + renderedPos.x + 15;
      let top = containerRect.top + renderedPos.y - 45;

      const popoverWidth = 240;
      const popoverHeight = 160;

      // Viewport clamping
      left = Math.max(10, Math.min(window.innerWidth - popoverWidth - 10, left));
      top = Math.max(10, Math.min(window.innerHeight - popoverHeight - 10, top));

      this.popoverElement.style.left = `${left}px`;
      this.popoverElement.style.top = `${top}px`;
      this.popoverElement.style.display = 'block';

      if (input) {
        setTimeout(() => input.focus(), 50);
      }
    }
  }

  /**
   * Dismiss the transition popover
   */
  hidePopover() {
    if (this.popoverElement) {
      this.popoverElement.style.display = 'none';
    }
    this._currentSourceId = null;
    this._currentTargetId = null;
  }

  /**
   * Add a new state node at model coordinates (x, y)
   * Auto-assigns lowest unused index q_i; sets start_state if canvas is empty
   * @param {number} x
   * @param {number} y
   * @param {string} [customId]
   * @returns {cytoscape.NodeSingular}
   */
  addStateAt(x, y, customId = null) {
    const cy = this.cy;
    if (!cy) return null;

    const userNodes = cy.nodes().filter(n => n.id() !== '__start__');
    const existingIds = new Set(userNodes.map(n => n.id()));

    let stateId = customId;
    if (!stateId) {
      let k = 0;
      while (existingIds.has('q' + k)) {
        k++;
      }
      stateId = 'q' + k;
    }

    const isFirstState = (userNodes.length === 0);
    const classes = ['state-node'];
    if (isFirstState) {
      classes.push('start-state');
    }

    const newNode = cy.add({
      group: 'nodes',
      data: {
        id: stateId,
        label: stateId,
        fontSize: stateId.length > 7 ? '11px' : '13px'
      },
      position: { x: Math.round(x), y: Math.round(y) },
      classes: classes.join(' ')
    });

    if (isFirstState) {
      this._updateStartMarker(stateId);
    }

    // Select the newly placed state
    cy.$(':selected').unselect();
    newNode.select();

    this.syncCanvasToModel();

    if (typeof showToast === 'function') {
      showToast(`State "${stateId}" added${isFirstState ? ' as initial start state' : ''}`, 'info');
    }

    return newNode;
  }

  /**
   * Add or merge a directed transition between sourceId and targetId on symbol
   * @param {string} sourceId
   * @param {string} targetId
   * @param {string} symbol
   */
  addTransition(sourceId, targetId, symbol) {
    const cy = this.cy;
    if (!cy) return;

    let sym = String(symbol).trim();
    if (sym === '' || sym === 'eps' || sym === 'epsilon' || sym === 'e') {
      sym = 'ε';
    }

    // Check if an edge already connects sourceId -> targetId (excluding __start__arrow)
    const existingEdge = cy.edges().filter(e =>
      e.data('source') === sourceId &&
      e.data('target') === targetId &&
      e.id() !== '__start__arrow'
    ).first();

    if (existingEdge.length > 0) {
      let symbols = existingEdge.data('symbols') || [];
      if (!Array.isArray(symbols)) {
        const lbl = existingEdge.data('label') || '';
        symbols = lbl.split(',').map(s => s.trim()).filter(Boolean);
      }
      if (!symbols.includes(sym)) {
        symbols.push(sym);
        symbols.sort();
        existingEdge.data('symbols', symbols);
        existingEdge.data('label', symbols.join(', '));
      }
    } else {
      const isLoop = (sourceId === targetId);
      const classes = ['transition-edge'];
      if (isLoop) classes.push('self-loop');

      const edgeId = `e_${sourceId}_${targetId}_${Date.now()}`;
      cy.add({
        group: 'edges',
        data: {
          id: edgeId,
          source: sourceId,
          target: targetId,
          label: sym,
          symbols: [sym]
        },
        classes: classes.join(' ')
      });
    }

    this.syncCanvasToModel();

    if (typeof showToast === 'function') {
      showToast(`Added transition ${sourceId} ➔ ${targetId} (${sym})`, 'info');
    }
  }

  /**
   * Toggle the selected state as start state, relocating __start__ indicator arrow
   * @param {cytoscape.NodeSingular} [targetNode]
   */
  toggleStartState(targetNode = null) {
    const cy = this.cy;
    if (!cy) return;

    const node = targetNode || cy.nodes(':selected').filter(n => n.id() !== '__start__').first();
    if (!node || !node.length) {
      if (typeof showToast === 'function') {
        showToast('Please select a state to set as start state', 'warning');
      }
      return;
    }

    const stateId = node.id();
    cy.nodes().filter(n => n.id() !== '__start__').removeClass('start-state');
    node.addClass('start-state');
    this._updateStartMarker(stateId);
    this.syncCanvasToModel();

    if (typeof showToast === 'function') {
      showToast(`Set "${stateId}" as start state`, 'info');
    }
  }

  /**
   * Toggle the selected state as accept/final state (double ring style)
   * @param {cytoscape.NodeSingular} [targetNode]
   */
  toggleAcceptState(targetNode = null) {
    const cy = this.cy;
    if (!cy) return;

    const node = targetNode || cy.nodes(':selected').filter(n => n.id() !== '__start__').first();
    if (!node || !node.length) {
      if (typeof showToast === 'function') {
        showToast('Please select a state to toggle accept status', 'warning');
      }
      return;
    }

    const isAccept = node.hasClass('accept-state') || node.hasClass('accept') || node.hasClass('final');
    if (isAccept) {
      node.removeClass('accept-state accept final');
      if (typeof showToast === 'function') {
        showToast(`State "${node.id()}" is now non-accepting`, 'info');
      }
    } else {
      node.addClass('accept-state accept final');
      if (typeof showToast === 'function') {
        showToast(`State "${node.id()}" marked as accept state`, 'info');
      }
    }

    this.syncCanvasToModel();
  }

  /**
   * Delete selected node(s) and incident edges, or selected edge(s)
   */
  deleteSelected() {
    const cy = this.cy;
    if (!cy) return;

    const selected = cy.$(':selected').filter(e => e.id() !== '__start__' && e.id() !== '__start__arrow');
    if (selected.length === 0) {
      if (typeof showToast === 'function') {
        showToast('Select a state or transition to delete', 'info');
      }
      return;
    }

    const wasStartDeleted = selected.nodes().some(n => n.hasClass('start-state'));
    cy.remove(selected);

    // If start state was removed, designate the first remaining state
    if (wasStartDeleted) {
      const remaining = cy.nodes().filter(n => n.id() !== '__start__');
      if (remaining.length > 0) {
        const newStart = remaining.first();
        newStart.addClass('start-state');
        this._updateStartMarker(newStart.id());
      } else {
        cy.remove(cy.$('#__start__, #__start__arrow'));
      }
    }

    this.syncCanvasToModel();

    if (typeof showToast === 'function') {
      showToast('Deleted selected element(s)', 'info');
    }
  }

  /**
   * Synchronize position and target of __start__ marker indicator
   * @param {string} startStateId
   */
  _updateStartMarker(startStateId) {
    const cy = this.cy;
    if (!cy || !startStateId) return;

    const target = cy.getElementById(startStateId);
    if (!target.length) return;

    const pos = target.position();
    const startPos = { x: pos.x - 90, y: pos.y };

    let startDummy = cy.getElementById('__start__');
    if (startDummy.length === 0) {
      cy.add({
        group: 'nodes',
        data: { id: '__start__', label: '', fontSize: '10px' },
        position: startPos,
        classes: 'start-marker-node start-indicator'
      });
    } else {
      startDummy.position(startPos);
    }

    let startArrow = cy.getElementById('__start__arrow');
    if (startArrow.length > 0) {
      cy.remove(startArrow);
    }

    cy.add({
      group: 'edges',
      data: {
        id: '__start__arrow',
        source: '__start__',
        target: startStateId,
        label: 'start'
      },
      classes: 'start-marker-edge start-indicator-edge'
    });
  }

  /**
   * Two-Way Sync (Direction A): Canvas ➔ Model
   * Serializes Cytoscape elements (filtering out synthetic __start__ elements)
   * into valid NFA JSON matching SourceCode/models.py schema.
   */
  syncCanvasToModel() {
    const cy = this.cy;
    if (!cy) return;

    this.isSyncing = true;
    try {
      const userNodes = cy.nodes().filter(n => n.id() !== '__start__');
      const states = userNodes.map(n => n.id()).sort();

      // Start state
      let startNode = userNodes.filter('.start-state').first();
      let startState = startNode.length > 0 ? startNode.id() : (states.length > 0 ? states[0] : '');

      if (states.length > 0 && (!startNode.length || !states.includes(startState))) {
        startState = states[0];
        const newStart = cy.getElementById(startState);
        if (newStart.length) {
          newStart.addClass('start-state');
          this._updateStartMarker(startState);
        }
      }

      // Final states
      const finalStates = userNodes.filter(n =>
        n.hasClass('accept-state') || n.hasClass('accept') || n.hasClass('final')
      ).map(n => n.id()).sort();

      // Transitions & Alphabet
      const userEdges = cy.edges().filter(e =>
        e.id() !== '__start__arrow' && e.data('source') !== '__start__'
      );

      const transMap = new Map(); // `${from}::${symbol}` -> Set(to)
      const alphabetSet = new Set();

      userEdges.forEach(edge => {
        const from = edge.data('source');
        const to = edge.data('target');
        if (!states.includes(from) || !states.includes(to)) return;

        let syms = edge.data('symbols');
        if (!Array.isArray(syms) || syms.length === 0) {
          const lbl = edge.data('label') || '';
          syms = lbl.split(',').map(s => s.trim()).filter(Boolean);
        }
        if (syms.length === 0) syms = ['0'];

        syms.forEach(rawSym => {
          const sym = (rawSym === '' || rawSym === 'eps' || rawSym === 'epsilon' || rawSym === 'e') ? 'ε' : String(rawSym);
          if (sym !== 'ε') {
            alphabetSet.add(sym);
          }
          const key = `${from}::${sym}`;
          if (!transMap.has(key)) {
            transMap.set(key, new Set());
          }
          transMap.get(key).add(to);
        });
      });

      const alphabet = alphabetSet.size > 0 ? Array.from(alphabetSet).sort() : ['0', '1'];

      const transitions = [];
      transMap.forEach((targetsSet, key) => {
        const parts = key.split('::');
        const from = parts[0];
        const symbol = parts[1];
        transitions.push({
          from: from,
          symbol: symbol,
          to: Array.from(targetsSet).sort()
        });
      });

      // Deterministic sort: from state then symbol
      transitions.sort((a, b) => {
        if (a.from !== b.from) return a.from.localeCompare(b.from);
        return a.symbol.localeCompare(b.symbol);
      });

      const nfaModel = {
        name: 'Custom_NFA',
        type: transitions.some(t => t.symbol === 'ε') ? 'EPSILON_NFA' : 'NFA',
        states: states,
        alphabet: alphabet,
        start_state: startState,
        final_states: finalStates,
        transitions: transitions
      };

      if (this.jsonEditor) {
        this.jsonEditor.value = JSON.stringify(nfaModel, null, 2);
      }
      if (this.sampleSelect) {
        this.sampleSelect.value = 'custom';
      }

      if (typeof this.onModelChanged === 'function') {
        this.onModelChanged(nfaModel);
      }
    } catch (err) {
      console.error('Error in syncCanvasToModel:', err);
    } finally {
      this.isSyncing = false;
    }
  }

  /**
   * Two-Way Sync (Direction B): Model ➔ Canvas
   * Loads parsed NFA JSON into Cytoscape, preserving user node positions
   * @param {Object} [automatonOrJson]
   */
  syncModelToCanvas(automatonOrJson = null) {
    if (this.isSyncing) return;

    let automaton = automatonOrJson;
    if (!automaton && this.jsonEditor) {
      try {
        automaton = JSON.parse(this.jsonEditor.value);
      } catch (e) {
        // Incomplete JSON while typing — silently ignore
        return;
      }
    }

    if (!automaton || typeof automaton !== 'object' || !Array.isArray(automaton.states)) {
      return;
    }

    if (this.graphManager && typeof this.graphManager.loadAutomaton === 'function') {
      this.graphManager.loadAutomaton(automaton, 'nfa', { layout: 'preset', animate: false });
    }
  }
}

if (typeof window !== 'undefined') {
  window.GraphBuilder = GraphBuilder;
}
