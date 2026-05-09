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
})();
