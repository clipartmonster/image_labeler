if (window.location.pathname === '/label_images/setup_session/')
document.addEventListener('DOMContentLoaded', function(){

    const data = window.__setupData;
    const initTaskType = data.taskType;
    const initRuleIndex = String(data.ruleIndex);
    const labelerId = data.labelerId;
    const ruleStats = data.ruleStats || [];
    const subBatchStats = data.subBatchStats || [];

    let selectedTaskType = null;
    let selectedRuleIndex = null;
    let selectedBatchId = null;
    let selectedSubBatch = null;

    const ruleSection = document.getElementById('rule-section');
    const ruleRow = document.getElementById('rule-row');
    const batchSection = document.getElementById('batch-section');
    const batchRow = document.getElementById('batch-row');
    const subBatchSection = document.getElementById('sub-batch-section');
    const subBatchGrid = document.getElementById('sub-batch-grid');
    const startBtn = document.getElementById('start-btn');

    // ─── Step 1: Task Type ───
    document.querySelectorAll('.task-type-pill').forEach(pill => {
        if (pill.dataset.taskType === initTaskType) {
            pill.classList.add('selected');
            selectedTaskType = initTaskType;
        }
        pill.addEventListener('click', () => {
            if (pill.dataset.taskType === selectedTaskType) return;
            window.location.href = '/label_images/setup_session/?task_type=' + pill.dataset.taskType;
        });
    });

    // ─── Step 2: Rules (deduplicated by rule_index) ───
    function buildRules() {
        ruleRow.innerHTML = '';
        const seen = {};

        ruleStats.forEach(rs => {
            const ri = String(rs.rule_index);
            if (!seen[ri]) {
                seen[ri] = { rule_index: ri, title: rs.title, completed: 0, total: 0 };
            }
            seen[ri].completed += (rs.completed_labels || 0);
            seen[ri].total += (rs.samples || 0);
        });

        const uniqueRules = Object.values(seen);
        if (uniqueRules.length === 0) {
            document.getElementById('no-rules-msg').style.display = '';
            return;
        }

        uniqueRules.sort((a, b) => Number(a.rule_index) - Number(b.rule_index));

        uniqueRules.forEach(rule => {
            const card = document.createElement('div');
            card.className = 'rule-card';
            card.dataset.ruleIndex = rule.rule_index;
            card.innerHTML =
                '<div class="rule-num">Rule ' + rule.rule_index + '</div>' +
                '<div class="rule-title">' + (rule.title || '') + '</div>' +
                '<div class="rule-progress">' + rule.completed + ' / ' + rule.total + ' labeled</div>';
            card.addEventListener('click', () => selectRule(rule.rule_index));
            ruleRow.appendChild(card);
        });
    }

    function selectRule(ruleIndex) {
        selectedRuleIndex = String(ruleIndex);
        selectedBatchId = null;
        selectedSubBatch = null;

        ruleRow.querySelectorAll('.rule-card').forEach(c => {
            c.classList.toggle('selected', c.dataset.ruleIndex === selectedRuleIndex);
        });

        buildBatches();
        subBatchSection.style.display = 'none';
        subBatchGrid.innerHTML = '';
        updateStartBtn();
    }

    // ─── Step 3: Batches (unique batch_ids that have sub-batches for this rule) ───
    function buildBatches() {
        batchRow.innerHTML = '';
        batchSection.style.display = '';

        const batchIds = new Set();
        subBatchStats.forEach(sb => {
            if (String(sb.rule_index) === selectedRuleIndex) {
                batchIds.add(String(sb.batch_id));
            }
        });

        const sorted = Array.from(batchIds).sort((a, b) => Number(a) - Number(b));

        if (sorted.length === 0) {
            document.getElementById('no-batches-msg').style.display = '';
            return;
        }
        document.getElementById('no-batches-msg').style.display = 'none';

        sorted.forEach(bid => {
            const pill = document.createElement('div');
            pill.className = 'pill';
            pill.dataset.batchId = bid;
            pill.textContent = 'Batch ' + bid;
            pill.addEventListener('click', () => selectBatch(bid));
            batchRow.appendChild(pill);
        });

        if (sorted.length === 1) {
            selectBatch(sorted[0]);
        }
    }

    function selectBatch(batchId) {
        selectedBatchId = String(batchId);
        selectedSubBatch = null;

        batchRow.querySelectorAll('.pill').forEach(p => {
            p.classList.toggle('selected', p.dataset.batchId === selectedBatchId);
        });

        buildSubBatches();
        updateStartBtn();
    }

    // ─── Step 4: Sub-Batches ───
    function buildSubBatches() {
        subBatchGrid.innerHTML = '';
        subBatchSection.style.display = '';

        const matching = subBatchStats.filter(sb =>
            String(sb.rule_index) === selectedRuleIndex &&
            String(sb.batch_id) === selectedBatchId
        ).sort((a, b) => Number(a.large_sub_batch) - Number(b.large_sub_batch));

        if (matching.length === 0) {
            document.getElementById('no-sub-msg').style.display = '';
            return;
        }
        document.getElementById('no-sub-msg').style.display = 'none';

        matching.forEach(sb => {
            const card = document.createElement('div');
            let statusClass = '';
            if (sb.percent_remaining === 0) statusClass = ' done';
            else if (sb.one_label === 0) statusClass = ' partial';

            card.className = 'sub-batch-card' + statusClass;
            card.dataset.largeSubBatch = sb.large_sub_batch;
            card.dataset.batchId = sb.batch_id;
            card.dataset.ruleIndex = sb.rule_index;

            let detail = '';
            if (sb.percent_remaining === 0) {
                detail = 'Done';
            } else {
                detail = (sb.no_labels || 0) + ' unlabeled &middot; ' + (sb.one_label || 0) + ' need 2nd';
            }

            card.innerHTML =
                '<div class="sb-num">Sub-batch ' + sb.large_sub_batch + '</div>' +
                '<div class="sb-stat">' + (sb.completed_labels || 0) + ' / ' + (sb.samples || 0) + '</div>' +
                '<div class="sb-detail">' + detail + '</div>';

            card.addEventListener('click', () => selectSubBatch(card));
            subBatchGrid.appendChild(card);
        });
    }

    function selectSubBatch(card) {
        subBatchGrid.querySelectorAll('.sub-batch-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        selectedSubBatch = card.dataset.largeSubBatch;
        updateStartBtn();
    }

    function updateStartBtn() {
        startBtn.disabled = !(selectedTaskType && selectedRuleIndex && selectedBatchId && selectedSubBatch);
    }

    // ─── Start Labeling ───
    startBtn.addEventListener('click', function() {
        if (startBtn.disabled) return;

        let linkStem = '/label_images/mturk_redirect/';
        if (selectedTaskType === 'line_width_type') {
            linkStem = '/label_images/select_line_widths/';
        }

        const href = window.location.origin
            + linkStem
            + '?task_type=' + selectedTaskType
            + '&label_source=Internal'
            + '&labeler_id=' + labelerId
            + '&rule_indexes=%5B' + selectedRuleIndex + '%5D'
            + '&batch_id=' + selectedBatchId
            + '&large_sub_batch=' + selectedSubBatch;

        window.location.href = href;
    });

    // ─── Init ───
    if (selectedTaskType) {
        ruleSection.style.display = '';
        buildRules();

        if (initRuleIndex && ruleRow.querySelector('[data-rule-index="' + initRuleIndex + '"]')) {
            selectRule(initRuleIndex);
        }
    }

});
