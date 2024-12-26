

if (window.location.pathname === '/label_images/manage_rules/') {
    document.addEventListener('DOMContentLoaded', function () {

        let rule_containers = document.querySelectorAll('.rule.index');

        rule_containers.forEach(rule_container => {
            rule_container.addEventListener('click', function () {
                toggle_rule_container(rule_container);
            });
        });

        let task_type_controls = document.querySelectorAll('.task_type')
        
         task_type_controls.forEach(task_type_control => {
            task_type_control.addEventListener('click', function () {
                toggle_task_type_controller(task_type_control);
                filter_task_type(task_type_control)
            });

            //set a control to selected when first initializing
            if (task_type_control.getAttribute('task_type') == 'clip_art_type'){
                task_type_control.classList.add('selected')
            }


        });

        let directive_text_field = document.getElementById('directive') 
        directive_text_field.addEventListener('focus', handleDirectiveFocus)

        // directive_valenece_controls = document.querySelectorAll('.circle.directive')
        // directive_valenece_controls.forEach(valence_control => {
        //     valence_control.addEventListener('click', function() {
        //         toggle_valence_control(valence_control)
        //     })
        // })
        

    });

}

// function toggle_valence_control(valence_control) {

//     directive_container = valence_control.closest('.directive.container')

//     valence_controls = directive_container.querySelectorAll('.circle.directive')

//     valence_controls.forEach(valence_control => {
//         valence_control.classList.remove('selected')
//     })

//     valence_control.classList.add('selected')

// }

const handleDirectiveFocus = (event) => add_directive_text_field(event);

function add_directive_text_field(event){

    const directive_text_field = event.target;

    directive_container = directive_text_field.closest('.directive.container')

    copy_directive_container = directive_container.cloneNode(true)
    copy_directive_container.classList.add = 'active'

    copy_directive_container.querySelector('.text.field.add_rule')
    .addEventListener('focus', handleDirectiveFocus)
    
    directive_container
    .parentNode
    .insertBefore(copy_directive_container, directive_container.nextSibling);

    directive_text_field.removeEventListener('focus', handleDirectiveFocus)

}



function filter_task_type(task_type_control){

    task_type = task_type_control.getAttribute('task_type')

    rule_containers = document.querySelectorAll('.rule.container')

    rule_containers.forEach(rule_container => {

        rule_container.style.display = 'none'

        if (rule_container.getAttribute('task_type') == task_type) {
            rule_container.style.display = 'block'
        }

    })

    console.log(task_type)
    


}


function toggle_task_type_controller(task_type_control) {

    document.querySelectorAll('.task_type').forEach(task_type_control => {
        task_type_control.classList.remove('selected')
    })

    task_type_control.classList.add("selected")

}

function toggle_rule_container(rule_container) {

    document.querySelectorAll('.rule.container').forEach(detail_container => {
        detail_container.classList.remove('selected')
    })

    detail_container = rule_container.closest('.rule.container')
    .querySelector('.detail')

    if (detail_container.style.display === 'block') {
        detail_container.style.display = 'none';
        rule_container.classList.remove('selected')
    } else {
        detail_container.style.display = 'block';
        rule_container.classList.add('selected')
    }
}

function add_a_rule(){

    task_type_control = document.querySelector('.task_type.selected')
    
    task_type = task_type_control.getAttribute('task_type')
    title = document.getElementById('title').value
    description = document.getElementById('description').value
    prompt = document.getElementById('prompt').value

    directives = document.querySelectorAll('.text.field.add_rule.directive')
    console.log(directives)

    let data = [];

    directives.forEach(directive => {
        if (directive.value !== '') {
            data.push({
                task_type: task_type,
                title: title,
                description: description,
                prompt: prompt,
                directive: directive.value
            });
        }
    });

    

    console.log(task_type, title, description, prompt)

}