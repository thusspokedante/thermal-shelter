/* Data integration for the supplied FastAPI contract. The backend owns all
   thermal calculations; this file only builds valid request objects and renders
   returned data. */
(() => {
  const API_BASE = 'http://127.0.0.1:8000/api';
  const byId = id => document.getElementById(id);
  const state = { runs: {}, selectedDesign: null };

  const notify = (message, isError = false) => {
    const toast = byId('toast');
    toast.textContent = message;
    toast.classList.toggle('error', isError);
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 4400);
  };
  const request = async (url, options) => {
    let response;
    try {
      response = await fetch(url, options);
    } catch (_) {
      throw new Error('Cannot reach the backend. Start FastAPI at http://127.0.0.1:8000 and try again.');
    }
    if (response.ok) return response.json();
    let detail = 'Request failed.';
    try {
      const body = await response.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || body);
    } catch (_) { /* keep the general message */ }
    const messageByStatus = {
      400: `Invalid simulation data: ${detail}`,
      404: `API route or material was not found: ${detail}`,
      422: `Some required values are invalid: ${detail}`,
      500: `The simulation could not be completed: ${detail}`
    };
    throw new Error(messageByStatus[response.status] || `Backend error (${response.status}): ${detail}`);
  };
  const selectedSite = () => window.selectedShelterLocation;
  const durationHours = () => document.querySelector('#duration button.active').textContent.trim() === '24 hours' ? 24 : 168;
  const addDays = (date, days) => {
<<<<<<< HEAD
    // Use UTC calendar arithmetic so an Indian/other positive timezone cannot
    // turn a same-day range into the previous date through toISOString().
    const value = new Date(`${date}T00:00:00Z`);
    value.setUTCDate(value.getUTCDate() + days);
=======
    const value = new Date(`${date}T00:00:00`);
    value.setDate(value.getDate() + days);
>>>>>>> 0e13ea69e5f96ec7ae39838ebbb0097e6dce61cb
    return value.toISOString().slice(0, 10);
  };
  const numberValue = (id, label, options = {}) => {
    const value = Number(byId(id).value);
    if (!Number.isFinite(value) || (options.positive && value <= 0) || (options.nonNegative && value < 0)) {
      throw new Error(`${label} must be ${options.positive ? 'greater than zero' : 'zero or greater'}.`);
    }
    return value;
  };
  const materialLayer = (materialId, thicknessId, label) => ({
    material_id: materialId,
    thickness_m: numberValue(thicknessId, `${label} thickness`, { positive: true }) / 1000
  });
  const wall = id => ({
    layers: [...document.querySelectorAll(`#layers${id} .layer`)].map((row, index) => {
      const thickness = Number.parseFloat(row.querySelector('input').value);
      if (!Number.isFinite(thickness) || thickness <= 0) throw new Error(`Wall layer ${index + 1} thickness for design ${id} must be greater than zero.`);
      return { material_id: row.querySelector('select').value, thickness_m: thickness / 1000 };
    })
  });
  const openingList = (count, area, uValue, shgc, solarExposure) => Array.from(
    { length: numberValue(count, 'Opening count', { nonNegative: true }) },
    () => ({ area_m2: area, u_value_w_m2k: uValue, shgc, solar_exposure_factor: solarExposure })
  );
  const designRequest = id => {
    const windowArea = numberValue(`windowArea${id}`, 'Window area', { positive: true });
    const windowU = numberValue(`windowU${id}`, 'Window U-value', { positive: true });
    const windowShgc = numberValue(`windowShgc${id}`, 'Window solar gain', { nonNegative: true });
    if (windowShgc > 1) throw new Error('Window solar gain (SHGC) must be between 0 and 1.');
    const doorArea = numberValue(`doorArea${id}`, 'Door area', { positive: true });
    const doorU = numberValue(`doorU${id}`, 'Door U-value', { positive: true });
    return {
      geometry: {
        length_m: numberValue(`length${id}`, 'Length', { positive: true }),
        width_m: numberValue(`width${id}`, 'Width', { positive: true }),
        height_m: numberValue(`height${id}`, 'Wall height', { positive: true })
      },
      wall: wall(id),
      roof: { layers: [materialLayer(byId('roofMaterial').value, 'roofThickness', 'Roof')] },
      floor: { layers: [materialLayer(byId('floorMaterial').value, 'floorThickness', 'Floor')] },
      windows: openingList(`windows${id}`, windowArea, windowU, windowShgc, 1),
      doors: openingList(`doors${id}`, doorArea, doorU, 0, 0),
      settings: {
        duration_hours: durationHours(),
        timestep_minutes: numberValue('timestepMinutes', 'Time step', { positive: true }),
        initial_indoor_temperature_c: numberValue('initialIndoorTemp', 'Initial indoor temperature'),
        air_changes_per_hour: numberValue('airChanges', 'Air changes', { nonNegative: true }),
        indoor_heat_gain_w: numberValue('internalGain', 'Internal gains', { nonNegative: true }),
        comfort_min_c: numberValue('comfortMin', 'Comfort minimum'),
        comfort_max_c: numberValue('comfortMax', 'Comfort maximum')
      }
    };
  };
  const updateComfortRange = () => {
    const min = Number(byId('comfortMin').value);
    const max = Number(byId('comfortMax').value);
    byId('comfortValue').textContent = Number.isFinite(min) && Number.isFinite(max) ? `${min}–${max} °C` : 'Set a valid range';
  };
  byId('comfortMin').addEventListener('input', updateComfortRange);
  byId('comfortMax').addEventListener('input', updateComfortRange);
  updateComfortRange();

  const linePath = (values, min, max, width, bottom, height) => values.map((value, index) => {
    const x = (index / Math.max(1, values.length - 1)) * width;
    const y = bottom - ((value - min) / Math.max(1, max - min)) * height;
    return `${index ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(' ');
  const drawWeather = rows => {
    const temperatures = rows.map(row => row.temperature);
    const solar = rows.map(row => row.solar_irradiance);
    if (!temperatures.length || !solar.length) return;
    const temperatureLine = linePath(temperatures, Math.min(...temperatures) - 1, Math.max(...temperatures) + 1, 500, 140, 130);
    const solarLine = linePath(solar, 0, Math.max(1, ...solar), 500, 140, 130);
    byId('weatherLine').setAttribute('d', temperatureLine);
    byId('weatherArea').setAttribute('d', `${temperatureLine} L500 140 L0 140 Z`);
    byId('solarLine').setAttribute('d', solarLine);
  };
  async function refreshWeather(site) {
    if (!site) return;
    try {
      const date = byId('simDate').value;
      const query = new URLSearchParams({ latitude: site.lat, longitude: site.lon, start_date: date, end_date: date });
      const climate = await request(`${API_BASE}/climate?${query}`);
      const rows = climate.hourly;
      if (!rows.length) throw new Error('No hourly climate data was returned for this date.');
      const temps = rows.map(row => row.temperature);
      const solar = rows.map(row => row.solar_irradiance);
      const place = site.label || `${site.lat.toFixed(4)}°, ${site.lon.toFixed(4)}°`;
      byId('weatherPlace').textContent = `${place} · ${date}`;
      byId('avgTemp').textContent = `${(temps.reduce((sum, value) => sum + value, 0) / temps.length).toFixed(1)}°C`;
      byId('solar').textContent = `${(solar.reduce((sum, value) => sum + value, 0) / 1000).toFixed(2)} kWh/m²`;
      byId('liveTemp').textContent = `${rows[Math.min(14, rows.length - 1)].temperature.toFixed(1)}°C`;
      drawWeather(rows);
    } catch (error) {
      byId('weatherPlace').textContent = 'Climate data unavailable';
      byId('avgTemp').textContent = '—';
      byId('solar').textContent = '—';
      byId('liveTemp').textContent = '—';
      notify(error.message, true);
    }
  }
  const loadMaterials = async () => {
    try {
      const response = await request(`${API_BASE}/materials`);
      if (!Array.isArray(response.materials) || !response.materials.length) throw new Error('The backend material catalogue is empty.');
      window.aasraMaterialCatalog = response.materials;
      document.querySelectorAll('select.material, select.construction-material').forEach(select => {
        const priorValue = select.value;
        select.innerHTML = response.materials.map(material => `<option value="${material.id}">${material.name}</option>`).join('');
        select.value = response.materials.some(material => material.id === priorValue) ? priorValue : response.materials[0].id;
      });
      ['A', 'B'].forEach(id => updateAssembly(id));
    } catch (error) {
      notify(error.message, true);
    }
  };
<<<<<<< HEAD
  const rankDesigns = () => Object.entries(state.runs).sort(([idA, runA], [idB, runB]) => {
    const a = runA.summary;
    const b = runB.summary;
    // Rank comfort first, then prefer lower heat loss, then higher solar gain.
    return (b.comfort_hours - a.comfort_hours)
      || (a.total_heat_loss_kwh - b.total_heat_loss_kwh)
      || (b.solar_energy_captured_kwh - a.solar_energy_captured_kwh)
      || idA.localeCompare(idB);
  });
=======
>>>>>>> 0e13ea69e5f96ec7ae39838ebbb0097e6dce61cb
  const displayReview = () => {
    const settings = state.runs.A?.summary ? state.runs.A.settings : null;
    ['A', 'B'].forEach(id => {
      const result = state.runs[id];
      const summary = result.summary;
      const comfortPercent = Math.round((summary.comfort_hours / summary.duration_hours) * 100);
      byId(`design${id}Desc`).textContent = `${summary.indoor_temperature_min_c.toFixed(1)}–${summary.indoor_temperature_max_c.toFixed(1)}°C indoors`;
      byId(`score${id}`).textContent = `${summary.comfort_hours.toFixed(1)} h`;
      byId(`score${id}Label`).textContent = `${comfortPercent}%`;
      byId(`bar${id}`).style.width = `${comfortPercent}%`;
      const lossMetric = Math.min(100, summary.total_heat_loss_kwh * 10);
      const solarMetric = Math.min(100, summary.solar_energy_captured_kwh * 25);
      byId(`mass${id}`).style.width = `${lossMetric}%`;
      byId(`mass${id}Label`).textContent = `${summary.total_heat_loss_kwh.toFixed(2)} kWh`;
      byId(`insulation${id}`).style.width = `${solarMetric}%`;
      byId(`insulation${id}Label`).textContent = `${summary.solar_energy_captured_kwh.toFixed(2)} kWh`;
      byId(`design${id}`).classList.remove('recommended');
    });
<<<<<<< HEAD
    const ranked = rankDesigns();
    const [winnerId, winner] = ranked[0];
    const [runnerUpId, runnerUp] = ranked[1];
    const comfortGap = winner.summary.comfort_hours - runnerUp.summary.comfort_hours;
    byId(`design${winnerId}`).classList.add('recommended');
    byId('comparisonWinner').textContent = `Design ${winnerId} is recommended: ${winner.summary.comfort_hours.toFixed(1)} comfort hours${comfortGap ? ` (${comfortGap.toFixed(1)} h more than design ${runnerUpId})` : ''}.`;
    byId('comparisonGap').textContent = `RANK 1 · DESIGN ${winnerId}`;
=======
    byId('comparisonWinner').textContent = 'Select design A or B to inspect its backend simulation result.';
    byId('comparisonGap').textContent = 'NO AUTO-RANKING';
>>>>>>> 0e13ea69e5f96ec7ae39838ebbb0097e6dce61cb
    return settings;
  };
  const drawResult = id => {
    const result = state.runs[id];
    if (!result) return;
    const { summary, time_series: rows } = result;
    const comfortPercent = Math.round((summary.comfort_hours / summary.duration_hours) * 100);
    const outdoorMax = Math.max(...rows.map(row => row.outdoor_temperature_c));
    byId('comfortHours').textContent = `${comfortPercent}%`;
    byId('meanIndoor').textContent = `${summary.indoor_temperature_average_c.toFixed(1)}°C`;
    byId('peakReduction').textContent = `−${Math.max(0, outdoorMax - summary.indoor_temperature_max_c).toFixed(1)}°C`;
    byId('resultSummary').textContent = `Design ${id} stayed in the selected comfort range for ${summary.comfort_hours.toFixed(1)} of ${summary.duration_hours} simulated hours. Backend results report ${summary.solar_energy_captured_kwh.toFixed(2)} kWh solar energy captured and ${summary.total_heat_loss_kwh.toFixed(2)} kWh total heat loss.`;
    const allTemps = rows.flatMap(row => [row.outdoor_temperature_c, row.indoor_temperature_c]);
    const min = Math.min(...allTemps) - 1;
    const max = Math.max(...allTemps) + 1;
    byId('outdoorPath').setAttribute('d', linePath(rows.map(row => row.outdoor_temperature_c), min, max, 330, 148, 132));
    byId('indoorPath').setAttribute('d', linePath(rows.map(row => row.indoor_temperature_c), min, max, 330, 148, 132));
    const comfortMid = (result.settings.comfort_min_c + result.settings.comfort_max_c) / 2;
    const y = 148 - ((comfortMid - min) / Math.max(1, max - min)) * 132;
    const band = Math.max(6, ((result.settings.comfort_max_c - result.settings.comfort_min_c) / Math.max(1, max - min)) * 132);
    byId('comfortBand').setAttribute('d', `M0 ${y.toFixed(1)} L330 ${y.toFixed(1)}`);
    byId('comfortBand').setAttribute('stroke-width', band.toFixed(1));
<<<<<<< HEAD
    const totalHours = summary.duration_hours;
    byId('resultAxisStart').textContent = '0 h';
    byId('resultAxisQuarter').textContent = `${(totalHours * .25).toFixed(0)} h`;
    byId('resultAxisHalf').textContent = `${(totalHours * .5).toFixed(0)} h`;
    byId('resultAxisThreeQuarter').textContent = `${(totalHours * .75).toFixed(0)} h`;
    byId('resultAxisEnd').textContent = `${totalHours.toFixed(0)} h`;
  };

  const csvCell = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
  window.exportAasraSummary = () => {
    const id = state.selectedDesign;
    const result = state.runs[id];
    if (!result) return false;
    const { summary, time_series: rows } = result;
    const exportRows = [
      ['AASRA thermal shelter simulation summary'],
      ['Selected design', id],
      ['Comfort hours', summary.comfort_hours],
      ['Duration hours', summary.duration_hours],
      ['Comfort percentage', `${((summary.comfort_hours / summary.duration_hours) * 100).toFixed(1)}%`],
      ['Mean indoor temperature (°C)', summary.indoor_temperature_average_c],
      ['Indoor minimum temperature (°C)', summary.indoor_temperature_min_c],
      ['Indoor maximum temperature (°C)', summary.indoor_temperature_max_c],
      ['Solar energy captured (kWh)', summary.solar_energy_captured_kwh],
      ['Total heat loss (kWh)', summary.total_heat_loss_kwh],
      [],
      ['Timestamp', 'Indoor temperature (°C)', 'Outdoor temperature (°C)']
    ];
    rows.forEach(row => exportRows.push([row.timestamp, row.indoor_temperature_c, row.outdoor_temperature_c]));
    const blob = new Blob([exportRows.map(row => row.map(csvCell).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `aasra-simulation-design-${id.toLowerCase()}.csv`;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
    return true;
=======
>>>>>>> 0e13ea69e5f96ec7ae39838ebbb0097e6dce61cb
  };

  const runButton = document.querySelector('[data-step="5"] [data-next]');
  runButton.onclick = async () => {
    const original = runButton.innerHTML;
    runButton.disabled = true;
    runButton.textContent = 'Running simulations…';
    try {
      const first = designRequest('A');
      const second = designRequest('B');
      if (first.settings.comfort_max_c <= first.settings.comfort_min_c) throw new Error('Comfort maximum must be greater than comfort minimum.');
      const site = selectedSite();
      const start = byId('simDate').value;
      const end = addDays(start, Math.ceil(durationHours() / 24) - 1);
      const climateQuery = new URLSearchParams({ latitude: site.lat, longitude: site.lon, start_date: start, end_date: end });
      const climateResponse = await request(`${API_BASE}/climate?${climateQuery}`);
      const climate = climateResponse.hourly.map(row => ({
        timestamp: row.time,
        outdoor_temperature_c: row.temperature,
        solar_irradiance_w_m2: row.solar_irradiance,
        relative_humidity_percent: row.relative_humidity,
        wind_speed_m_s: row.wind_speed
      }));
      if (climate.length < 2) throw new Error('The backend returned too little climate data to run a simulation.');
      const [runA, runB] = await Promise.all([
        request(`${API_BASE}/simulation`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...first, climate }) }),
        request(`${API_BASE}/simulation`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...second, climate }) })
      ]);
      state.runs = { A: { ...runA, settings: first.settings }, B: { ...runB, settings: second.settings } };
      displayReview();
      step = 6;
      render();
      displayReview();
    } catch (error) {
      notify(error.message, true);
    } finally {
      runButton.disabled = false;
      runButton.innerHTML = original;
    }
  };
  document.querySelectorAll('[data-view-result]').forEach(button => {
    button.onclick = () => {
      const id = button.dataset.viewResult;
      if (!state.runs[id]) return notify('Run both designs before viewing results.', true);
      state.selectedDesign = id;
      step = 7;
      render();
      drawResult(id);
    };
  });
  byId('simDate').addEventListener('change', () => refreshWeather(selectedSite()));
  window.addEventListener('shelterlocationchange', event => refreshWeather(event.detail));
  loadMaterials();
  refreshWeather(selectedSite());
})();
