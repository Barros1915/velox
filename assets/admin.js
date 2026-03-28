/**
 * Admin JavaScript - Velox Framework
 * Funcionalidades interativas do painel admin
 */

// Auto-dismiss alerts
document.querySelectorAll('.alert[data-ah]').forEach(el => {
  setTimeout(() => {
    el.style.transition = 'opacity .4s,transform .4s';
    el.style.opacity = '0';
    el.style.transform = 'translateY(-3px)';
    setTimeout(() => el.remove(), 400);
  }, 3500);
});

// Delete modal
function od(url, lbl) {
  document.getElementById('dl').textContent = lbl;
  document.getElementById('df').action = url;
  document.getElementById('dm').classList.add('open');
}

function cd() {
  document.getElementById('dm').classList.remove('open');
}

// Close modal on background click or Escape key
document.addEventListener('click', e => {
  if (e.target.id === 'dm') cd();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') cd();
});

// Search on Enter
document.querySelectorAll('.sinp[data-url]').forEach(inp => {
  inp.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      const url = new URL(inp.dataset.url, location.href);
      url.searchParams.set('q', inp.value.trim());
      url.searchParams.delete('p');
      location = url.toString();
    }
  });
});

// Clock
function tc() {
  const el = document.getElementById('clk');
  if (el) el.textContent = new Date().toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}
tc();
setInterval(tc, 1000);

// Select all checkboxes
const selAll = document.getElementById('sel-all');
if (selAll) {
  selAll.addEventListener('change', () => {
    document.querySelectorAll('.row-chk').forEach(c => c.checked = selAll.checked);
    updateSelCount();
  });
  document.querySelectorAll('.row-chk').forEach(c => {
    c.addEventListener('change', () => {
      updateSelCount();
      selAll.checked = [...document.querySelectorAll('.row-chk')].every(x => x.checked);
    });
  });
}

function updateSelCount() {
  const n = document.querySelectorAll('.row-chk:checked').length;
  const el = document.getElementById('sel-count');
  if (el) el.textContent = n > 0 ? n + ' selecionado' + (n > 1 ? 's' : '') : '';
  
  const rows = document.querySelectorAll('tbody tr');
  rows.forEach(tr => {
    const chk = tr.querySelector('.row-chk');
    if (chk) tr.classList.toggle('selected', chk.checked);
  });
}

// Bulk action submit
const bulkForm = document.getElementById('bulk-form');
if (bulkForm) {
  bulkForm.addEventListener('submit', e => {
    const ids = [...document.querySelectorAll('.row-chk:checked')].map(c => c.value);
    if (!ids.length) {
      e.preventDefault();
      alert('Selecione pelo menos um registro.');
      return;
    }
    ids.forEach(id => {
      const inp = document.createElement('input');
      inp.type = 'hidden';
      inp.name = 'ids';
      inp.value = id;
      bulkForm.appendChild(inp);
    });
  });
}

// Filter selects auto-submit
document.querySelectorAll('.filter-select').forEach(sel => {
  sel.addEventListener('change', () => {
    const url = new URL(location.href);
    if (sel.value) url.searchParams.set(sel.name, sel.value);
    else url.searchParams.delete(sel.name);
    url.searchParams.delete('p');
    location = url.toString();
  });
});