
if (window.location.pathname === '/label_images/view_prediction_labels/') {

    document.addEventListener('DOMContentLoaded', function () {

        const urlParams = new URLSearchParams(window.location.search);
        const task_type = urlParams.get('task_type')
        const rule_index = urlParams.get('rule_index')
        const batch_index = urlParams.get('batch_index')
        const label_type_filter = urlParams.get('label_type')

        let slider_controls = document.querySelectorAll('.input_slider.prediction_labels')

        slider_controls.forEach(slider_control => {
            slider_control.addEventListener('input', function () {
                toggle_slider_control(slider_control)
            })
        })

        let label_type_controls = document.querySelectorAll('.control.button.prediction_labels')
       
        label_type_controls.forEach(label_type_control => {

            label_type_control.addEventListener('click', function(){
                toggle_label_type_control(label_type_control)
            })

        })

        let task_type_containers = document.querySelectorAll('.option.container.task_type');

        task_type_containers.forEach(task_type_container => {
            task_type_container.addEventListener('click', function () {
                toggle_task_type_controller(task_type_container);                
            });
        });

        let rule_options = document.querySelectorAll('.rule_option');

        rule_options.forEach(rule_option => {
            
            rule_option.addEventListener('click', function () {
                load_assets(rule_option.getAttribute('rule_index'), null, null);                
            });

            //Remove rule options not in the selected task type container
            if (rule_option.getAttribute('task_type') == task_type) {
                rule_option.style.display = 'grid'

                if (rule_option.getAttribute('rule_index') == rule_index){
                    rule_option.querySelector('.button.circle').classList.add('selected')
                }

            } else {
                rule_option.style.display = 'none'
            }


        })

        let batch_options = document.querySelectorAll('.batch_option')

        batch_options.forEach(batch_option => {

            batch_option.addEventListener('click', function () {
                load_assets(null,null, batch_option.getAttribute('batch_index'));                
            });

            if (batch_option.getAttribute('batch_index') == batch_index){
                batch_option.classList.add('selected')
            } 

        })


        let label_filter_options = document.querySelectorAll('.label_filter_option')

        label_filter_options.forEach(label_filter_option => {

            label_filter_option.addEventListener('click', function () {
                load_assets(null, label_filter_option.getAttribute('label_type_filter', null));                
            });

            if (label_filter_option.getAttribute('label_type_filter') == label_type_filter){
                label_filter_option.classList.add('selected')
            } 

        })


        status_container = document.querySelector('.status.container')
        status_container.style.display = 'none'

    });



}

function toggle_slider_control(slider_control){

    console.log(slider_control.value)

    if (slider_control.value == 0) {
        slider_control.classList.remove('yes')
        slider_control.classList.add('no')
        modified_prompt_response = 'no'
    }else{
        slider_control.classList.remove('no')
        slider_control.classList.add('yes')
        modified_prompt_response = 'yes'
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

function toggle_label_type_control(label_type_control) {

    let label_type_controls = document.querySelectorAll('.control.button.prediction_labels')

    label_type_controls.forEach(label_type_control => {
        label_type_control.querySelector('.control.container.predicted_labels').classList.remove('selected')
    })

    label_type_control.querySelector('.control.container.predicted_labels').classList.add('selected')
    label_type = label_type_control.getAttribute('label_type')

    filter_by_label_type(label_type)

}

function filter_by_label_type(label_type) {

    console.log(label_type)

    image_boxes = document.querySelectorAll('.image_box')

    image_boxes.forEach(image_box => {
        image_box.style.display = 'none'
    })

    if (label_type == 'false positive') {

        image_boxes.forEach(image_box => {

            if (image_box.getAttribute('model_label') == 'yes' && image_box.getAttribute('manual_label') == 'no')

                image_box.style.display = 'grid'

        })

    } else {

        image_boxes.forEach(image_box => {

            if (image_box.getAttribute('model_label') == 'no' && image_box.getAttribute('manual_label') == 'yes')

                image_box.style.display = 'grid'

        })

    }

}


function load_assets(rule_index, label_type_filter, batch_index) {

    console.log(rule_index,label_type_filter, batch_index)

 
    rule_option = document.querySelector('.option.button.circle.rule.index.selected')
    .closest('.rule_option')

    task_type = rule_option.getAttribute('task_type')

    if (batch_index == null){
        batch_option = document.querySelector('.control.container.batch_option.predicted_labels.selected')
        batch_index = batch_option.getAttribute('batch_index')    
    } else {

        batch_options = document.querySelectorAll('.control.container.batch_option.predicted_labels')

        batch_options.forEach(batch_option =>{
            if (batch_option.getAttribute('batch_index') == batch_index) {
                batch_option.classList.add('selected')
            } else {
                batch_option.classList.remove('selected')
            }
        })

    }

    if (rule_index == null){

        rule_index = rule_option.getAttribute('rule_index')

    } else {

        rule_options = document.querySelectorAll('.option.button.circle.rule.index')

        rule_options.forEach(rule_option =>{
            if (rule_option.getAttribute('batch_index') == rule_index) {
                rule_option.classList.add('selected')
            } else {
                rule_option.classList.remove('selected')
            }
        })

    }

    if (label_type_filter == null){

        label_filter_option = document.querySelector('.control.container.label_filter_option.predicted_labels.selected')
        label_type_filter = label_filter_option.getAttribute('label_type_filter')    

    } else {

        label_filter_options = document.querySelectorAll('.control.container.label_filter_option.predicted_labels')

        label_filter_options.forEach(label_filter_option =>{
            if (label_filter_option.getAttribute('label_type_filter') == label_type_filter) {
                label_filter_option.classList.add('selected')
            } else {
                label_filter_option.classList.remove('selected')
            }
        })

    }

    ///////////////////////////////////
    //hide all images
    image_containers = document.querySelectorAll('.image_box')

    image_containers.forEach(image_container => {
        image_container.style.display = 'none'
    })

    ///////////////////////////////////

    status_container = document.querySelector('.status.container')
    status_container.style.display = 'block'

    
    href = window.location.origin  
    + '/label_images/view_prediction_labels/?task_type='+task_type
    + '&rule_index=' + rule_index
    + '&batch_index=' + batch_index
    + '&label_type=' + label_type_filter
   
    window.location.href = href;



}


function toggle_task_type_controller(selected_task_type_container) {

    task_type_containers = document.querySelectorAll('.option.container.task_type')

    task_type_containers.forEach(task_type_container => {

        rule_options = task_type_container.querySelectorAll('.rule_option')

        rule_options.forEach(rule_option => {
            rule_option.style.display = 'none'
        })

    })

    selected_rule_options = selected_task_type_container.querySelectorAll('.rule_option')

    selected_rule_options.forEach(rule_option => {
        rule_option.style.display = 'grid'
    })


}



function collect_label_issue(button){

    image_box_container = button.closest('.image_box')
    console.log(image_box_container)

    button.style.opacity = .25

    data = {asset_id:image_box_container.getAttribute('asset_id'), 
            task_type:image_box_container.getAttribute('task_type'),
            rule_index:image_box_container.getAttribute('rule_index')
            }


    api_collect_label_issue(data)

}

    