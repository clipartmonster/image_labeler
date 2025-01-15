if (window.location.pathname === '/label_images/setup_session/')
document.addEventListener('DOMContentLoaded', function(){

    selected_options = document.getElementById('selected_options')
  
    /////////////////////
    task_type_options = document.querySelectorAll('.task_type')

    task_type_options.forEach(task_type_option => {
        task_type_option.addEventListener('click', ()=> select_task_type_option(task_type_option))

        if (task_type_option.getAttribute('task_type') == selected_options.getAttribute('task_type')){
            task_type_option.classList.add('selected')
        }

    })

    /////////////////////
    rule_options = document.querySelectorAll('.rule_option')
    // rule_options[0].classList.add('selected')

    rule_options.forEach(rule_option => {
        rule_option.addEventListener('click', ()=> select_rule_option(rule_option))

        if (rule_option.getAttribute('rule_index') === selected_options.getAttribute('rule_index')){
            rule_option.classList.add('selected')
        }
        
    })

    /////////////////////
    batch_option_containers = document.querySelectorAll('.batch.indicator.container')

    batch_option_containers.forEach(batch_option_container => {      
        if (batch_option_container.getAttribute('rule_index') != 1){
            batch_option_container.style.display = 'none'
        }    
    })

    batch_options = document.querySelectorAll('.batch.indicator:not(.container')
    // batch_options[0].classList.add('selected')

    batch_options.forEach(batch_option => {
        batch_option.addEventListener('click', ()=> select_batch_option(batch_option))
    })

    /////////////////////
    view_buttons = document.querySelectorAll('.view_button')

    console.log(view_buttons)

    view_buttons.forEach(view_button => {
        view_button.addEventListener('click', ()=> go_to_view_page(view_button))
    })



    labeler_control = document.getElementById('labeler_id')
    labeler_control.addEventListener('click', ()=> toggle_add_a_name_field(labeler_control))

    add_name_field = document.getElementById('add_a_name_field')
    add_name_field.addEventListener('keydown', add_labeler_name)

    labeler_control.value = selected_options.getAttribute('labeler_id')

})

function go_to_view_page(view_button){

    batch_index = view_button
    .closest('.batch.indicator.container')
    .children[0]
    .getAttribute('batch_index')
    
    selected_options = document.querySelectorAll('.selected')
    console.log(selected_options)
    
    selected_options.forEach(selected_option => {

        console.log(selected_option)

        selected_option.classList.forEach(selected_option_class => {

            if (selected_option_class == 'task_type') {
                task_type = selected_option.children[0].textContent
            } else if (selected_option_class == 'rule_option') {
                rule_index = selected_option.getAttribute('rule_index')               
            }
        })


    })

    console.log(task_type, rule_index, batch_index)

     href = window.location.origin  
     + '/label_images/view_batch_labels/?task_type='+task_type
     + '&rule_index=' + rule_index
     + '&batch_index=' + batch_index
    
     window.location.href = href;
    


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


function select_task_type_option(task_type_option) {

    task_type_controls = document.querySelectorAll('.task_type')
    batch_control_containers = document.querySelectorAll('.batch_control.container')

    task_type_controls.forEach(task_type_control => {

        task_type_control.classList.remove('selected')

        if (task_type_control.getAttribute('task_type') == task_type_option.getAttribute('task_type')){
            task_type_control.classList.add('selected')
        }
    })

    batch_control_containers.forEach(batch_container => {

        batch_container.style.display = 'none'

        if (batch_container.getAttribute('task_type') == task_type_option.getAttribute('task_type')){
            batch_container.style.display = 'block'
        }

    })

}

function select_rule_option(rule_option){

    batch_option_containers = document.querySelectorAll('.batch.indicator.container')
    rule_option_controls = document.querySelectorAll('.rule_option')

    rule_option_controls.forEach(rule_control => {
        rule_control.classList.remove('selected')
    })

    rule_option.classList.add('selected')

    batch_option_containers.forEach(batch_container => {

        batch_container.style.display = 'none'

        if (batch_container.getAttribute('rule_index') == rule_option.getAttribute('rule_index')) {
            batch_container.style.display = 'flex';
        }

    })


}




function show_images_wo_labels(){

    selected_options = document.querySelectorAll('.selected')
    console.log(selected_options)
    
    selected_options.forEach(selected_option => {

        console.log(selected_option)

        selected_option.classList.forEach(selected_option_class => {

            if (selected_option_class == 'task_type') {
                task_type = selected_option.children[0].textContent
            } else if (selected_option_class == 'rule_option') {
                rule_index = selected_option.getAttribute('rule_index')               
            } else if (selected_option_class == 'batch') {
                batch_index = selected_option.getAttribute('batch_index')
            }

        })


    })

     href = window.location.origin  
     + '/label_images/mturk_redirect/?task_type='+task_type
     + '&label_source=Internal'  
     + '&labeler_id=' + document.getElementById('labeler_id').value 
     + '&rule_indexes=%5B'+ rule_index +'%5D'
     + '&batch_index='+ batch_index
    
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