document.addEventListener('DOMContentLoaded', function () {
  // populate months (if not already present elsewhere)
  const payslipMonth = document.getElementById('payslipMonth');
  if (payslipMonth && payslipMonth.children.length === 0) {
    const now = new Date();
    for (let i = 0; i < 12; i++) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const label = d.toLocaleString(undefined, { month: 'long', year: 'numeric' });
      const opt = document.createElement('option');
      opt.value = `${y}-${m}`;
      opt.textContent = label;
      payslipMonth.appendChild(opt);
    }
  }

  const navItems = document.querySelectorAll('.nav-item');
  const panels = document.querySelectorAll('.tab-panel');
  const cta = document.querySelector('.cta');
  const payslipForm = document.getElementById('generatePayslipForm');
  const payslipEmployee = document.getElementById('payslipEmployee');
  const generatePayslipBtn = document.getElementById('generatePayslipBtn');
  const payslipSuccessModal = document.getElementById('payslipSuccessModal');
  const payslipSuccessText = document.getElementById('payslipSuccessText');
  const closePayslipSuccess = document.getElementById('closePayslipSuccess');

  function activate(targetId) {
    navItems.forEach(n => n.classList.toggle('active', n.dataset.target === targetId));
    panels.forEach(p => p.classList.toggle('active', p.id === targetId));
    history.replaceState(null, '', '#' + targetId);
  }

  navItems.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const target = btn.dataset.target || 'home';
      activate(target);
      // focus first input in panel (optional)
      const panel = document.getElementById(target);
      if (panel) {
        const focusable = panel.querySelector('input, select, button, a');
        if (focusable) focusable.focus();
      }
    });
  });

  // support hash on load (fallback to home)
  const initial = (location.hash && location.hash.replace('#','')) || 'home';
  // if requested panel doesn't exist, fallback to home
  if (!document.getElementById(initial)) {
    activate('home');
  } else {
    activate(initial);
  }

  // CTA action -> open New Employee modal
  if (cta) {
    cta.addEventListener('click', (e) => {
      e.preventDefault();
      // show modal
      const modal = document.getElementById('newEmployeeModal');
      if (modal) modal.style.display = 'flex';
      const first = modal && modal.querySelector('input[name="username"]');
      if (first) first.focus();
    });
  }

  // Handle pending payslip buttons (mark-paid) using delegation
  document.addEventListener('click', function (e) {
    const actionBtn = e.target.closest('button[data-action]');
    if (actionBtn) {
      const action = actionBtn.dataset.action;
      const id = actionBtn.dataset.id;
      if (action === 'mark-paid') {
        if (!confirm('Mark payslip ' + id + ' as paid?')) return;

        actionBtn.disabled = true;
        // call server to delete the pending payslip
        fetch(`/payslips/${id}`, {
          method: 'DELETE',
          headers: { 'Accept': 'application/json' }
        }).then(async (res) => {
          let body = {};
          try { body = await res.json(); } catch (err) {
            const txt = await res.text().catch(()=>null);
            body = { error: txt || `HTTP ${res.status}` };
          }

          if (!res.ok) {
            actionBtn.disabled = false;
            alert(body.error || `Failed to mark payslip (status ${res.status})`);
            console.error('Mark-paid failed', res.status, body);
            return;
          }

          // remove the table row
          const row = actionBtn.closest('tr');
          if (row) row.remove();

          // decrement pending payslips card if present (assumes second .card-value)
          try {
            const cardValues = document.querySelectorAll('.card-value');
            if (cardValues && cardValues.length >= 2) {
              const pendingEl = cardValues[1];
              const cur = parseInt(pendingEl.textContent || '0', 10);
              pendingEl.textContent = Math.max(0, cur - 1);
            }
          } catch (err) {
            // ignore update errors
          }

          // popup message
          alert('MARKED');
        }).catch(err => {
          actionBtn.disabled = false;
          alert('Request failed: ' + (err.message || err));
          console.error(err);
        });
      }
      return;
    }

    // Edit employee handler (existing)
    const editBtn = e.target.closest('.edit-emp');
    if (editBtn) {
      // existing edit handler code triggers via delegation earlier in file
      return;
    }

    // Delete employee handler
    const delBtn = e.target.closest('.delete-emp');
    if (!delBtn) return;
    e.preventDefault();
    const empId = delBtn.dataset.id;
    if (!empId) return;
    if (!confirm('Delete employee ID ' + empId + '? This cannot be undone.')) return;

    delBtn.disabled = true;
    fetch(`/employees/${empId}`, { method: 'DELETE', headers: { 'Accept': 'application/json' } })
      .then(async (res) => {
        let body = {};
        try { body = await res.json(); } catch (err) { body = { error: 'Invalid server response' }; }

        if (!res.ok) {
          delBtn.disabled = false;
          alert(body.error || body.detail || `Failed to delete (status ${res.status})`);
          console.error('Delete failed', res.status, body);
          return;
        }

        // confirmed deleted on server — update UI
        const row = document.getElementById('emp-row-' + empId);
        if (row) row.remove();

        // update payslip select
        const sel = document.querySelector('#payslip select');
        if (sel) {
          const opt = sel.querySelector(`option[value="${empId}"]`);
          if (opt) opt.remove();
        }

        // update totals
        const totalEl = document.getElementById('totalEmployees');
        if (totalEl) {
          const cur = parseInt(totalEl.textContent || '0', 10);
          totalEl.textContent = Math.max(0, cur - 1);
        }
      })
      .catch(err => {
        delBtn.disabled = false;
        alert('Request failed: ' + (err.message || err));
        console.error(err);
      });
  });

  // New Employee modal handlers
  const newForm = document.getElementById('newEmployeeForm');
  const newModal = document.getElementById('newEmployeeModal');
  const cancelBtn = document.getElementById('cancelNewEmployee');
  if (cancelBtn) cancelBtn.addEventListener('click', () => { if (newModal) newModal.style.display = 'none'; });

  if (newForm) {
    newForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const msg = document.getElementById('newEmployeeMsg');
      msg.style.display = 'none';

      const form = newForm;
      const payload = {
        // only employees table fields — do NOT send user_id or any users-related field
        name: (form.elements['name'].value || '').trim(),
        email: (form.elements['email'].value || '').trim() || null,
        phone: (form.elements['phone'].value || '').trim() || null,
        designation: (form.elements['designation'].value || '').trim() || null,
        department: (form.elements['department'].value || '').trim() || null,
        join_date: (form.elements['join_date'].value || '') || null,
        salary: parseFloat(form.elements['salary'].value || 0) || 0
      };

      if (!payload.name) {
        msg.textContent = 'Name is required.';
        msg.style.display = '';
        return;
      }

      try {
        const res = await fetch('/employees', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(payload)
        });
        const j = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(j.error || j.detail || 'Server error');

        // prepend new row to Manage Employees table
        const tbody = document.querySelector('#employees .table tbody');
        if (tbody) {
          const tr = document.createElement('tr');
          tr.id = 'emp-row-' + j.id;
          tr.innerHTML = `<td>${j.id}</td>
                          <td class="emp-username">${j.name}</td>
                          <td class="emp-role">employee</td>
                          <td>
                            <button type="button" class="mini edit-emp" data-id="${j.id}">Edit</button>
                            <button type="button" class="mini delete-emp" data-id="${j.id}">Delete</button>
                          </td>`;
          tbody.prepend(tr);
        }

        // add to payslip select
        const sel = document.querySelector('#payslip select');
        if (sel) {
          const opt = document.createElement('option');
          opt.value = j.id;
          opt.textContent = j.name;
          sel.appendChild(opt);
        }

        const totalEl = document.getElementById('totalEmployees');
        if (totalEl) totalEl.textContent = parseInt(totalEl.textContent || '0', 10) + 1;

        if (newModal) newModal.style.display = 'none';
        newForm.reset();
      } catch (err) {
        msg.textContent = err.message || 'Failed to add employee';
        msg.style.display = '';
      }
    });
  }

  // close modal by click outside dialog
  if (newModal) {
    newModal.addEventListener('click', (e) => {
      if (e.target === newModal) newModal.style.display = 'none';
    });
  }

  // Edit employee: open modal, fetch data, submit update (employees table fields)
  const editModal = document.getElementById('editEmployeeModal');
  const editForm = document.getElementById('editEmployeeForm');
  const cancelEdit = document.getElementById('cancelEditEmployee');

  // open modal when Edit clicked (delegation)
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.edit-emp');
    if (!btn) return;
    const id = btn.dataset.id;
    e.preventDefault();
    try {
      const res = await fetch(`/employees/${id}`, { method: 'GET', headers: { 'Accept': 'application/json' } });
      if (!res.ok) throw new Error('Failed to fetch employee');
      const data = await res.json();
      // populate form with employees fields
      editForm.elements['id'].value = data.id;
      editForm.elements['name'].value = data.name || '';
      editForm.elements['email'].value = data.email || '';
      editForm.elements['phone'].value = data.phone || '';
      editForm.elements['designation'].value = data.designation || '';
      editForm.elements['department'].value = data.department || '';
      // ensure join_date is YYYY-MM-DD or empty
      editForm.elements['join_date'].value = data.join_date || '';
      editForm.elements['salary'].value = (data.salary != null) ? data.salary : '';
      if (editModal) editModal.style.display = 'flex';
      editForm.elements['name'].focus();
    } catch (err) {
      alert('Could not load employee: ' + err.message);
    }
  });

  if (cancelEdit) cancelEdit.addEventListener('click', () => { if (editModal) editModal.style.display = 'none'; });

  if (editForm) {
    editForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const msg = document.getElementById('editEmployeeMsg');
      msg.style.display = 'none';
      const id = editForm.elements['id'].value;
      const payload = {
        name: editForm.elements['name'].value.trim(),
        email: editForm.elements['email'].value.trim() || null,
        phone: editForm.elements['phone'].value.trim() || null,
        designation: editForm.elements['designation'].value.trim() || null,
        department: editForm.elements['department'].value.trim() || null,
        join_date: editForm.elements['join_date'].value || null,
        salary: parseFloat(editForm.elements['salary'].value || 0) || 0
      };
      if (!payload.name) {
        msg.textContent = 'Name required';
        msg.style.display = '';
        return;
      }
      try {
        const res = await fetch(`/employees/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const j = await res.json().catch(()=>{});
        if (!res.ok) throw new Error(j.error || 'Update failed');

        // update table row in Manage Employees
        const row = document.getElementById('emp-row-' + id);
        if (row) {
          const nameEl = row.querySelector('.emp-username');
          if (nameEl) nameEl.textContent = payload.name;
        }
        if (editModal) editModal.style.display = 'none';
      } catch (err) {
        msg.textContent = err.message || 'Failed to update';
        msg.style.display = '';
      }
    });
  }

  // close modals by clicking outside
  if (editModal) {
    editModal.addEventListener('click', (e) => { if (e.target === editModal) editModal.style.display = 'none'; });
  }

  const generateBtn = document.getElementById('generatePayslipBtn');
  const empSelect = document.getElementById('payslipEmployee');
  const successModal = document.getElementById('payslipSuccessModal');
  const successText = document.getElementById('payslipSuccessText');
  const closeSuccess = document.getElementById('closePayslipSuccess');

  async function generatePayslip() {
    if (!empSelect || !payslipMonth) return alert('Form not ready');
    const empId = empSelect.value;
    const period = payslipMonth.value;
    if (!empId || !period) return alert('Select employee and month.');

    generateBtn.disabled = true;
    try {
      const res = await fetch('/payslips', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ employee_id: parseInt(empId, 10), period: period })
      });
      const body = await res.json().catch(async () => {
        const txt = await res.text().catch(() => '');
        return { error: txt || `HTTP ${res.status}` };
      });

      if (!res.ok) {
        alert(body.error || `Failed to generate payslip (${res.status})`);
        return;
      }

      const empName = empSelect.options[empSelect.selectedIndex].text || 'Employee';
      successText.textContent = `Payslip generated successfully for ${empName} (${period}). It will be approved by Finance Department.`;
      if (successModal) successModal.style.display = 'flex';

      // optional: refresh pending payslips UI or call refreshEmployees() if implemented
      if (typeof refreshEmployees === 'function') refreshEmployees();
    } catch (err) {
      console.error(err);
      alert('Request failed: ' + (err.message || err));
    } finally {
      generateBtn.disabled = false;
    }
  }

  if (generateBtn) generateBtn.addEventListener('click', generatePayslip);
  // fallback: handle form submit if JS attaches elsewhere
  const form = document.getElementById('generatePayslipForm');
  if (form) form.addEventListener('submit', (e) => { e.preventDefault(); generatePayslip(); });

  if (closeSuccess) closeSuccess.addEventListener('click', () => { if (successModal) successModal.style.display = 'none'; });
  if (successModal) successModal.addEventListener('click', (e) => { if (e.target === successModal) successModal.style.display = 'none'; });
});

// small helper to avoid XSS when inserting innerHTML for names
function escapeHtml(s) {
  return String(s || '').replace(/[&<>"'`=\/]/g, function (c) {
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','/':'&#x2F;','=':'&#x3D;','`':'&#x60;'}[c];
  });
}

