
document.addEventListener('DOMContentLoaded', function(){

    // Select all radio buttons within the switch3-container
    const radio_buttons = document.querySelectorAll('.radio_button.view');

    radio_buttons.forEach(radio_button => {

        radio_button.addEventListener('change', function() {

            response = radio_button.value
            assignment_id = radio_button.getAttribute('assignment_id')
            feedback = 'no comment'

            if (response == 'yes'){

                api_collect_validation_response(assignment_id, response, feedback)

            }else{
                
                popup_containers = document.querySelectorAll('.label_option.popup.container')

                popup_containers.forEach(container => {
    
                    if (container.getAttribute('assignment_id') == assignment_id) {                        
                        container.style.display  = 'block'
                    }
                });
            }      
        })            
     })      
})


document.addEventListener('DOMContentLoaded', function(){

    // Select all radio buttons within the switch3-container
    const radio_buttons = document.querySelectorAll('.radio_button.rule_violation');


    radio_buttons.forEach(radio_button =>{

        radio_button.addEventListener('change', function(){

            response = 'no'

            assignment_id = radio_button
            .closest('.label_option.popup.container')
            .getAttribute('assignment_id')

            feedback = radio_button.getAttribute('directive')

            console.log(assignment_id, response, feedback)

            api_collect_validation_response(assignment_id, response, feedback)
        
        })

    })


})

document.addEventListener('DOMContentLoaded', function(){

    // Select all radio buttons within the switch3-container
    const directive_containers = document.querySelectorAll('.label_option.directive.container');

    directive_containers.forEach(directive_container => {
        directive_container.addEventListener('click', function() {

            directive_container
            .querySelector('.label_option.directive.panel')
            .style.display = 'block'

        })
    })
    
})    
