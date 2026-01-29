
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
