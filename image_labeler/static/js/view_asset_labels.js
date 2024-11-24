document.addEventListener('DOMContentLoaded', function(){

    console.log("hello")
    image_boxes = document.querySelectorAll('.listing.light.container.image_box')

    image_boxes.forEach(image_box => {

        data = image_box.querySelector('.labeler_data')

        const validators = 
            image_box.querySelectorAll('.labeler.response.validator');

        if (data.getAttribute('accept_response') == 'yes') {
            validators[0].className = validators[0].className + ' yes'
        }

        if (data.getAttribute('accept_response') == 'no') {
            validators[1].className = validators[1].className + ' no'
        }

    })

    const validators = 
        document.querySelectorAll('.labeler.response.validator');

    validators.forEach(validator => {
        validator.addEventListener('click', ()=> validate_response(validator))
    })

})

document.addEventListener('DOMContentLoaded', function(){

    batch_id_buttons = document.querySelectorAll('.option.button.batch_id')

    batch_id_buttons.forEach(batch_id_button => {
        batch_id_button.addEventListener('click', ()=> filter_by_batch_id(batch_id_button))
    })

})


function filter_by_batch_id(batch_id_button){

    if (['selected'].some(className => batch_id_button.classList.contains(className))) {
        batch_id_button.classList.remove('selected')
    }else{
        batch_id_button.classList.add('selected')
    }

    selected_batch_indexes = 
        batch_id_button.parentElement.querySelectorAll('[class*="selected"]')

    console.log(selected_batch_indexes)

    image_boxes = 
        document.querySelectorAll('.listing.light.container.image_box')

    image_boxes.forEach(image_box => {
        image_box.style.display = 'none'
    })

    selected_batch_indexes.forEach(batch_index => {
        
        button_batch_index = batch_index.getAttribute('batch_id')

        image_boxes.forEach(image_box => {
            
            batch_index = 
                image_box.querySelector('.labeler_data').getAttribute('mturk_batch_id')

            if (batch_index == button_batch_index) {
                image_box.style.display = 'grid'
            }


        })

    })

}




function validate_response(validator){

    validators =  
        validator.parentElement.querySelectorAll('.labeler.response.validator') 

    validators.forEach(validator => {

        validator.classList.remove('no')
        validator.classList.remove('yes')

    })

    if (['top'].some(className => validator.classList.contains(className))) {
        validator.className = 'labeler response validator top yes'
    } else {
        validator.className = 'labeler response validator bot no'
    }

}