// add refreshEmployees() to populate/manage the employees table and payslip select
async function refreshEmployees() {
  try {
    const res = await fetch('/employees', { headers: { 'Accept': 'application/json' } });
    if (!res.ok) {
      console.error('Failed to fetch employees', res.status);
      return;
    }
    const payload = await res.json();
    const employees = payload.employees || [];

    // render manage employees table
    const tbody = document.querySelector('#employees .table tbody');
    if (tbody) {
      tbody.innerHTML = '';
      for (const emp of employees) {
        const displayName = emp.name || emp.username || '';
        const tr = document.createElement('tr');
        tr.id = 'emp-row-' + emp.id;
        tr.innerHTML = `<td>${emp.id}</td>
                        <td class="emp-username">${escapeHtml(displayName)}</td>
                        <td class="emp-role">employee</td>
                        <td>
                          <button type="button" class="mini edit-emp" data-id="${emp.id}">Edit</button>
                          <button type="button" class="mini delete-emp" data-id="${emp.id}">Delete</button>
                        </td>`;
        tbody.appendChild(tr);
      }
    }

    // render payslip select options
    const sel = document.querySelector('#payslip select');
    if (sel) {
      sel.innerHTML = '<option value="">— select employee —</option>';
      for (const emp of employees) {
        const opt = document.createElement('option');
        opt.value = emp.id;
        opt.textContent = emp.name || emp.username || emp.id;
        sel.appendChild(opt);
      }
    }
  } catch (err) {
    console.error('refreshEmployees error', err);
  }
}

