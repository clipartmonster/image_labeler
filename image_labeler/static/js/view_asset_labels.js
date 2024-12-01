document.addEventListener('DOMContentLoaded', function(){

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
        batch_id_button.addEventListener('click', ()=> filter_image_boxes(batch_id_button))
    })

    labeler_source_buttons = document.querySelectorAll('.option.button.labeler_source')

    labeler_source_buttons.forEach(labeler_source_button => {
        labeler_source_button.addEventListener('click', ()=> filter_image_boxes(labeler_source_button))
    })


})

// function filter_by_labeler_source_button(labeler_source_button){

//     console.log('hello')

//     if (['selected'].some(className => labeler_source_button.classList.contains(className))) {
//         labeler_source_button.classList.remove('selected')
//     }else{
//         labeler_source_button.classList.add('selected')
//     }



// }



function filter_image_boxes(element){

    if (['selected'].some(className => element.classList.contains(className))) {
        element.classList.remove('selected')
    }else{
        element.classList.add('selected')
    }

    ////////////////
    //get images boxes to filter

    image_boxes = 
    document.querySelectorAll('.listing.light.container.image_box')

    image_boxes.forEach(image_box => {
        image_box.style.display = 'none'
    })

    //////////////
    //get count of selected buttons
    const selected_buttons = Array.from(document.querySelectorAll('[class]')).filter(el =>
    /^option.button.*selected$/.test(el.className)
    );

    selected_button_count = selected_buttons.length

    console.log(selected_button_count)
    
    function create_condition_vector(selected_buttons){

        const condition_array = Array.from({ length: image_boxes.length }, () =>
            Array(selected_buttons.length).fill(0)
        );

        for (let row = 0; row < image_boxes.length; row++) {
            for (let column = 0; column < selected_buttons.length; column++) {
        
                filter_type = selected_buttons[column].getAttribute('filter_type')
                filter_value = selected_buttons[column].getAttribute('filter_value')

                labeler_data_sets = image_boxes[row].querySelectorAll('.labeler_data')

                labeler_data_sets.forEach(labeler_data => {

                    if (labeler_data.getAttribute(filter_type) == filter_value) {
                       
                        condition_array[row][column] = 1
    
                    }

                })

            }
        }

        condition_vector = condition_array.map(row => row.reduce((sum, value) => sum + value, 0))

        return condition_vector

    }

    function computeRowSums(...vectors) {
        // Check if all vectors have the same length
        const vectorLengths = vectors.map(vector => vector.length);
        const allSameLength = vectorLengths.every(length => length === vectorLengths[0]);
      
        if (!allSameLength) {
          console.error('All vectors must have the same length.');
          return [];
        }
      
        // Initialize an array of zeros for the row sums
        const rowSums = Array(vectorLengths[0]).fill(0);
      
        // Iterate through each vector and sum row-wise
        vectors.forEach(vector => {
          vector.forEach((value, index) => {
            rowSums[index] += value;
          });
        });
      
        return rowSums;
      }

    batch_id_condition_vector = create_condition_vector(document.querySelectorAll('.batch_id.selected'))
    labeler_source_condition_vector = create_condition_vector(document.querySelectorAll('.labeler_source.selected'))


    condition_array =computeRowSums(labeler_source_condition_vector,batch_id_condition_vector)
    
    condition_array.forEach((value, index) => {

        if (value == selected_button_count){
            image_boxes[index].style.display = 'grid'
        }

    })

    // image_boxes = 
    // document.querySelectorAll('.listing.light.container.image_box')

    // image_boxes.forEach(image_box => {
    //     image_box.style.display = 'none'
    // })

    // const condition_array = Array.from({ length: image_boxes.length }, () =>
    //     Array(selected_buttons.length).fill(0)
    // );

    // for (let row = 0; row < image_boxes.length; row++) {
    //     for (let column = 0; column < selected_buttons.length; column++) {
    
    //         filter_type = selected_buttons[column].getAttribute('filter_type')
    //         filter_value = selected_buttons[column].getAttribute('filter_value')

    //         labeler_data = image_boxes[row].querySelectorAll('.labeler_data')

    //         if (labeler_data[0].getAttribute(filter_type) == filter_value) {

    //             console.log('condition met')
    //             condition_array[row][column] = 1

    //         }
                

    //     }
    // }

    // let across_column_sum = condition_array.map(row => row.reduce((sum, value) => sum + value, 0));

    // console.log(selected_buttons)

    // across_column_sum.forEach((sum, index) => {
    //     if (sum == selected_buttons.length) {            
    //         image_boxes[index].style.display = 'grid'            
    //     } else {   
    //         image_boxes[index].style.display = 'none'            
    //     }
    // });



    // image_boxes.forEach(image_box => {

    //     selected_buttons.forEach(selected_button => {

    //         filter_type = selected_button.getAttribute('filter_type')
    //         filter_value = selected_button.getAttribute('filter_value')

    //         // console.log(filter_type)

    //         if (filter_type == 'labeler_source'){


    //             label_boxes = image_box.querySelectorAll('.labeler.container')

    //             label_boxes.forEach(label_box => {

    //                 if (label_box.querySelector('.labeler_data').getAttribute(filter_type) == filter_value){
    //                     console.log('triggred labeler condition')
    //                     image_box.style.display = 'grid'
    //                 }        

    //             })

    //         } else if (filter_type == 'mturk_batch_id') {

    //             if (image_box.querySelector('.labeler_data').getAttribute(filter_type) != filter_value
    //                 && image_box.style.display == 'grid'){
    //                 console.log('triggred mturk batch id condition')
    //                 image_box.style.display = 'none'
    //             }   

    //         } else {

    //             // image_box.style.display = 'none'
            
    //         }
    //     })        

    // })

        // const selected_buttons = Array.from(document.querySelectorAll('[class]')).filter(el =>
    //     /^option.button.*selected$/.test(el.className)
    // );

}


function filter_by_batch_id(batch_id_button){

    if (['selected'].some(className => batch_id_button.classList.contains(className))) {
        batch_id_button.classList.remove('selected')
    }else{
        batch_id_button.classList.add('selected')
    }

    selected_batch_indexes = 
        batch_id_button.parentElement.querySelectorAll('[class*="selected"]')

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



