(function () {
  'use strict';

  const root = document.querySelector('[data-nx-demo]');
  if (!root) return;

  const TYPE_META = {
    lp: { label: 'LP prospect', color: '#2E7898', shape: 'triangle' },
    vc: { label: 'Co-investor / VC', color: '#B75A25', shape: 'circle' },
    fund: { label: 'Fund', color: '#4A7D4B', shape: 'hexagon' },
    portfolio: { label: 'Portfolio company', color: '#76558F', shape: 'square' },
    startup: { label: 'Startup pipeline', color: '#178C87', shape: 'diamond' }
  };

  /* Every entity below is invented for this public portfolio demonstration. */
  const SYNTHETIC_NAMES = {
    lp: [
      'Aster Vale Endowment', 'Brighthaven Pension Trust', 'Cedar Arc Foundation', 'Dawnridge Family Office',
      'Evermere University Endowment', 'Fableton Sovereign Reserve', 'Glenward Impact Trust', 'Harbor Quill Foundation',
      'Ivory Pine Pension Board', 'Juniper Crest Endowment', 'Kestrel Bay Family Capital', 'Lattice Grove Foundation',
      'Moonrise Civic Pension', 'Northwind Scholars Trust', 'Opaline Coast Endowment', 'Peregrine Meadow Foundation',
      'Quartz Harbor Family Office', 'Redwood Lantern Pension', 'Silverfern Public Trust', 'Tamarind Vale Endowment'
    ],
    vc: [
      'Aetherline Ventures', 'Blueforge Capital', 'Cinderleaf Partners', 'Driftglass Ventures', 'Emberwell Capital',
      'Fernlight Ventures', 'Goldfinch Climate Capital', 'Harborline Ventures', 'Ion Meadow Partners', 'Juncture Seedworks',
      'Kiteframe Ventures', 'Lantern Peak Capital', 'Meridian Loom Ventures', 'Novafield Partners', 'Orchard Current Ventures',
      'Prismroot Capital', 'Quiver Bay Ventures', 'Rivermint Partners', 'Sunward Foundry Capital', 'Tidal Grove Ventures',
      'Umbra Spring Partners', 'Verdant Signal Ventures', 'Willow Circuit Capital', 'Xenon Harbor Partners', 'Yarrow Bridge Ventures'
    ],
    fund: [
      'Aster Transition Fund I', 'Blue Delta Climate Fund', 'Coral Grid Growth Fund', 'Daybreak Adaptation Fund',
      'Ember Mobility Fund', 'Flux Circularity Fund', 'Greenline Deployment Fund', 'Harbor Resilience Fund',
      'Ion Frontier Fund', 'Juniper Energy Fund', 'Kinetic Cities Fund', 'Lumen Industry Fund',
      'Monsoon Infrastructure Fund', 'Nova Carbon Fund', 'Opal Food Systems Fund'
    ],
    portfolio: ['Auralis Storage', 'BrineLoop Systems', 'CirrusForge', 'Dewpoint Mobility', 'EmberGrid Labs'],
    startup: [
      'Aerolith Cooling', 'Brightsoil Analytics', 'Canalyn Water', 'Driftcell Energy', 'EcoWeave Materials',
      'FluxHarvest', 'Gridnest', 'Heatwise Labs', 'IonSprout', 'JouleFleet', 'Kelpstone Carbon', 'Loopbrick',
      'Mistline Cooling', 'NoriVolt', 'OrbitWaste', 'PollenGrid', 'QuantaCrop', 'Reefroute Logistics',
      'SolarMint', 'TerraKiln', 'Updraft Renewables', 'VerdantMesh', 'Wattleaf Systems', 'Xenra Materials',
      'YieldOrbit', 'ZephyrCharge', 'AmberCycle', 'BasinIQ', 'CeraLoop', 'DeltaCanopy', 'Evercharge Labs',
      'Fieldstone AI', 'Geotide Systems', 'Heliocraft', 'Infraseed'
    ]
  };

  const REGIONS = ['Maritime Southeast Asia', 'Mainland Southeast Asia', 'Asia-Pacific', 'Emerging Asia', 'Global South'];
  const SECTORS = ['Energy transition', 'Climate adaptation', 'Circular economy', 'Sustainable mobility', 'Food and water', 'Industrial decarbonization'];
  const FITS = ['Transition', 'Resilience', 'Infrastructure', 'Circularity', 'Unclassified'];
  const STAGES = ['Pre-seed', 'Seed', 'Series A', 'Growth', 'Fund investment'];

  function seededRandom(seed) {
    let value = seed >>> 0;
    return function () {
      value += 0x6D2B79F5;
      let t = value;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  const random = seededRandom(20260826);
  const pick = list => list[Math.floor(random() * list.length)];
  const nodes = [];

  Object.keys(SYNTHETIC_NAMES).forEach(type => {
    SYNTHETIC_NAMES[type].forEach((name, index) => {
      const region = REGIONS[(index + Object.keys(TYPE_META).indexOf(type)) % REGIONS.length];
      const sector = SECTORS[(index * 2 + type.length) % SECTORS.length];
      const fit = FITS[(index + type.length * 2) % FITS.length];
      const stage = type === 'lp' ? 'Allocator' : type === 'fund' ? 'Fund investment' : STAGES[(index + type.length) % 4];
      const description = type === 'lp'
        ? `Fictional institutional allocator exploring ${sector.toLowerCase()} exposure across ${region}.`
        : type === 'vc'
          ? `Fictional investment firm backing ${stage.toLowerCase()} ${sector.toLowerCase()} ventures across ${region}.`
          : type === 'fund'
            ? `Fictional investment vehicle focused on ${sector.toLowerCase()} deployment across ${region}.`
            : `Fictional ${stage.toLowerCase()} company developing ${sector.toLowerCase()} solutions for ${region}.`;
      nodes.push({
        id: `${type}-${String(index + 1).padStart(2, '0')}`,
        name, type, region, sector, fit, stage, description,
        x: 0, y: 0, vx: 0, vy: 0, degree: 0, bridge: 0, reach: 0
      });
    });
  });

  const byId = new Map(nodes.map(node => [node.id, node]));
  const isolatedIds = new Set(['lp-19', 'vc-23', 'fund-14', 'portfolio-05', 'startup-26', 'startup-31', 'startup-33', 'startup-35']);
  const eligible = nodes.filter(node => !isolatedIds.has(node.id));
  const edges = [];
  const edgeKeys = new Set();

  function addEdge(source, target, kind) {
    if (!source || !target || source.id === target.id) return false;
    const key = [source.id, target.id].sort().join('|');
    if (edgeKeys.has(key)) return false;
    edgeKeys.add(key);
    edges.push({
      source: source.id,
      target: target.id,
      kind: kind || (random() < 0.69 ? 'active' : random() < 0.66 ? 'affiliated' : 'exploratory'),
      strength: 0.45 + random() * 0.55,
      length: 58 + random() * 34
    });
    return true;
  }

  /* A connected synthetic backbone, followed by deterministic cross-cluster relationships. */
  for (let i = 1; i < eligible.length; i += 1) {
    const node = eligible[i];
    const crossType = eligible.slice(0, i).filter(candidate => candidate.type !== node.type);
    const pool = crossType.length ? crossType : eligible.slice(0, i);
    addEdge(node, pool[Math.floor(random() * pool.length)], 'active');
  }
  while (edges.length < 220) {
    const source = pick(eligible);
    let candidates = eligible.filter(target => target.id !== source.id && (target.fit === source.fit || target.region === source.region || target.type !== source.type));
    if (!candidates.length) candidates = eligible;
    addEdge(source, pick(candidates));
  }

  const centers = {
    lp: [210, 160], vc: [520, 175], fund: [370, 330], portfolio: [650, 380], startup: [440, 510]
  };
  nodes.forEach(node => {
    const center = centers[node.type];
    node.x = center[0] + (random() - 0.5) * 230;
    node.y = center[1] + (random() - 0.5) * 150;
  });

  /* Lightweight deterministic force layout: no company source code or private scoring logic. */
  for (let tick = 0; tick < 190; tick += 1) {
    edges.forEach(edge => {
      const source = byId.get(edge.source);
      const target = byId.get(edge.target);
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const distance = Math.max(1, Math.hypot(dx, dy));
      const force = (distance - edge.length) * 0.0017;
      source.vx += dx / distance * force;
      source.vy += dy / distance * force;
      target.vx -= dx / distance * force;
      target.vy -= dy / distance * force;
    });
    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const a = nodes[i];
        const b = nodes[j];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let distance = Math.hypot(dx, dy);
        if (distance < 1) { dx = random() - 0.5; dy = random() - 0.5; distance = 1; }
        if (distance < 76) {
          const force = (76 - distance) * 0.0033;
          a.vx += dx / distance * force;
          a.vy += dy / distance * force;
          b.vx -= dx / distance * force;
          b.vy -= dy / distance * force;
        }
      }
    }
    nodes.forEach(node => {
      const center = centers[node.type];
      node.vx += (center[0] - node.x) * 0.00055;
      node.vy += (center[1] - node.y) * 0.00055;
      node.vx *= 0.84;
      node.vy *= 0.84;
      node.x = Math.max(28, Math.min(812, node.x + node.vx));
      node.y = Math.max(28, Math.min(582, node.y + node.vy));
    });
  }

  const canvas = document.getElementById('nxCanvas');
  const stage = document.getElementById('nxStage');
  const context = canvas.getContext('2d');
  const tooltip = document.getElementById('nxTooltip');
  const live = document.getElementById('nxLive');
  const search = document.getElementById('nxSearch');
  const searchResults = document.getElementById('nxSearchResults');
  const selectedPanel = document.getElementById('nxSelected');
  const bridgeList = document.getElementById('nxBridgeList');
  const reachList = document.getElementById('nxReachList');
  const typeInputs = Array.from(root.querySelectorAll('[data-nx-type]'));
  const fitInputs = Array.from(root.querySelectorAll('[data-nx-fit]'));
  const edgeInputs = Array.from(root.querySelectorAll('[data-nx-edge]'));
  const priorityTab = document.getElementById('nxPriorityTab');
  const selectionTab = document.getElementById('nxSelectionTab');
  const priorityPane = document.getElementById('nxPriorityPane');
  const selectionPane = document.getElementById('nxSelectionPane');
  const expandButton = document.getElementById('nxExpand');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  let width = 0;
  let height = 0;
  let pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  let visibleNodes = nodes.slice();
  let visibleEdges = edges.slice();
  let visibleById = new Set(nodes.map(node => node.id));
  let hovered = null;
  let selected = null;
  let fittedOnce = false;
  let view = { scale: 1, x: 0, y: 0 };
  let pointerState = null;

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]);
  }

  function activeSet(inputs, attribute) {
    return new Set(inputs.filter(input => input.checked).map(input => input.getAttribute(attribute)));
  }

  function buildAdjacency(edgeList) {
    const adjacency = new Map(visibleNodes.map(node => [node.id, new Set()]));
    edgeList.forEach(edge => {
      if (!adjacency.has(edge.source) || !adjacency.has(edge.target)) return;
      adjacency.get(edge.source).add(edge.target);
      adjacency.get(edge.target).add(edge.source);
    });
    return adjacency;
  }

  function computeNetworkScores() {
    const adjacency = buildAdjacency(visibleEdges);
    visibleNodes.forEach(node => {
      const neighbors = adjacency.get(node.id) || new Set();
      node.degree = neighbors.size;
      const neighborTypes = new Set(Array.from(neighbors).map(id => byId.get(id).type));
      const neighborFits = new Set(Array.from(neighbors).map(id => byId.get(id).fit));
      node.bridge = Math.round(node.degree * Math.max(1, neighborTypes.size) * (1 + Math.max(0, neighborFits.size - 1) * 0.22) * 10);
      const reached = new Set(neighbors);
      neighbors.forEach(id => (adjacency.get(id) || new Set()).forEach(next => reached.add(next)));
      reached.delete(node.id);
      node.reach = reached.size;
    });
  }

  function applyFilters() {
    const types = activeSet(typeInputs, 'data-nx-type');
    const fits = activeSet(fitInputs, 'data-nx-fit');
    const overlays = activeSet(edgeInputs, 'data-nx-edge');
    visibleNodes = nodes.filter(node => types.has(node.type) && fits.has(node.fit));
    visibleById = new Set(visibleNodes.map(node => node.id));
    visibleEdges = edges.filter(edge => visibleById.has(edge.source) && visibleById.has(edge.target) && (edge.kind === 'active' || overlays.has(edge.kind)));
    if (selected && !visibleById.has(selected.id)) selected = null;
    if (hovered && !visibleById.has(hovered.id)) hovered = null;
    computeNetworkScores();
    updateMetrics();
    updateInsights();
    updateSelection();
    draw();
  }

  function updateMetrics() {
    const adjacency = buildAdjacency(visibleEdges);
    const unconnected = visibleNodes.filter(node => !(adjacency.get(node.id) || new Set()).size).length;
    document.getElementById('nxInstitutionCount').textContent = visibleNodes.length.toLocaleString();
    document.getElementById('nxRelationshipCount').textContent = visibleEdges.length.toLocaleString();
    document.getElementById('nxUnconnectedCount').textContent = unconnected.toLocaleString();
    root.querySelectorAll('[data-nx-fit-count]').forEach(element => {
      element.textContent = nodes.filter(node => node.fit === element.getAttribute('data-nx-fit-count')).length;
    });
    root.querySelectorAll('[data-nx-edge-count]').forEach(element => {
      element.textContent = edges.filter(edge => edge.kind === element.getAttribute('data-nx-edge-count')).length;
    });
  }

  function rankItem(node, value, suffix) {
    const item = document.createElement('li');
    item.tabIndex = 0;
    item.innerHTML = `<i class="nx-node-icon nx-shape-${TYPE_META[node.type].shape}" style="--node-color:${TYPE_META[node.type].color}"></i><strong>${escapeHtml(node.name)}</strong><b>${value}${suffix || ''}</b>`;
    const choose = () => selectNode(node, true);
    item.addEventListener('click', choose);
    item.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(); }
    });
    return item;
  }

  function updateInsights() {
    bridgeList.innerHTML = '';
    reachList.innerHTML = '';
    visibleNodes.slice().sort((a, b) => b.bridge - a.bridge).slice(0, 6).forEach(node => bridgeList.appendChild(rankItem(node, node.bridge, '')));
    visibleNodes.slice().sort((a, b) => b.reach - a.reach).slice(0, 6).forEach(node => reachList.appendChild(rankItem(node, node.reach, '')));
  }

  function showTab(tab) {
    const selectionIsOn = tab === 'selection';
    priorityTab.classList.toggle('on', !selectionIsOn);
    selectionTab.classList.toggle('on', selectionIsOn);
    priorityPane.classList.toggle('on', !selectionIsOn);
    selectionPane.classList.toggle('on', selectionIsOn);
    priorityTab.setAttribute('aria-selected', String(!selectionIsOn));
    selectionTab.setAttribute('aria-selected', String(selectionIsOn));
  }

  function suggestedAction(node) {
    const actions = {
      lp: `Map a warm introduction through the strongest ${node.region.toLowerCase()} connection and validate appetite for ${node.fit.toLowerCase()} exposure.`,
      vc: `Compare overlapping pipeline in ${node.sector.toLowerCase()} and identify one credible co-diligence opportunity.`,
      fund: `Review complementary mandate and explore a simulated co-investment or referral pathway.`,
      portfolio: `Use the two-hop network to prioritize commercial introductions and the next fundraising conversation.`,
      startup: `Confirm thesis fit, then route the company to the most relevant fictional investor cluster for screening.`
    };
    return actions[node.type];
  }

  function updateSelection() {
    if (!selected) {
      selectedPanel.innerHTML = '<div class="nx-empty">Select any node in the network to inspect its fictional profile, connections, and suggested next action.</div>';
      return;
    }
    selectedPanel.innerHTML = `
      <span class="nx-selected-badge"><i class="nx-node-icon nx-shape-${TYPE_META[selected.type].shape}" style="--node-color:${TYPE_META[selected.type].color}"></i> Fictional ${escapeHtml(TYPE_META[selected.type].label)}</span>
      <h4>${escapeHtml(selected.name)}</h4>
      <p>${escapeHtml(selected.description)} This profile and every relationship connected to it are synthetic.</p>
      <div class="nx-detail"><span>Region</span><b>${escapeHtml(selected.region)}</b><span>Focus</span><b>${escapeHtml(selected.sector)}</b><span>Demo fund fit</span><b>${escapeHtml(selected.fit)}</b><span>Direct relationships</span><b>${selected.degree}</b><span>Two-hop reach</span><b>${selected.reach}</b><span>Bridge score</span><b>${selected.bridge}</b></div>
      <div class="nx-action"><b>Suggested next action</b>${escapeHtml(suggestedAction(selected))}</div>`;
  }

  function resizeCanvas() {
    const rect = stage.getBoundingClientRect();
    width = Math.max(320, rect.width);
    height = Math.max(420, rect.height);
    pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * pixelRatio);
    canvas.height = Math.round(height * pixelRatio);
    if (!fittedOnce) { fitGraph(); fittedOnce = true; }
    draw();
  }

  function fitGraph() {
    const list = visibleNodes.length ? visibleNodes : nodes;
    const xs = list.map(node => node.x);
    const ys = list.map(node => node.y);
    const minX = Math.min.apply(null, xs);
    const maxX = Math.max.apply(null, xs);
    const minY = Math.min.apply(null, ys);
    const maxY = Math.max.apply(null, ys);
    const padding = width < 520 ? 42 : 64;
    const graphWidth = Math.max(1, maxX - minX);
    const graphHeight = Math.max(1, maxY - minY);
    view.scale = Math.max(0.35, Math.min(1.45, Math.min((width - padding * 2) / graphWidth, (height - padding * 2) / graphHeight)));
    view.x = width / 2 - (minX + maxX) / 2 * view.scale;
    view.y = height / 2 - (minY + maxY) / 2 * view.scale;
  }

  function screenPoint(node) {
    return { x: node.x * view.scale + view.x, y: node.y * view.scale + view.y };
  }

  function nodeRadius(node) {
    return 3.7 + Math.min(7.2, Math.sqrt(Math.max(0, node.degree)) * 1.05);
  }

  function pathNode(node, x, y, radius) {
    const shape = TYPE_META[node.type].shape;
    context.beginPath();
    if (shape === 'circle') {
      context.arc(x, y, radius, 0, Math.PI * 2);
    } else if (shape === 'square') {
      context.rect(x - radius, y - radius, radius * 2, radius * 2);
    } else if (shape === 'diamond') {
      context.moveTo(x, y - radius * 1.15); context.lineTo(x + radius * 1.15, y); context.lineTo(x, y + radius * 1.15); context.lineTo(x - radius * 1.15, y); context.closePath();
    } else {
      const sides = shape === 'triangle' ? 3 : 6;
      const offset = -Math.PI / 2;
      for (let index = 0; index < sides; index += 1) {
        const angle = offset + index * Math.PI * 2 / sides;
        const px = x + Math.cos(angle) * radius * (shape === 'triangle' ? 1.18 : 1);
        const py = y + Math.sin(angle) * radius * (shape === 'triangle' ? 1.18 : 1);
        if (!index) context.moveTo(px, py); else context.lineTo(px, py);
      }
      context.closePath();
    }
  }

  function draw() {
    if (!width || !height) return;
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    context.clearRect(0, 0, width, height);

    context.save();
    visibleEdges.forEach(edge => {
      const source = byId.get(edge.source);
      const target = byId.get(edge.target);
      const a = screenPoint(source);
      const b = screenPoint(target);
      const highlighted = selected && (edge.source === selected.id || edge.target === selected.id);
      context.beginPath();
      context.moveTo(a.x, a.y);
      context.lineTo(b.x, b.y);
      context.lineWidth = highlighted ? 1.45 : 0.55;
      context.strokeStyle = highlighted ? 'rgba(15,91,80,.66)' : edge.kind === 'active' ? 'rgba(112,126,115,.24)' : 'rgba(48,143,135,.38)';
      context.setLineDash(edge.kind === 'active' ? [] : [4, 4]);
      context.stroke();
    });
    context.setLineDash([]);

    const labelNodes = new Set(visibleNodes.slice().sort((a, b) => b.degree - a.degree).slice(0, width < 520 ? 7 : 14).map(node => node.id));
    visibleNodes.forEach(node => {
      const point = screenPoint(node);
      if (point.x < -30 || point.x > width + 30 || point.y < -30 || point.y > height + 30) return;
      const radius = nodeRadius(node) * Math.max(0.8, Math.min(1.1, view.scale));
      if (selected && selected.id === node.id) {
        context.beginPath();
        context.arc(point.x, point.y, radius + 6, 0, Math.PI * 2);
        context.fillStyle = 'rgba(15,91,80,.13)';
        context.fill();
        context.strokeStyle = '#0F5B50';
        context.lineWidth = 1.4;
        context.stroke();
      }
      pathNode(node, point.x, point.y, radius);
      context.fillStyle = TYPE_META[node.type].color;
      context.globalAlpha = hovered && hovered.id !== node.id && (!selected || selected.id !== node.id) ? 0.66 : 0.96;
      context.fill();
      context.strokeStyle = '#FFFFFF';
      context.lineWidth = 1;
      context.stroke();
      context.globalAlpha = 1;

      if (labelNodes.has(node.id) || (selected && selected.id === node.id) || (hovered && hovered.id === node.id)) {
        context.font = `${selected && selected.id === node.id ? 600 : 500} ${width < 520 ? 8 : 9}px Inter, sans-serif`;
        context.textAlign = 'center';
        context.textBaseline = 'top';
        context.lineWidth = 3.5;
        context.strokeStyle = 'rgba(252,253,249,.96)';
        context.strokeText(node.name, point.x, point.y + radius + 4);
        context.fillStyle = selected && selected.id === node.id ? '#0A4239' : '#59645B';
        context.fillText(node.name, point.x, point.y + radius + 4);
      }
    });
    context.restore();
  }

  function nodeAt(screenX, screenY) {
    let best = null;
    let bestDistance = Infinity;
    visibleNodes.forEach(node => {
      const point = screenPoint(node);
      const distance = Math.hypot(point.x - screenX, point.y - screenY);
      if (distance <= nodeRadius(node) + 6 && distance < bestDistance) { best = node; bestDistance = distance; }
    });
    return best;
  }

  function pointerPosition(event) {
    const rect = canvas.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  function setTooltip(node, x, y) {
    if (!node) { tooltip.classList.remove('show'); return; }
    tooltip.innerHTML = `<strong>${escapeHtml(node.name)}</strong><span>${escapeHtml(TYPE_META[node.type].label)} &middot; fictional</span>${escapeHtml(node.sector)}<br>${node.degree} visible relationships`;
    tooltip.style.left = `${Math.min(width - 220, Math.max(8, x + 12))}px`;
    tooltip.style.top = `${Math.min(height - 90, Math.max(8, y + 12))}px`;
    tooltip.classList.add('show');
  }

  function selectNode(node, focusGraph) {
    selected = node;
    showTab('selection');
    updateSelection();
    if (focusGraph) {
      view.x = width / 2 - node.x * view.scale;
      view.y = height / 2 - node.y * view.scale;
    }
    live.textContent = `${node.name}, fictional ${TYPE_META[node.type].label}, ${node.degree} visible relationships and ${node.reach} stakeholders within two hops.`;
    draw();
  }

  canvas.addEventListener('pointerdown', event => {
    const position = pointerPosition(event);
    const hit = nodeAt(position.x, position.y);
    pointerState = { mode: hit ? 'node' : 'pan', node: hit, startX: position.x, startY: position.y, lastX: position.x, lastY: position.y, moved: false };
    canvas.classList.add('is-dragging');
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener('pointermove', event => {
    const position = pointerPosition(event);
    if (pointerState) {
      const dx = position.x - pointerState.lastX;
      const dy = position.y - pointerState.lastY;
      if (Math.hypot(position.x - pointerState.startX, position.y - pointerState.startY) > 4) pointerState.moved = true;
      if (pointerState.mode === 'node' && pointerState.node) {
        pointerState.node.x = (position.x - view.x) / view.scale;
        pointerState.node.y = (position.y - view.y) / view.scale;
      } else {
        view.x += dx;
        view.y += dy;
      }
      pointerState.lastX = position.x;
      pointerState.lastY = position.y;
      setTooltip(null);
      draw();
      return;
    }
    hovered = nodeAt(position.x, position.y);
    canvas.style.cursor = hovered ? 'pointer' : 'grab';
    setTooltip(hovered, position.x, position.y);
    draw();
  });

  function finishPointer(event) {
    if (!pointerState) return;
    if (pointerState.mode === 'node' && pointerState.node && !pointerState.moved) selectNode(pointerState.node, false);
    pointerState = null;
    canvas.classList.remove('is-dragging');
    if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
  }
  canvas.addEventListener('pointerup', finishPointer);
  canvas.addEventListener('pointercancel', finishPointer);
  canvas.addEventListener('pointerleave', () => { if (!pointerState) { hovered = null; setTooltip(null); draw(); } });

  function zoomAt(factor, x, y) {
    const oldScale = view.scale;
    const newScale = Math.max(0.25, Math.min(3, oldScale * factor));
    view.x = x - (x - view.x) * newScale / oldScale;
    view.y = y - (y - view.y) * newScale / oldScale;
    view.scale = newScale;
    draw();
  }

  canvas.addEventListener('wheel', event => {
    event.preventDefault();
    const position = pointerPosition(event);
    zoomAt(event.deltaY < 0 ? 1.12 : 0.89, position.x, position.y);
  }, { passive: false });

  canvas.addEventListener('keydown', event => {
    const step = 24;
    if (event.key === 'ArrowLeft') view.x += step;
    else if (event.key === 'ArrowRight') view.x -= step;
    else if (event.key === 'ArrowUp') view.y += step;
    else if (event.key === 'ArrowDown') view.y -= step;
    else if (event.key === '+' || event.key === '=') zoomAt(1.15, width / 2, height / 2);
    else if (event.key === '-' || event.key === '_') zoomAt(0.87, width / 2, height / 2);
    else if (event.key === '0') fitGraph();
    else if (event.key === 'Escape') { selected = null; showTab('priority'); updateSelection(); }
    else return;
    event.preventDefault();
    draw();
  });

  function renderSearchResults() {
    const query = search.value.trim().toLowerCase();
    searchResults.innerHTML = '';
    if (query.length < 2) { searchResults.classList.remove('open'); return; }
    const matches = visibleNodes.filter(node => node.name.toLowerCase().includes(query) || node.sector.toLowerCase().includes(query)).slice(0, 6);
    matches.forEach(node => {
      const button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('role', 'option');
      button.innerHTML = `${escapeHtml(node.name)}<small>${escapeHtml(TYPE_META[node.type].label)} &middot; fictional</small>`;
      button.addEventListener('click', () => { search.value = node.name; searchResults.classList.remove('open'); selectNode(node, true); });
      searchResults.appendChild(button);
    });
    searchResults.classList.toggle('open', matches.length > 0);
  }

  search.addEventListener('input', renderSearchResults);
  search.addEventListener('keydown', event => {
    if (event.key === 'Enter') {
      const first = visibleNodes.find(node => node.name.toLowerCase().includes(search.value.trim().toLowerCase()));
      if (first) { event.preventDefault(); searchResults.classList.remove('open'); selectNode(first, true); }
    } else if (event.key === 'Escape') searchResults.classList.remove('open');
  });
  document.addEventListener('click', event => { if (!root.contains(event.target) || (!search.contains(event.target) && !searchResults.contains(event.target))) searchResults.classList.remove('open'); });

  typeInputs.concat(fitInputs, edgeInputs).forEach(input => input.addEventListener('change', applyFilters));
  priorityTab.addEventListener('click', () => showTab('priority'));
  selectionTab.addEventListener('click', () => showTab('selection'));
  document.getElementById('nxZoomIn').addEventListener('click', () => zoomAt(1.18, width / 2, height / 2));
  document.getElementById('nxZoomOut').addEventListener('click', () => zoomAt(0.84, width / 2, height / 2));
  document.getElementById('nxFit').addEventListener('click', () => { fitGraph(); draw(); });

  function isExpanded() {
    return document.fullscreenElement === root || document.webkitFullscreenElement === root || root.classList.contains('nx-expanded');
  }

  function updateExpandButton() {
    const expanded = isExpanded();
    expandButton.innerHTML = `<span aria-hidden="true">&#x26F6;</span> ${expanded ? 'Exit full screen' : 'Extend'}`;
    expandButton.setAttribute('aria-label', expanded ? 'Exit network fullscreen' : 'Open network in fullscreen');
    window.setTimeout(() => { resizeCanvas(); fitGraph(); draw(); }, 80);
  }

  function useExpandedFallback(turnOn) {
    root.classList.toggle('nx-expanded', turnOn);
    document.body.classList.toggle('nx-lock', turnOn);
    updateExpandButton();
  }

  expandButton.addEventListener('click', async () => {
    if (root.classList.contains('nx-expanded')) {
      useExpandedFallback(false);
      return;
    }
    if (document.fullscreenElement === root || document.webkitFullscreenElement === root) {
      const exit = document.exitFullscreen || document.webkitExitFullscreen;
      if (exit) await exit.call(document);
      return;
    }
    const request = root.requestFullscreen || root.webkitRequestFullscreen;
    if (request) {
      try {
        const result = request.call(root);
        if (result && typeof result.then === 'function') await result;
      } catch (error) {
        useExpandedFallback(true);
      }
    } else {
      useExpandedFallback(true);
    }
  });

  document.addEventListener('fullscreenchange', updateExpandButton);
  document.addEventListener('webkitfullscreenchange', updateExpandButton);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && root.classList.contains('nx-expanded')) useExpandedFallback(false);
  });

  document.getElementById('nxReset').addEventListener('click', () => {
    typeInputs.forEach(input => { input.checked = true; });
    fitInputs.forEach(input => { input.checked = true; });
    edgeInputs.forEach(input => { input.checked = input.getAttribute('data-nx-edge') === 'affiliated'; });
    search.value = '';
    selected = null;
    hovered = null;
    showTab('priority');
    applyFilters();
    fitGraph();
    draw();
  });

  const helpDialog = document.getElementById('nxHelpDialog');
  function openHelp() {
    if (typeof helpDialog.showModal === 'function') helpDialog.showModal(); else helpDialog.setAttribute('open', '');
  }
  document.getElementById('nxHelp').addEventListener('click', openHelp);
  root.querySelectorAll('[data-nx-help]').forEach(button => button.addEventListener('click', openHelp));
  document.getElementById('nxHelpClose').addEventListener('click', () => helpDialog.close ? helpDialog.close() : helpDialog.removeAttribute('open'));
  helpDialog.addEventListener('click', event => { if (event.target === helpDialog && helpDialog.close) helpDialog.close(); });

  if ('ResizeObserver' in window) new ResizeObserver(resizeCanvas).observe(stage);
  else window.addEventListener('resize', resizeCanvas);

  applyFilters();
  resizeCanvas();
  if (!reducedMotion) requestAnimationFrame(draw);
})();
