const screens = [...document.querySelectorAll('.screen')];
const progress = document.getElementById('progress');
let step = 0;
const names = ['Site', 'Form', 'Envelope', 'Openings', 'Simulation', 'Review', 'Results'];

function render() {
  screens.forEach(screen => screen.classList.toggle('active', Number(screen.dataset.step) === step));
  progress.hidden = !step;
  progress.innerHTML = step
    ? names.map((_, index) => `<i class="${index < step ? 'active' : ''}"></i>`).join('') + `<span>${String(step).padStart(2, '0')} / 07</span>`
    : '';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.querySelectorAll('[data-next]').forEach(button => {
  button.onclick = () => { step = Math.min(7, step + 1); render(); };
});
document.querySelectorAll('[data-back]').forEach(button => {
  button.onclick = () => { step = Math.max(0, step - 1); render(); };
});
document.getElementById('themeToggle').onclick = () => {
  document.documentElement.dataset.theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
};

const materialStyle = {
  'Rammed Earth': 'mat-earth', Brick: 'mat-brick', Stone: 'mat-stone', Concrete: 'mat-stone',
  Plaster: 'mat-clay', 'Mineral Wool': 'mat-cork', 'Glass Wool': 'mat-cork',
  'EPS Insulation': 'mat-cork', 'XPS Insulation': 'mat-cork', Polyurethane: 'mat-cork',
  Timber: 'mat-timber', Plywood: 'mat-timber', AAC: 'mat-earth'
};

function selectedMaterial(select) {
  return select.options[select.selectedIndex].text;
}
function updateAssembly(id) {
  const root = document.getElementById(`layers${id}`);
  const layers = [...root.querySelectorAll('.layer')];
  const visual = document.getElementById(`wallVisual${id}`);
  const caption = document.getElementById(`wallCaption${id}`);
  visual.innerHTML = '';
  layers.forEach(row => {
    const material = selectedMaterial(row.querySelector('select'));
    const block = document.createElement('div');
    block.className = materialStyle[material] || 'mat-earth';
    block.style.width = `${100 / layers.length}%`;
    block.title = material;
    visual.append(block);
  });
  caption.textContent = layers.map(row => `${selectedMaterial(row.querySelector('select')).toUpperCase()} ${row.querySelector('input').value}`).join(' · ');
}
['A', 'B'].forEach(id => {
  const root = document.getElementById(`layers${id}`);
  root.onchange = () => updateAssembly(id);
  root.onclick = event => {
    if (event.target.classList.contains('remove') && root.querySelectorAll('.layer').length > 1) {
      event.target.closest('.layer').remove();
      updateAssembly(id);
    }
  };
  updateAssembly(id);
});

function materialOptions() {
  const materials = window.aasraMaterialCatalog || [
    { id: 'mineral_wool', name: 'Mineral Wool' }, { id: 'brick', name: 'Brick' }, { id: 'plaster', name: 'Plaster' }
  ];
  return materials.map(material => `<option value="${material.id}">${material.name}</option>`).join('');
}
document.querySelectorAll('[data-add]').forEach(button => {
  button.onclick = () => {
    const id = button.dataset.add;
    const root = document.getElementById(`layers${id}`);
    const row = document.createElement('div');
    row.className = 'layer';
    row.innerHTML = `<span class="layer-num">${String(root.querySelectorAll('.layer').length + 1).padStart(2, '0')}</span><select class="material">${materialOptions()}</select><input value="40 mm"><button class="remove">×</button>`;
    root.append(row);
    updateAssembly(id);
  };
});

document.querySelectorAll('.count').forEach(button => {
  button.onclick = () => {
    const output = document.getElementById(button.dataset.for);
    output.value = Math.max(0, Number(output.value) + Number(button.dataset.delta));
  };
});
document.getElementById('duration').onclick = event => {
  if (event.target.tagName === 'BUTTON') {
    document.querySelectorAll('#duration button').forEach(button => button.classList.remove('active'));
    event.target.classList.add('active');
  }
};

document.getElementById('restart').onclick = () => { step = 1; render(); };
document.getElementById('export').onclick = () => {
  const toast = document.getElementById('toast');
<<<<<<< HEAD
  if (!window.exportAasraSummary || !window.exportAasraSummary()) {
    toast.textContent = 'Run and select a design before exporting.';
    toast.classList.add('error');
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2400);
    return;
  }
  toast.classList.remove('error');
  toast.textContent = 'Simulation summary downloaded as CSV';
=======
  toast.textContent = 'Simulation summary exported';
>>>>>>> 0e13ea69e5f96ec7ae39838ebbb0097e6dce61cb
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2400);
};
document.getElementById('homeButton').onclick = () => { step = 0; render(); };

const info = {
  about: {
    kicker: 'ABOUT AASRA', title: 'Area-specific shelter design',
    text: 'AASRA is a guided interface for running the supplied thermal model with real climate data and the backend material catalogue.'
  }
};
const modal = document.getElementById('infoModal');
document.querySelectorAll('[data-info]').forEach(button => {
  button.onclick = () => {
    const content = info[button.dataset.info];
    document.getElementById('infoKicker').textContent = content.kicker;
    document.getElementById('infoTitle').textContent = content.title;
    document.getElementById('infoText').textContent = content.text;
    modal.hidden = false;
  };
});
document.getElementById('modalClose').onclick = () => { modal.hidden = true; };
document.getElementById('modalAction').onclick = () => { modal.hidden = true; step = 1; render(); };
modal.onclick = event => { if (event.target === modal) modal.hidden = true; };
