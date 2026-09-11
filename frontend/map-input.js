/* Map, manual coordinates, and optional place search for the site screen. */
(() => {
  const mapElement = document.getElementById('siteMap');
  const coordinates = document.getElementById('selectedCoordinates');
  const latitudeInput = document.getElementById('latitude');
  const longitudeInput = document.getElementById('longitude');
  const searchInput = document.getElementById('locationSearch');
  const searchButton = document.getElementById('searchLocation');
  const status = document.getElementById('mapSearchStatus');
  const initial = { lat: Number(latitudeInput.value), lon: Number(longitudeInput.value), label: 'Initial location' };

  const map = L.map(mapElement, { zoomControl: true }).setView([initial.lat, initial.lon], 8);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);
  const marker = L.circleMarker([initial.lat, initial.lon], {
    radius: 9, color: '#0d5545', weight: 3, fillColor: '#86dcb8', fillOpacity: 1,
    title: 'Selected shelter location'
  }).addTo(map);

  const format = (value, positive, negative) => `${Math.abs(value).toFixed(4)}° ${value >= 0 ? positive : negative}`;
  const validCoordinates = (lat, lon) => Number.isFinite(lat) && Number.isFinite(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
  const setStatus = message => { status.textContent = message; };

  function setLocation(lat, lon, label = 'Selected map point', recenter = false) {
    if (!validCoordinates(lat, lon)) {
      setStatus('Enter latitude from −90 to 90 and longitude from −180 to 180.');
      return false;
    }
    latitudeInput.value = lat.toFixed(4);
    longitudeInput.value = lon.toFixed(4);
    marker.setLatLng([lat, lon]);
    coordinates.textContent = `${format(lat, 'N', 'S')} · ${format(lon, 'E', 'W')}`;
    marker.bindPopup(`${label}<br><b>${lat.toFixed(4)}, ${lon.toFixed(4)}</b>`);
    if (recenter) map.setView([lat, lon], 10, { animate: true });
    window.selectedShelterLocation = { lat, lon, label };
    window.dispatchEvent(new CustomEvent('shelterlocationchange', { detail: { lat, lon, label } }));
    return true;
  }

  function applyManualCoordinates() {
    const lat = Number(latitudeInput.value);
    const lon = Number(longitudeInput.value);
    if (setLocation(lat, lon, 'Manual coordinates', true)) setStatus('Map updated from manual coordinates.');
  }

  async function searchPlace() {
    const query = searchInput.value.trim();
    if (!query) return setStatus('Enter a place name or address to search.');
    searchButton.disabled = true;
    setStatus('Searching map…');
    try {
      const params = new URLSearchParams({ q: query, format: 'jsonv2', limit: '1', addressdetails: '1' });
      const response = await fetch(`https://nominatim.openstreetmap.org/search?${params}`);
      if (!response.ok) throw new Error('The location search service is unavailable.');
      const results = await response.json();
      if (!results.length) throw new Error('No location found. Try a more specific search.');
      const result = results[0];
      const label = result.display_name || query;
      setLocation(Number(result.lat), Number(result.lon), label, true);
      searchInput.value = label;
      setStatus('Location found.');
      marker.openPopup();
    } catch (error) {
      setStatus(error.message || 'Location search failed. You can enter coordinates manually.');
    } finally {
      searchButton.disabled = false;
    }
  }

  map.on('click', event => {
    setLocation(event.latlng.lat, event.latlng.lng, 'Selected map point');
    setStatus('Map location selected.');
    marker.openPopup();
  });
  latitudeInput.addEventListener('change', applyManualCoordinates);
  longitudeInput.addEventListener('change', applyManualCoordinates);
  searchButton.addEventListener('click', searchPlace);
  searchInput.addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); searchPlace(); }
  });

  setLocation(initial.lat, initial.lon, initial.label);
  window.aasraMap = map;
  const siteScreen = document.querySelector('.screen[data-step="1"]');
  new MutationObserver(() => {
    if (siteScreen.classList.contains('active')) setTimeout(() => map.invalidateSize(), 0);
  }).observe(siteScreen, { attributes: true, attributeFilter: ['class'] });
})();
