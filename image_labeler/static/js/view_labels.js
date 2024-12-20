document.addEventListener('DOMContentLoaded', function(){

        filter_controls = document.querySelectorAll('.option.button.circle.rule_index')

        filter_controls.forEach(filter_control => {

            filter_control.addEventListener('click', 
                ()=> filter_image_boxes(filter_control, '.design.dark.container.asset_view.image_box'))

        })


})

document.addEventListener('DOMContentLoaded', function(){

    size_controls = document.querySelectorAll('.option.button.circle.image_size')

    size_controls.forEach(size_control => {

        size_control.addEventListener('click', 
            ()=> change_image_size(size_control))

    })

})


function change_image_size(element){


    size_controls = document.querySelectorAll('.option.button.circle.image_size')

    size_controls.forEach(size_control => {
        size_control.className = 'option button circle image_size'
    })
 
    element.className = element.className + ' selected'


    images = document.querySelectorAll('.design.view_asset_labels')
    
    images.forEach(image => {

        image.className = 'design view_asset_labels ' + element.getAttribute('size')

    })


}



document.addEventListener('DOMContentLoaded', function(){

    switch_states = document.querySelectorAll('.option.triple_switch_state')

    switch_states.forEach(switch_state => {

        switch_state.addEventListener('click', 
            ()=> switch_filter(switch_state))

    })

})


function switch_filter(element){

    image_boxes = document.querySelectorAll('.design.dark.container.asset_view')
    triple_switches = document.querySelectorAll('.triple_switch.container')

    switch_states = element
    .closest('.triple_switch.container')
    .querySelectorAll('.option.triple_switch_state')

    switch_states.forEach(switch_state => {
        switch_state.classList.remove('selected')
    })

    if (!element.classList.contains('off')) {
        element.classList.add('selected');
    }

    selected_filter_count = document
    .querySelectorAll('.option.triple_switch_state[class*="selected"]')
    .length

    condition_array = create_condition_array(image_boxes.length, triple_switches.length)

    for (let column = 0; column < triple_switches.length; column++) {

        selected_switch_state = triple_switches[column].querySelector('.selected') 
    
        if (selected_switch_state){

            filter_type = triple_switches[column].getAttribute('filter_type')
            filter_value = selected_switch_state.getAttribute('filter_value')
            filter_value = filter_value == 'yes' ? 1:0

             for (let row = 0; row < image_boxes.length; row++) {

                image_box_filter_value = image_boxes[row]
                .querySelector('.labeler_data')
                .getAttribute(filter_type)

                if (filter_value == image_box_filter_value) {
                    condition_array[row][column] = 1
                }

            }

        }     

    }

    condition_vector = 
        condition_array.map(row => row.reduce((sum, value) => sum + value, 0))

    box_image_count = 0

    condition_vector.forEach((value, index) => {

        if (value == selected_filter_count) {
            image_boxes[index].style.display = 'block'
            box_image_count +=1
        } else {
            image_boxes[index].style.display = 'none'
        }

    })   

    document.getElementById('image_count').textContent = box_image_count


}

function create_condition_array(rows,columns ){

    const condition_array = Array.from({ length: rows }, () =>
        Array(columns).fill(0)
    );

    return condition_array
}