// call on load
refreshEmployees();

// if your create/edit/delete handlers updated earlier, replace local DOM updates with:
// await refreshEmployees();
// (optional) call refreshEmployees() after successful create/edit/delete/payslip generation

// call this after DOM ready and after lists are re-rendered
function removePendingNameColumn() {
  try {
    // find sections that contain a heading with "pending payslip" (case-insensitive)
    const sections = Array.from(document.querySelectorAll('section, .panel'));
    for (const sec of sections) {
      const heading = sec.querySelector('h1, h2, h3, h4, h5, h6');
      if (!heading) continue;
      if (!/pending\s+payslips?/i.test(heading.textContent)) continue;
      const table = sec.querySelector('table');
      if (!table) continue;
      const thead = table.querySelector('thead');
      if (!thead) continue;
      const ths = Array.from(thead.querySelectorAll('th'));
      // find index of name/employee column
      const idx = ths.findIndex(th => /^(employee|name)$/i.test(th.textContent.trim()));
      if (idx === -1) {
        // also try partial match
        const idx2 = ths.findIndex(th => /employee|name/i.test(th.textContent));
        if (idx2 === -1) continue;
        removeColumn(table, idx2);
      } else {
        removeColumn(table, idx);
      }
    }
  } catch (err) {
    console.error('removePendingNameColumn error', err);
  }

  function removeColumn(table, colIndex) {
    // remove header cell
    const headerRow = table.querySelector('thead tr');
    if (headerRow && headerRow.children[colIndex]) headerRow.children[colIndex].remove();
    // remove each body cell in that column
    table.querySelectorAll('tbody tr').forEach(tr => {
      if (tr.children[colIndex]) tr.children[colIndex].remove();
    });
  }
}

document.addEventListener('DOMContentLoaded', function () {
  // ensure pending name column removed after initial render
  removePendingNameColumn();
  // if refreshEmployees is used later, it should call removePendingNameColumn() after finish
});

// at end of refreshEmployees() add:
  // after rendering pending table(s) and employees lists
  removePendingNameColumn();