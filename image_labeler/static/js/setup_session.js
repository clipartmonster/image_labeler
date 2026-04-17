if (window.location.pathname === '/label_images/setup_session/')
document.addEventListener('DOMContentLoaded', function(){

    const selected_options = document.getElementById('selected_options')
    const saved_rule  = selected_options.getAttribute('rule_index')
    const saved_batch = selected_options.getAttribute('batch_id')
    const saved_task  = selected_options.getAttribute('task_type')

    // ── Task type ──────────────────────────────────────────────────────────
    document.querySelectorAll('.task_type').forEach(el => {
        if (el.getAttribute('task_type') == saved_task) el.classList.add('selected')
        el.addEventListener('click', () => select_task_type(el.getAttribute('task_type')))
    })

    // ── Rule index ─────────────────────────────────────────────────────────
    document.querySelectorAll('.rule_option').forEach(el => {
        if (el.getAttribute('rule_index') === saved_rule) el.classList.add('selected')
        el.addEventListener('click', () => {
            // highlight
            document.querySelectorAll('.rule_option').forEach(r => r.classList.remove('selected'))
            el.classList.add('selected')
            filterBatchOptions(el.getAttribute('rule_index'))
            loadReconcileCount(el.getAttribute('rule_index'))
        })
    })

    // ── Batch options (revealed after rule pick) ────────────────────────────
    document.querySelectorAll('.batch_option').forEach(el => {
        el.addEventListener('click', () => {
            document.querySelectorAll('.batch_option').forEach(b => b.classList.remove('selected'))
            el.classList.add('selected')
            filterSubBatches(el.getAttribute('batch_id'), el.getAttribute('rule_index'))
        })
    })

    // ── Sub-batch indicators ────────────────────────────────────────────────
    document.querySelectorAll('.batch.indicator:not(.container)').forEach(el => {
        el.addEventListener('click', () => select_batch_option(el))
    })
    document.querySelectorAll('.view_button').forEach(el => {
        el.addEventListener('click', () => go_to_view_page(el))
    })

    // ── Labeler ────────────────────────────────────────────────────────────
    const labeler_control = document.getElementById('labeler_id')
    labeler_control.addEventListener('click', () => toggle_add_a_name_field(labeler_control))
    document.getElementById('add_a_name_field').addEventListener('keydown', add_labeler_name)
    labeler_control.value = selected_options.getAttribute('labeler_id')

    // ── Restore state from URL params (only if matching elements exist) ───
    if (saved_rule) {
        const savedRuleBtn = document.querySelector(`.rule_option[rule_index="${saved_rule}"]`)
        if (savedRuleBtn) {
            savedRuleBtn.classList.add('selected')
            filterBatchOptions(saved_rule)
            loadReconcileCount(saved_rule)
            if (saved_batch) {
                const matchedBatch = document.querySelector(
                    `.batch_option[batch_id="${saved_batch}"][rule_index="${saved_rule}"]`
                )
                if (matchedBatch) {
                    matchedBatch.classList.add('selected')
                    filterSubBatches(saved_batch, saved_rule)
                }
            }
        }
    }

})


// Toggle the "+" sub-batch trigger when the user has picked a task_type.
function syncAddSubBatchBtn() {
    const btn = document.getElementById('add_sub_batch_btn')
    if (!btn) return
    const taskType = document.getElementById('selected_options').getAttribute('task_type')
    btn.style.display = taskType ? 'block' : 'none'
}

// Show batch buttons that match the chosen rule_index; hide the rest.
// Also collapses the sub-batch grid until a batch is picked.
function filterBatchOptions(rule_index) {
    document.querySelectorAll('.batch_option').forEach(el => {
        el.style.display = el.getAttribute('rule_index') === String(rule_index) ? 'block' : 'none'
        el.classList.remove('selected')
    })
    document.querySelectorAll('.batch.indicator.container').forEach(el => {
        el.style.display = 'none'
    })
    syncAddSubBatchBtn()
}


