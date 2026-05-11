
if (window.location.pathname === '/label_images/view_batch_labels/') {

    document.addEventListener('DOMContentLoaded', function () {

        let slider_controls = document.querySelectorAll('.input_slider.prediction_labels')

        slider_controls.forEach(slider_control => {
            slider_control.addEventListener('input', function () {
                toggle_slider_control(slider_control)
            })
        })

        let label_filter_options = document.querySelectorAll('.label_filter_option.batch_labels')

        label_filter_options.forEach(option => {
            option.addEventListener('click', function() {
                let filter = this.getAttribute('label_filter');
                let url = new URL(window.location.href);
                url.searchParams.set('label_filter', filter);
                window.location.href = url.toString();
            })
            
            const urlParams = new URLSearchParams(window.location.search);
            const current_filter = urlParams.get('label_filter') || 'only_yes';
            if (option.getAttribute('label_filter') == current_filter) {
                option.classList.add('selected');
            }
        })

        const task_type_select = document.getElementById('task_type_select');
        if (task_type_select) {
            task_type_select.addEventListener('change', function () {
                const selected = this.options[this.selectedIndex];
                const url = new URL(window.location.href);
                url.searchParams.set('task_type', selected.value);
                url.searchParams.set('rule_index', selected.getAttribute('data-rule-index'));
                window.location.href = url.toString();
            });
        }

        const sort_by_select = document.getElementById('sort_by_select');
        if (sort_by_select) {
            sort_by_select.addEventListener('change', function () {
                const url = new URL(window.location.href);
                url.searchParams.set('sort_by', this.value);
                window.location.href = url.toString();
            });
        }

    });

}

function toggle_slider_control(slider_control){

    console.log(slider_control.value)

    if (slider_control.value == 0) {
        slider_control.classList.remove('yes')
        slider_control.classList.add('no')
        modified_prompt_response = 0
    }else{
        slider_control.classList.remove('no')
        slider_control.classList.add('yes')
        modified_prompt_response = 1
    }
    
    image_box_container = slider_control.closest('.image_box')
    labeler_id = document.querySelector('#labeler_id').value

    data = {asset_id:image_box_container.getAttribute('asset_id'), 
            task_type:image_box_container.getAttribute('task_type'),
            rule_index:image_box_container.getAttribute('rule_index'),
            labeler_source:'view_prediction_labels',
            labeler_id:labeler_id,
            modified_prompt_response:modified_prompt_response
            }
    
    api_collect_modified_prompt(data)
    

}

// --- Similar labeled examples (embedding search) ---
function showSimilarExamples(assetId, taskType, ruleIndex, targetLabel) {
    var modal = document.getElementById('similar_examples_modal');
    var content = document.getElementById('similar_examples_content');
    var title = document.getElementById('similar_examples_title');

    title.textContent = 'Similar images labeled "' + targetLabel + '"';
    content.innerHTML = '<p style="color:#a0b8b8;">Loading...</p>';
    modal.style.display = 'flex';

    var url = window.LABELING_API_BASE_URL + '/get_similar_labeled_examples/?asset_id=' + assetId +
              '&task_type=' + taskType + '&rule_index=' + ruleIndex + '&target_label=' + targetLabel;

    fetch(url)
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.status === 'unavailable') {
                content.innerHTML = '<p style="color:#e0a0a0;">Embedding search unavailable (models not loaded).</p>';
                return;
            }
            if (data.status !== 'ok' || !data.results || data.results.length === 0) {
                content.innerHTML = '<p style="color:#a0b8b8;">No similar examples found.</p>';
                return;
            }
            var html = '<div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:10px;">';
            data.results.forEach(function(item) {
                html += '<div style="text-align:center;">';
                html += '<img src="' + item.image_link + '" style="width:100%; border-radius:6px; border:1px solid #4a5a5a;">';
                html += '<p style="font-size:11px; color:#8a9a9a; margin:4px 0 0;">Score: ' + item.score.toFixed(3) + '</p>';
                html += '</div>';
            });
            html += '</div>';
            content.innerHTML = html;
        })
        .catch(function() {
            content.innerHTML = '<p style="color:#e0a0a0;">Error loading similar examples.</p>';
        });
}

function closeSimilarModal() {
    document.getElementById('similar_examples_modal').style.display = 'none';
}
