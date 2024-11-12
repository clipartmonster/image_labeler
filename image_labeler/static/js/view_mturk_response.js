
document.addEventListener('DOMContentLoaded', function(){

    // Select all radio buttons within the switch3-container
    const radio_buttons = document.querySelectorAll('.radio_button.view');

    radio_buttons.forEach(radio_button => {

        radio_button.addEventListener('change', function() {
            console.log(radio_button.value)
            console.log(radio_button.getAttribute('assignment_id'))

            response = radio_button.value
            assignment_id = radio_button.getAttribute('assignment_id')
            feedback = 'no comment'
            
            api_collect_validation_response(assignment_id, response, feedback)

        })
            
     })
      
})


