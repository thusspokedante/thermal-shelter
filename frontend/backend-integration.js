/* Connects the existing Thermonest interface to the supplied FastAPI backend.
   It changes data flow only; visual markup, CSS and animations remain untouched. */
(() => {
  const API_BASE = 'http://127.0.0.1:8000/api';
  const sites = {
    'Barmer, Rajasthan': { lat: 25.746, lon: 71.392 },
    'Jaisalmer, Rajasthan': { lat: 26.915, lon: 70.908 },
    'Bikaner, Rajasthan': { lat: 28.023, lon: 73.312 }
  };
  const materialIds = {
    'Adobe block': 'rammed_earth', 'Fired brick': 'brick',
    'Rammed earth': 'rammed_earth', Stone: 'stone',
    'Lime plaster': 'plaster', 'Clay plaster': 'plaster',
    'Cork insulation': 'mineral_wool', 'Air cavity': 'mineral_wool',
    'Timber lining': 'wood', 'Gypsum board': 'plaster'
  };
  const roofLayers = {
    'Terracotta tile + air gap': [{ material_id: 'concrete', thickness_m: .02 }, { material_id: 'mineral_wool', thickness_m: .05 }],
    'Corrugated metal + insulation': [{ material_id: 'wood', thickness_m: .02 }, { material_id: 'mineral_wool', thickness_m: .08 }],
    'Earth roof': [{ material_id: 'rammed_earth', thickness_m: .20 }]
  };
  const floorLayers = {
    'Compacted earth': [{ material_id: 'rammed_earth', thickness_m: .15 }],
    'Stone slab': [{ material_id: 'stone', thickness_m: .12 }],
    'Concrete + finish': [{ material_id: 'concrete', thickness_m: .15 }]
  };
  let state = { comparison: null, recommended: null, settings: null };
  const byId = id => document.getElementById(id);
  const today = value => value || new Date().toISOString().slice(0, 10);
  const toast = message => {
    const element = byId('toast');
    element.textContent = message;
    element.classList.add('show');
    setTimeout(() => element.classList.remove('show'), 3000);
  };
  const request = async (url, options) => {
    const response = await fetch(url, options);
    if (response.ok) return response.json();
    let message = 'Backend request failed';
    try { message = (await response.json()).detail || message; } catch (_) {}
    throw new Error(message);
  };
  const addDays = (date, days) => {
    const value = new Date(`${date}T00:00:00`);
    value.setDate(value.getDate() + days);
    return value.toISOString().slice(0, 10);
  };
  const duration = () => {
    const label = [...document.querySelectorAll('#duration button')]
      .find(button => button.classList.contains('active'))?.textContent.trim();
    return label === 'Hourly' ? 24 : 168; // Backend schema limits a run to 168 hours.
  };
  const assembly = id => [...document.querySelectorAll(`#layers${id} .layer`)].map(row => {
    const name = row.querySelector('select').value;
    const thickness = Math.max(.001, parseFloat(row.querySelector('input').value) / 1000 || .02);
    return { material_id: materialIds[name] || 'plaster', thickness_m: thickness };
  });
  const glazing = label => label.startsWith('Double') ? { u: 1.8, shgc: .52 } : label.startsWith('Unshaded') ? { u: 4.8, shgc: .72 } : { u: 2.8, shgc: .60 };
  const openingData = id => {
    const panel = [...document.querySelectorAll('.opening-design')][id === 'A' ? 0 : 1];
    const windowCount = Number(byId(`windows${id}`).value), doorCount = Number(byId(`doors${id}`).value), ventCount = Number(byId(`vents${id}`).value);
    const glass = glazing(panel.querySelector('select').value);
    return {
      windows: Array.from({ length: Math.max(0, windowCount) }, () => ({ area_m2: 1.2, u_value_w_m2k: glass.u, shgc: glass.shgc, solar_exposure_factor: 1 })),
      doors: Array.from({ length: Math.max(0, doorCount) }, () => ({ area_m2: 1.8, u_value_w_m2k: 2, shgc: 0, solar_exposure_factor: 0 })),
      vents: Math.max(0, ventCount)
    };
  };
  const design = id => {
    const shared = document.querySelectorAll('.envelope-finishes select');
    const openings = openingData(id);
    return {
      design_id: `design_${id.toLowerCase()}`,
      name: `Shelter ${id}`,
      geometry: { length_m: Number(byId(`length${id}`).value), width_m: Number(byId(`width${id}`).value), height_m: Number(byId(`height${id}`).value) },
      wall: { layers: assembly(id) },
      roof: { layers: roofLayers[shared[0].value] || roofLayers['Terracotta tile + air gap'] },
      floor: { layers: floorLayers[shared[1].value] || floorLayers['Compacted earth'] },
      windows: openings.windows, doors: openings.doors, vents: openings.vents
    };
  };
  const settings = designs => {
    const simulation = document.querySelector('[data-step="5"]');
    const initial = Number(simulation.querySelector('input[type="number"]').value);
    const comfortMin = Number(byId('comfort').value);
    const vents = (designs[0].vents + designs[1].vents) / 2;
    return { duration_hours: duration(), timestep_minutes: 10, initial_indoor_temperature_c: initial, air_changes_per_hour: .2 + vents * .1 + Number(byId('ventilation').value) * .05, indoor_heat_gain_w: 100, comfort_min_c: comfortMin, comfort_max_c: comfortMin + 8 };
  };
  const comparisonUI = comparison => {
    const durationHours = state.settings.duration_hours;
    comparison.results.forEach(result => {
      const id = result.design_id.endsWith('a') ? 'A' : 'B';
      const metrics = result.metrics;
      const comfort = Math.round(metrics.comfort_hours / durationHours * 100);
      const protection = Math.max(0, Math.min(100, 100 - metrics.total_heat_loss_kwh * 8));
      const solar = Math.max(0, Math.min(100, metrics.solar_energy_captured_kwh * 25));
      byId(`design${id}Desc`).textContent = result.name;
      byId(`score${id}`).textContent = comfort;
      byId(`score${id}Label`).textContent = `${comfort}%`;
      byId(`bar${id}`).style.width = `${comfort}%`;
      byId(`mass${id}`).style.width = `${protection}%`;
      byId(`mass${id}Label`).textContent = `${metrics.total_heat_loss_kwh.toFixed(1)} kWh`;
      byId(`insulation${id}`).style.width = `${solar}%`;
      byId(`insulation${id}Label`).textContent = `${metrics.solar_energy_captured_kwh.toFixed(1)} kWh`;
      byId(`design${id}`).classList.toggle('recommended', result.rank === 1);
    });
    const winner = comparison.results.find(result => result.rank === 1);
    byId('comparisonWinner').textContent = `${winner.name} is the recommended design.`;
    byId('comparisonGap').textContent = `Rank 1 · ${winner.metrics.comfort_hours.toFixed(1)} comfort h`;
  };
  const line = (rows, field, min, max) => rows.map((row, index) => `${index ? 'L' : 'M'}${(index / (rows.length - 1 || 1) * 330).toFixed(1)} ${(148 - (row[field] - min) / Math.max(max - min, 1) * 132).toFixed(1)}`).join(' ');
  const resultUI = result => {
    const { summary, time_series: rows } = result;
    const comfort = Math.round(summary.comfort_hours / summary.duration_hours * 100);
    const outdoorMax = Math.max(...rows.map(row => row.outdoor_temperature_c));
    byId('comfortHours').textContent = `${comfort}%`;
    byId('meanIndoor').textContent = `${summary.indoor_temperature_average_c.toFixed(1)}°C`;
    byId('peakReduction').textContent = `−${Math.max(0, outdoorMax - summary.indoor_temperature_max_c).toFixed(1)}°C`;
    byId('resultSummary').textContent = `The recommended user-defined shelter maintains comfort for ${summary.comfort_hours.toFixed(1)} of ${summary.duration_hours} simulated hours, captures ${summary.solar_energy_captured_kwh.toFixed(1)} kWh of solar energy and loses ${summary.total_heat_loss_kwh.toFixed(1)} kWh through the envelope.`;
    const values = rows.flatMap(row => [row.outdoor_temperature_c, row.indoor_temperature_c]);
    const min = Math.min(...values) - 1, max = Math.max(...values) + 1;
    byId('outdoorPath').setAttribute('d', line(rows, 'outdoor_temperature_c', min, max));
    byId('indoorPath').setAttribute('d', line(rows, 'indoor_temperature_c', min, max));
    const midpoint = (state.settings.comfort_min_c + state.settings.comfort_max_c) / 2;
    const y = 148 - (midpoint - min) / Math.max(max - min, 1) * 132;
    const thickness = Math.max(6, (state.settings.comfort_max_c - state.settings.comfort_min_c) / Math.max(max - min, 1) * 132);
    byId('comfortBand').setAttribute('d', `M0 ${y} L330 ${y}`);
    byId('comfortBand').setAttribute('stroke-width', thickness);
  };
  const simButton = document.querySelector('[data-step="5"] [data-next]');
  simButton.onclick = async () => {
    const original = simButton.innerHTML;
    simButton.disabled = true;
    simButton.textContent = 'Running simulation…';
    try {
      const startDate = today(byId('simDate').value);
      const site = sites[byId('locationSelect').value];
      const query = new URLSearchParams({ latitude: site.lat, longitude: site.lon, start_date: startDate, end_date: addDays(startDate, Math.ceil(duration() / 24) - 1) });
      const climateResponse = await request(`${API_BASE}/climate?${query}`);
      const climate = climateResponse.hourly.map(row => ({ timestamp: row.time, outdoor_temperature_c: row.temperature, solar_irradiance_w_m2: row.solar_irradiance, relative_humidity_percent: row.relative_humidity, wind_speed_m_s: row.wind_speed }));
      const designs = [design('A'), design('B')];
      const sharedSettings = settings(designs);
      const comparison = await request(`${API_BASE}/simulation/compare`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ designs: designs.map(({ vents, ...payload }) => payload), climate, settings: sharedSettings }) });
      const winning = comparison.results.find(result => result.rank === 1);
      const winningDesign = designs.find(item => item.design_id === winning.design_id);
      const recommended = await request(`${API_BASE}/simulation`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...winningDesign, climate, settings: sharedSettings }) });
      state = { comparison, recommended, settings: sharedSettings };
      comparisonUI(comparison);
      step = 6; render(); comparisonUI(comparison);
    } catch (error) {
      toast(`Simulation unavailable: ${error.message}`);
    } finally {
      simButton.disabled = false;
      simButton.innerHTML = original;
    }
  };
  document.querySelector('[data-step="6"] [data-next]').onclick = () => { step = 7; render(); if (state.recommended) resultUI(state.recommended); };
  byId('locationSelect').addEventListener('change', async () => {
    const site = sites[byId('locationSelect').value];
    try {
      const date = today(byId('simDate').value);
      const climate = await request(`${API_BASE}/climate?${new URLSearchParams({ latitude: site.lat, longitude: site.lon, start_date: date, end_date: date })}`);
      const rows = climate.hourly, temps = rows.map(row => row.temperature), solar = rows.map(row => row.solar_irradiance);
      byId('weatherPlace').textContent = `${byId('locationSelect').value} · ${date}`;
      byId('avgTemp').textContent = `${(temps.reduce((sum, value) => sum + value, 0) / temps.length).toFixed(1)}°C`;
      byId('solar').textContent = `${(solar.reduce((sum, value) => sum + value, 0) / 1000).toFixed(1)} kWh/m²`;
      byId('liveTemp').textContent = `${rows[Math.min(14, rows.length - 1)].temperature.toFixed(1)}°C`;
    } catch (_) { /* Existing preview remains available when the API is offline. */ }
  });
})();