// Show sub-batch containers that match the chosen batch_id + rule_index.
function filterSubBatches(batch_id, rule_index) {
    document.querySelectorAll('.batch.indicator.container').forEach(el => {
        el.style.display = (
            el.getAttribute('batch_id')    === String(batch_id) &&
            el.getAttribute('rule_index')  === String(rule_index)
        ) ? 'flex' : 'none'
    })
    syncAddSubBatchBtn()
}

function loadReconcileCount(rule_index) {
    const countText = document.getElementById('reconcile_count_text')
    const btn       = document.getElementById('reconcile_btn')
    if (!countText) { console.error('reconcile_count_text not found'); return }

    try {
        const task_type  = document.getElementById('selected_options').getAttribute('task_type')
        const labeler_id = document.getElementById('labeler_id').value
            || document.getElementById('selected_options').getAttribute('labeler_id')

        if (!task_type || rule_index == null || rule_index === '') {
            countText.textContent = 'Select a rule to see reconciliation status.'
            if (btn) btn.style.display = 'none'
            return
        }
        countText.textContent = 'Loading…'
        if (btn) btn.style.display = 'none'

        const url = `/get_reconcile_count/?task_type=${encodeURIComponent(task_type)}&rule_index=${encodeURIComponent(rule_index)}`

        fetch(url)
            .then(r => r.text().then(t => ({ status: r.status, t })))
            .then(({ status, t }) => {
                let data
                try { data = JSON.parse(t) } catch (e) {
                    countText.textContent = `Server error ${status}: ${t.slice(0, 200)}`
                    return
                }
                const n = data.disputed_count
                if (typeof n !== 'number') {
                    countText.textContent = `Bad response (${status}): ${t.slice(0, 200)}`
                    return
                }
                if (n === 0) {
                    countText.textContent = `No assets currently need reconciliation for Rule ${rule_index}.`
                    if (btn) btn.style.display = 'none'
                } else {
                    countText.textContent = `${n} asset${n === 1 ? '' : 's'} need reconciliation for Rule ${rule_index}.`
                    if (btn) {
                        btn.style.display = 'inline-block'
                        btn.onclick = () => {
                            window.location.href = `/label_images/reconcile_labels/?task_type=${encodeURIComponent(task_type)}`
                                + `&rule_indexes=${encodeURIComponent(JSON.stringify([parseInt(rule_index)]))}`
                                + `&labeler_id=${encodeURIComponent(labeler_id)}`
                        }
                    }
                }
            })
            .catch(err => {
                countText.textContent = 'Fetch failed: ' + (err && err.message ? err.message : err)
            })
    } catch (e) {
        countText.textContent = 'JS error: ' + (e && e.message ? e.message : e)
    }
}


function select_task_type(task_type) {
    const labeler_id = document.getElementById('labeler_id').value
        || document.getElementById('selected_options').getAttribute('labeler_id')
    window.location.href = window.location.origin
        + '/label_images/setup_session/?task_type=' + encodeURIComponent(task_type)
        + '&labeler_id=' + encodeURIComponent(labeler_id)
}


function go_to_view_page(view_button){
    const container = view_button.closest('.batch.indicator.container')
    const task_type  = document.getElementById('selected_options').getAttribute('task_type')
    const rule_index = container.getAttribute('rule_index')
    const batch_id   = container.getAttribute('batch_id')

    window.location.href = window.location.origin
        + '/label_images/view_batch_labels/?task_type=' + task_type
        + '&rule_index=' + rule_index
        + '&batch_id='   + batch_id
}

function select_batch_option(selected_batch_option){

    batch_options = document.querySelectorAll('.batch.indicator:not(.container')

    batch_options.forEach(batch_option => {
        batch_option.classList.remove('selected')
    })

    selected_batch_option.classList.add('selected')

}


