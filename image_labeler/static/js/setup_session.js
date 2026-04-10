if (window.location.pathname === '/label_images/setup_session/')
document.addEventListener('DOMContentLoaded', function(){

    const opts = document.getElementById('selected_options');
    const initTaskType = opts.dataset.taskType;
    const initRuleIndex = opts.dataset.ruleIndex;
    const labelerId = opts.dataset.labelerId;

    let selectedTaskType = null;
    let selectedBatchId = null;
    let selectedRuleIndex = null;
    let selectedSubBatch = null;

    const ruleSection = document.getElementById('rule-section');
    const batchSection = document.getElementById('batch-section');
    const startBtn = document.getElementById('start-btn');

    // --- Task type pills ---
    const taskPills = document.querySelectorAll('.task-type-pill');
    taskPills.forEach(pill => {
        pill.addEventListener('click', () => selectTaskType(pill.dataset.taskType));
    });

    function selectTaskType(taskType) {
        if (taskType === selectedTaskType) return;

        // Reload with the new task_type so the backend returns fresh rule/batch data
        const url = window.location.origin
            + '/label_images/setup_session/?task_type=' + taskType
            + '&rule_index=' + (initRuleIndex || 1);
        window.location.href = url;
    }

    // Highlight the active task type on load
    taskPills.forEach(pill => {
        if (pill.dataset.taskType === initTaskType) {
            pill.classList.add('selected');
            selectedTaskType = initTaskType;
        }
    });

    // --- Rule cards ---
    const ruleCards = document.querySelectorAll('.rule-card');

    // Show rule section if we have a task type selected
    if (selectedTaskType && ruleCards.length > 0) {
        ruleSection.style.display = '';
    }

    // Filter rules to those matching the selected batch context
    // The API returns rule_index_stats scoped to the task_type already,
    // so we just show them all
    let visibleRules = 0;
    ruleCards.forEach(card => {
        card.style.display = '';
        visibleRules++;
        card.addEventListener('click', () => selectRule(card));
    });

    if (visibleRules === 0) {
        document.getElementById('no-rules-msg').style.display = '';
    }

    // Auto-select rule on load if initRuleIndex matches
    ruleCards.forEach(card => {
        if (card.dataset.ruleIndex === String(initRuleIndex)) {
            selectRule(card, true);
        }
    });

    function selectRule(card, skipBatchReset) {
        ruleCards.forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        selectedRuleIndex = card.dataset.ruleIndex;
        selectedBatchId = card.dataset.batchId;

        showBatches();
        if (!skipBatchReset) {
            selectedSubBatch = null;
            updateStartBtn();
        }
    }

    // --- Batch cards ---
    const batchCards = document.querySelectorAll('.batch-card');
    batchCards.forEach(card => {
        card.style.display = 'none';
        card.addEventListener('click', () => selectBatch(card));
    });

    function showBatches() {
        batchSection.style.display = '';
        let visible = 0;

        batchCards.forEach(card => {
            if (card.dataset.batchId === selectedBatchId &&
                card.dataset.ruleIndex === selectedRuleIndex) {
                card.style.display = '';
                visible++;
            } else {
                card.style.display = 'none';
                card.classList.remove('selected');
            }
        });

        document.getElementById('no-batches-msg').style.display = visible === 0 ? '' : 'none';
    }

    function selectBatch(card) {
        batchCards.forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        selectedSubBatch = card.dataset.largeSubBatch;
        updateStartBtn();
    }

    function updateStartBtn() {
        startBtn.disabled = !(selectedTaskType && selectedRuleIndex && selectedSubBatch);
    }

    // --- Start labeling ---
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

});
