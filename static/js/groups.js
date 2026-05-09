/* groups.js — Phase 4 interactive behaviour */

(function () {
  'use strict';

  // ── Tab switching ──────────────────────────────────────────────────
  document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;

      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => { p.hidden = true; });

      btn.classList.add('active');
      const panel = document.getElementById('tab-' + target);
      if (panel) panel.hidden = false;

      // Keep URL in sync so refresh / back works
      const url = new URL(window.location.href);
      url.searchParams.set('tab', target);
      history.replaceState(null, '', url.toString());
    });
  });

  // ── Archive confirmation ───────────────────────────────────────────
  document.getElementById('archive-form')?.addEventListener('submit', e => {
    const btn = e.submitter || e.target.querySelector('[type=submit]');
    const verb = btn && btn.textContent.trim().toLowerCase().startsWith('unarchive')
      ? 'Unarchive'
      : 'Archive';
    if (!confirm(verb + ' this group?')) e.preventDefault();
  });

  // ── Upload destination: sync hidden group_id input ─────────────────
  const destSelect  = document.getElementById('destination-select');
  const groupIdInput = document.getElementById('group-id-input');
  const folderGroup  = document.getElementById('folder-group');

  if (destSelect && groupIdInput) {
    function syncGroupId() {
      const opt = destSelect.options[destSelect.selectedIndex];
      groupIdInput.value = opt.dataset.groupId || '';

      // Hide folder selector when uploading to a group (group has its own organisation)
      if (folderGroup) {
        folderGroup.style.display = opt.dataset.groupId ? 'none' : '';
      }
    }

    destSelect.addEventListener('change', syncGroupId);
    syncGroupId(); // run once on page load to respect pre-selected group
  }

  // ── Escape key closes preview modal ───────────────────────────────
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closePreview();
  });

})();


// ── Card click: toggle checkbox selection ─────────────────────────
function fileCardClick(event, card) {
  // Ignore clicks on links, buttons, and labels (checkbox area)
  if (
    event.target.tagName === 'A' ||
    event.target.tagName === 'BUTTON' ||
    event.target.tagName === 'INPUT' ||
    event.target.tagName === 'LABEL' ||
    event.target.closest('a') ||
    event.target.closest('button') ||
    event.target.closest('.file-card__actions') ||
    event.target.closest('.file-card__checkbox-wrap')
  ) return;

  const checkbox = card.querySelector('.file-card__checkbox');
  if (checkbox) {
    checkbox.checked = !checkbox.checked;
    card.classList.toggle('file-card--selected', checkbox.checked);
  }
}


// ── File preview modal ────────────────────────────────────────────
function previewFile(btn) {
  const card        = btn.closest('.file-card');
  const previewUrl  = card.dataset.previewUrl || '';
  const downloadUrl = card.dataset.downloadUrl || '';
  const type        = card.dataset.previewType || '';
  const title       = card.dataset.title || '';

  const modal      = document.getElementById('preview-modal');
  const modalTitle = document.getElementById('preview-modal-title');
  const modalBody  = document.getElementById('preview-modal-body');
  const dlLink     = document.getElementById('preview-modal-download');
  if (!modal) return;

  modalTitle.textContent = title;
  modalBody.innerHTML = '';

  // Wire up download button
  if (dlLink && downloadUrl) {
    dlLink.href = downloadUrl;
    dlLink.setAttribute('download', title);
    dlLink.style.display = '';
  }

  let content;
  if (type.startsWith('image/')) {
    content = document.createElement('img');
    content.src = previewUrl;
    content.alt = title;
    content.style.cssText = 'max-width:100%;max-height:70vh;display:block;margin:auto;border-radius:4px;';
  } else if (type.startsWith('video/')) {
    content = document.createElement('video');
    content.src = previewUrl;
    content.controls = true;
    content.style.cssText = 'max-width:100%;max-height:70vh;display:block;margin:auto;';
  } else if (type === 'application/pdf') {
    content = document.createElement('iframe');
    content.src = previewUrl;
    content.style.cssText = 'width:100%;height:70vh;border:none;';
    content.title = title;
  } else if (type.startsWith('audio/')) {
    content = document.createElement('audio');
    content.src = previewUrl;
    content.controls = true;
    content.style.cssText = 'width:100%;display:block;margin:auto;';
  } else {
    // Non-previewable: show a download prompt
    const msg = document.createElement('div');
    msg.style.cssText = 'text-align:center;padding:2rem;';
    msg.innerHTML = `<p style="margin-bottom:1rem;color:#6b7280;">This file type cannot be previewed.</p>
      <a href="${downloadUrl}" download="${title}" class="btn btn-primary">⬇ Download File</a>`;
    content = msg;
  }

  if (content) modalBody.appendChild(content);

  modal.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closePreview() {
  const modal = document.getElementById('preview-modal');
  if (!modal) return;
  modal.classList.remove('open');
  document.body.style.overflow = '';
  const body = document.getElementById('preview-modal-body');
  if (body) body.innerHTML = '';
}


// ── Trash file via AJAX ───────────────────────────────────────────
async function trashFile(btn) {
  const card  = btn.closest('.file-card');
  const title = card.dataset.title;
  const url   = card.dataset.deleteUrl;

  if (!confirm(`Move "${title}" to trash?`)) return;

  btn.disabled    = true;
  btn.textContent = '…';

  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken':      window.CSRF_TOKEN || '',
        'X-Requested-With': 'XMLHttpRequest',
      },
    });

    if (!resp.ok) throw new Error(`Server error ${resp.status}`);

    card.style.transition = 'opacity 0.25s, transform 0.25s';
    card.style.opacity    = '0';
    card.style.transform  = 'scale(0.95)';
    setTimeout(() => card.remove(), 250);

    showToast(`"${title}" moved to trash.`);

  } catch (err) {
    btn.disabled    = false;
    btn.textContent = '🗑';
    showToast(`Failed to delete "${title}". Please try again.`, 'error');
  }
}


// ── Toast notifications ───────────────────────────────────────────
function showToast(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 200);
  }, 3500);
}