function add_labeler_name(event) {
    
    entered_name = event.target.value.trim()
    const labeler_control = document.getElementById('labeler_id');

    if (event.key === 'Enter') {
        
        const newOption = document.createElement('option');
        newOption.value = entered_name;
        newOption.textContent = entered_name;

        // Append the new option to the select element
        labeler_control.appendChild(newOption);

        const add_labeler_option = labeler_control.querySelector('option[value="add_a_labeler"]');
        labeler_control.appendChild(add_labeler_option); // Move "Add Labeler" option to the end

        // Optionally, select the newly added option
        labeler_control.value = entered_name;

        toggle_add_a_name_field(labeler_control)
    } else if (event.key === 'Escape') {
        console.log('here')
        event.target.style.display = 'none'
    }

}

function toggle_add_a_name_field(labeler_control){

    const add_name_field = document.getElementById('add_a_name_field');
    console.log(labeler_control.value)
    console.log(add_name_field.style.display)

    if (labeler_control.value === 'add_a_labeler') {
        add_name_field.style.display = 'block'; // Show the text input
    } else {
        add_name_field.style.display = 'none'; // Hide the text input
    }

}



function show_images_wo_labels(){

    selected_batch_container = document.querySelector('.batch.indicator.selected')
    .parentElement

    task_type = selected_batch_container.getAttribute('task_type')
    batch_id = selected_batch_container.getAttribute('batch_id')
    rule_index = selected_batch_container.getAttribute('rule_index')
    large_sub_batch = selected_batch_container.getAttribute('large_sub_batch')

    console.log(task_type,batch_id,rule_index,large_sub_batch)

    if (task_type == 'line_width_type') {
        link_stem = '/label_images/select_line_widths/'
    } else {
        link_stem = '/label_images/mturk_redirect/'
    }


     href = window.location.origin
     + link_stem  
     + '?task_type='+task_type
     + '&label_source=Internal'  
     + '&labeler_id=' + document.getElementById('labeler_id').value 
     + '&rule_indexes=%5B'+ rule_index +'%5D'
     + '&batch_id='+ batch_id
     + '&large_sub_batch=' + large_sub_batch
    
     window.location.href = href;

}


function show_batch_indicator_container(rule_index){

    console.log('here')

    //remove selected class from the selected batch indicators
    if (document.querySelector('.batch.indicator.selected')) {

        document.querySelector('.batch.indicator.selected')
        .classList.remove('selected')

    }


    batch_option_containers = document.querySelectorAll('.batch.indicator.container')

    batch_option_containers.forEach(batch_option_container => {
        batch_option_container.style.display = 'none'
    })

    batch_option_containers[rule_index - 1].style.display = 'flex'

}


// ============================================================
// Add Sub-batch modal
// ============================================================

(function () {
    // active rule_index chosen inside the modal (string)
    let _modalRuleIndex = null;

    // ----- helpers -----
    function getSelectedTaskType() {
        const sel = document.querySelectorAll('.selected');
        let task_type = null;
        sel.forEach(el => {
            if (el.classList.contains('task_type')) task_type = el.getAttribute('task_type');
        });
        return task_type || (document.getElementById('selected_options') || {}).getAttribute?.('task_type');
    }

    // Collect all unique rule_indexes available on this page (from .rule_option elements)
    function getAvailableRuleIndexes() {
        const seen = new Set();
        const result = [];
        document.querySelectorAll('.rule_option').forEach(el => {
            const ri = el.getAttribute('rule_index');
            if (ri && !seen.has(ri)) { seen.add(ri); result.push(ri); }
        });
        return result.sort((a, b) => Number(a) - Number(b));
    }

    function syncAddButton() {
        const btn = document.getElementById('add_sub_batch_btn');
        if (!btn) return;
        // Show + button as long as we have a task_type (rule picked inside modal)
        btn.style.display = getSelectedTaskType() ? 'block' : 'none';
    }

    // syncAddButton is called directly from filterBatchOptions / filterSubBatches

    // ----- modal open / close -----
    function openModal() {
        _modalRuleIndex = null;
        document.getElementById('sub_batch_step2').style.display = 'none';
        document.getElementById('sub_batch_status').textContent = '';
        buildRuleIndexButtons();
        document.getElementById('sub_batch_modal_overlay').style.display = 'flex';
    }

    function closeModal() {
        document.getElementById('sub_batch_modal_overlay').style.display = 'none';
    }

    // ----- step 1: render rule index buttons -----
    function buildRuleIndexButtons() {
        const container = document.getElementById('rule_index_buttons');
        const indexes   = getAvailableRuleIndexes();
        container.innerHTML = indexes.length
            ? indexes.map(ri => `<button class="rule_idx_btn" data-ri="${ri}">Rule ${ri}</button>`).join('')
            : '<span style="color:#f38ba8; font-size:.85rem;">No rules found on page.</span>';

        container.querySelectorAll('.rule_idx_btn').forEach(btn => {
            btn.addEventListener('click', () => selectRuleIndex(btn, btn.dataset.ri));
        });
    }

    function selectRuleIndex(btn, ri) {
        // highlight selection
        document.querySelectorAll('.rule_idx_btn').forEach(b => b.classList.remove('active_rule'));
        btn.classList.add('active_rule');
        _modalRuleIndex = ri;

        // show step 2 and load batch/model options
        document.getElementById('sub_batch_step2').style.display = 'block';
        loadBatchAndModelOptions(ri);
        setSource('model');
    }

    // ----- step 2: load batch capacities + model versions for chosen rule -----
    function loadBatchAndModelOptions(rule_index) {
        const task_type = getSelectedTaskType();
        if (!task_type || !rule_index) return;

        const mvSel    = document.getElementById('model_version_select');
        const batchSel = document.getElementById('target_batch_select');

        mvSel.innerHTML    = '<option value="">Loading…</option>';
        batchSel.innerHTML = '<option value="">Loading…</option>';
        document.getElementById('batch_capacity_note').textContent = '';

        fetch(`/get_sub_batch_options/?task_type=${encodeURIComponent(task_type)}&rule_index=${encodeURIComponent(rule_index)}`)
            .then(r => r.json())
            .then(data => {
                if (data.status !== 'success') {
                    mvSel.innerHTML    = '<option value="">Error loading</option>';
                    batchSel.innerHTML = '<option value="">Error loading</option>';
                    return;
                }

                mvSel.innerHTML = data.model_versions.length
                    ? data.model_versions.map(v => `<option value="${v}">${v}</option>`).join('')
                    : '<option value="">No models available</option>';

                // store capacities on the select for the change handler
                batchSel._capacities = data.batch_capacities;
                batchSel.innerHTML = data.batch_capacities.length
                    ? data.batch_capacities.map(b => {
                        const label = b.has_room
                            ? `Batch ${b.batch_id}  (${b.asset_count} / 20000)`
                            : `Batch ${b.batch_id}  (FULL — ${b.asset_count} / 20000)`;
                        return `<option value="${b.batch_id}" ${b.has_room ? '' : 'disabled'}>${label}</option>`;
                    }).join('')
                    : '<option value="">No batches yet — first batch will be created</option>';

                updateCapacityNote();
            })
            .catch(() => {
                mvSel.innerHTML    = '<option value="">Error</option>';
                batchSel.innerHTML = '<option value="">Error</option>';
            });
    }

    function updateCapacityNote() {
        const batchSel = document.getElementById('target_batch_select');
        const note     = document.getElementById('batch_capacity_note');
        const caps     = batchSel._capacities || [];
        const chosen   = caps.find(b => String(b.batch_id) === batchSel.value);
        if (!chosen) { note.textContent = ''; return; }
        const remaining = 20000 - chosen.asset_count;
        note.textContent = `${remaining} slots remaining in this batch.`;
        note.style.color = remaining >= 500 ? '#a6adc8' : '#f38ba8';
    }

    // ----- source toggle -----
    function setSource(src) {
        const modelSec  = document.getElementById('model_options_section');
        const modelBtn  = document.getElementById('src_model_btn');
        const randomBtn = document.getElementById('src_random_btn');
        if (src === 'model') {
            modelSec.style.display = 'block';
            modelBtn.classList.add('active_src');
            randomBtn.classList.remove('active_src');
        } else {
            modelSec.style.display = 'none';
            randomBtn.classList.add('active_src');
            modelBtn.classList.remove('active_src');
        }
    }

    // ----- submit -----
    function submitSubBatch() {
        const task_type    = getSelectedTaskType();
        const rule_index   = _modalRuleIndex;
        const source       = document.getElementById('src_model_btn').classList.contains('active_src') ? 'model' : 'random';
        const batch_id     = document.getElementById('target_batch_select').value;
        const model_version = document.getElementById('model_version_select').value;
        const prob_min     = parseFloat(document.getElementById('prob_min_input').value);
        const prob_max     = parseFloat(document.getElementById('prob_max_input').value);

        const statusEl  = document.getElementById('sub_batch_status');
        const submitBtn = document.getElementById('sub_batch_submit_btn');

        if (!rule_index) { statusEl.style.color = '#f38ba8'; statusEl.textContent = 'Please select a rule index.'; return; }
        if (!batch_id)   { statusEl.style.color = '#f38ba8'; statusEl.textContent = 'Please select a target batch.'; return; }
        if (source === 'model' && !model_version) { statusEl.style.color = '#f38ba8'; statusEl.textContent = 'Please select a model version.'; return; }

        submitBtn.disabled = true;
        statusEl.style.color = '#a6adc8';
        statusEl.textContent = 'Creating sub-batch…';

        const payload = { task_type, rule_index: parseInt(rule_index), batch_id: parseInt(batch_id), source };
        if (source === 'model') Object.assign(payload, { model_version, prob_min, prob_max });

        fetch('/create_sub_batch/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
            .then(r => r.text().then(text => ({ status: r.status, text })))
            .then(({ status, text }) => {
                submitBtn.disabled = false;
                let data;
                try { data = JSON.parse(text); } catch(e) {
                    statusEl.style.color = '#f38ba8';
                    statusEl.textContent = `Server error (${status}): ${text.slice(0, 200)}`;
                    return;
                }
                if (data.status === 'success') {
                    statusEl.style.color = '#a6e3a1';
                    statusEl.textContent = data.explanation;
                    setTimeout(() => window.location.reload(), 1200);
                } else {
                    statusEl.style.color = '#f38ba8';
                    statusEl.textContent = data.explanation || data.detail || `Error ${status}`;
                }
            })
            .catch(err => {
                submitBtn.disabled = false;
                statusEl.style.color = '#f38ba8';
                statusEl.textContent = 'Request failed: ' + err.message;
            });
    }

    // ----- bind on DOMContentLoaded -----
    document.addEventListener('DOMContentLoaded', function () {
        syncAddButton();

        const trigger   = document.getElementById('add_sub_batch_btn');
        const closeBtn  = document.getElementById('sub_batch_modal_close');
        const overlay   = document.getElementById('sub_batch_modal_overlay');
        const modelBtn  = document.getElementById('src_model_btn');
        const randBtn   = document.getElementById('src_random_btn');
        const submitBtn = document.getElementById('sub_batch_submit_btn');
        const batchSel  = document.getElementById('target_batch_select');

        if (trigger)   trigger.addEventListener('click', openModal);
        if (closeBtn)  closeBtn.addEventListener('click', closeModal);
        if (overlay)   overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });
        if (modelBtn)  modelBtn.addEventListener('click', () => setSource('model'));
        if (randBtn)   randBtn.addEventListener('click',  () => setSource('random'));
        if (submitBtn) submitBtn.addEventListener('click', submitSubBatch);
        if (batchSel)  batchSel.addEventListener('change', updateCapacityNote);
    });
})();