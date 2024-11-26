

function expand_image(event){

    event.stopPropagation();

    x_coord = event.clientX
    y_coord = event.clientY

    expanded_div = event.target.nextElementSibling

    expanded_div.style.display = 'block'
    expanded_div.style.position = 'absolute'
    expanded_div.style.left = 'x_coord'
    expanded_div.style.top = 'y_coord'

    // Toggle the display property of the expanded div
    if (expanded_div && expanded_div.classList.contains('expanded') && expanded_div.classList.contains('example')) {
        // Show the expanded div
        expanded_div.style.display = 'block';

        // Disable other thumbnails while expanded_div is visible
        disableThumbnails();

        // Add a one-time event listener to hide the expanded div on any click
        document.addEventListener('click', function hideOnAnyClick() {
            // Hide the expanded div
            expanded_div.style.display = 'none';

            // Re-enable other thumbnails after expanded_div is hidden
            enableThumbnails();

            // Remove the event listener after the action
            document.removeEventListener('click', hideOnAnyClick);
        });
    }

}

// Function to disable all other thumbnail clicks
function disableThumbnails() {
    var thumbnails = document.querySelectorAll('.label_option.thumbnail');
    thumbnails.forEach(function(thumbnail) {
        thumbnail.style.pointerEvents = 'none'; // Disable clicking on the thumbnail
    });
}

// Function to re-enable thumbnail clicks
function enableThumbnails() {
    var thumbnails = document.querySelectorAll('.label_option.thumbnail');
    thumbnails.forEach(function(thumbnail) {
        thumbnail.style.pointerEvents = 'auto'; // Re-enable clicking on the thumbnail
    });
}


function collect_label(element, response){

    label = response

    collection_data = element
    .closest('.listing.light.container')
    .querySelector('.collection_data')

    data = {task_type:collection_data.getAttribute('task_type'),
            asset_id:collection_data.getAttribute('asset_id'),
            labeler_source:collection_data.getAttribute('labeler_source'),
            labeler_id:collection_data.getAttribute('labeler_id'),
            label_type:collection_data.getAttribute('label_type'),
            label:label
    }

    api_collect_label(data)

}

function collect_prompt(element, reponse){

    collection_data = element
    .closest('.listing.light.container')
    .querySelector('.collection_data')

    data = {task_type:collection_data.getAttribute('task_type'),
            asset_id:collection_data.getAttribute('asset_id'),
            labeler_source:collection_data.getAttribute('labeler_source'),
            labeler_id:collection_data.getAttribute('labeler_id'),
            label_type:collection_data.getAttribute('label_type'),
            rule_index:parseInt(element.getAttribute('rule_index')),
            prompt_response:reponse,
            assignment_id:collection_data.getAttribute('assignment_id'),
            hit_id:collection_data.getAttribute('hit_id'),
            is_test_question:collection_data.getAttribute('is_test_question'),
            mturk_batch_id:collection_data.getAttribute('mturk_batch_id'),
            is_lure_question:collection_data.getAttribute('is_lure_question')
    }

    console.log(data)

    api_collect_prompt(data)

}

function direct_hotkey_action(hotkey) {

        //get list of active elements 

        active_elements = document.querySelectorAll('[class*="active"]')

        priority_element = select_element(Array.from(active_elements))

        response = hotkey === '1' ? 'yes' : 'no'

        if (priority_element.type === 'prompt') {

            collect_prompt(priority_element.element, response)
            update_prompt(hotkey,priority_element.element, response)

        } else if (priority_element.type === 'button_container'){

            update_button(hotkey, priority_element.element)
            collect_label(priority_element.element, response)

        } else {

            collection_data = document
            .getElementsByClassName('collection_data')

            assignment_id = collection_data[0].getAttribute('assignment_id')
            labeler_source = collection_data[0].getAttribute('labeler_source')

            api_update_submission_status(assignment_id)
   
            //advance the page where next page is determined by mturk or not
            const form = document.getElementById('submit_labels')

            if (form.getAttribute('labeler_source') === 'MTurk')
                form.submit()
            else{
                window.location.href = window.location.href;
            }

        }

}

document.addEventListener('keydown', function(event) {
    const hotkey = event.key;  // Get the pressed key (e.g., '1', '2', '3')

    if (hotkey === '1' || hotkey === '2') {

        direct_hotkey_action(hotkey)
       
    }

})

//activeate first listing after content loadsa
// document.addEventListener('DOMContentLoaded', function(){

//     first_listing_container = document.getElementById('listing_container_0')

//     activate_listing_container(first_listing_container)

// })


function select_element(elements) {
    let selectedElement = null;
    let type = null;

    // Prioritize selecting the prompt element, if present
    selectedElement = elements.find(el => el.classList.contains('rule_validator'));
    type = 'prompt'
    
    // If prompt is not found, select label element
    if (!selectedElement) {
        selectedElement = elements.find(el => el.classList.contains('prompt'));
        type = 'prompt_container'
    }

    // If prompt is not found, select label element
    // if (!selectedElement) {
    //     selectedElement = elements.find(el => el.classList.contains('button'));
    //     type = 'button_container'
    // }
    
    // If neither prompt nor label is found, select listing container
    if (!selectedElement) {
        selectedElement = elements.find(el => el.classList.contains('listing'));
        type = 'listing_container'
    }
    
    return {type:type, element:selectedElement};
}


function activate_listing_container(listing_container) {

    listing_container.className = 'listing light container active'

    listing_container.querySelector('.label_option.prompt.container.open')
    .className = 'label_option prompt container active'

    listing_container.querySelectorAll('.label_option.rule_validator')[0]
    .className = 'label_option rule_validator active'

    // scroll to new listing; dont scroll if page has just loaded
    if (document.querySelectorAll('[class*="closed"]').length > 0){
        listing_container.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }


}

function update_prompt(hotkey, element, response) {


    const radioButton = 
        element.querySelector(`input.radio_button[data-hotkey="${hotkey}"]`);
            
    if (radioButton) {
        radioButton.click();  // Select the radio button
    }

    element.className = 'label_option rule_validator closed'

    const open_prompt_count = element
    .closest('.label_option.prompt.container.active')
    .querySelectorAll('[class*="open"], [class*="active"]')
    .length;

    if (open_prompt_count > 0) {    
        element
        .nextElementSibling
        .className = 'label_option rule_validator active'
    } else {
        close_listing_container(element)
    }

    // if (element.getAttribute('correct_response') === null || element.getAttribute('correct_response') === response){
    //     console.log('correct or irrevelant')

    //     element.className = 'label_option rule_validator closed'

    //     const open_prompt_count = element
    //     .closest('.label_option.prompt.container.active')
    //     .querySelectorAll('[class*="open"], [class*="active"]')
    //     .length;
    
    //     if (open_prompt_count > 0) {    
    //         element
    //         .nextElementSibling
    //         .className = 'label_option rule_validator active'
    //     } else {
    //         close_listing_container(element)
    //     }

    // } else {
    //     console.log('incorrect')
    // }



}


function close_listing_container(element){

    prompts = element
    .closest('.listing_info.container')
    .querySelectorAll('.label_option.rule_validator.closed')

    is_test_question = element
    .closest('.listing.light.container.active')
    .getAttribute('test_question')

    feedback_container = element
    .closest('.listing_info.container')
    .getElementsByClassName('label_option response_feedback incorrect')[0]

    prompt_container = element
    .closest('.label_option.prompt.container.active')


    prompt_container.className = 'label_option prompt container closed'
    prompt_container.style.opacity = .35        

    // element
    // .closest('.label_option.prompt.container.active')
    // .style.opacity = .25

    element
    .closest('.listing.light.container.active')
    .className = 'listing light container closed'

    // element
    // .className = 'label_option button container'

    open_listing_containers = document
    .querySelectorAll('.listing.light.container.open, .listing.light.container.test_question')

    if (open_listing_containers.length > 0) {

        open_listing_container = open_listing_containers[0]
        activate_listing_container(open_listing_container)

    } else {

        //wiht no more open listing containers show the sumbit button for leaving page
        document.querySelector('.submit.button.container').style.display = 'grid'
        document.querySelector('.submit.button.container').scrollIntoView({ behavior: 'smooth', block: 'center' });

    }

    
    if (is_test_question == 'yes'){
        result = check_responses(prompts)
    }    


    if (result == 'incorrect') {
        
        feedback_container.style.display = 'grid'

        console.log(element.closest('.listing.light.container.active'))

        element
        .closest('.listing.light.container.closed')
        .querySelector('.label_option.reset.button')
        .click()
    
    } else {

        if (feedback_container != null){
            feedback_container.style.display = 'none'
        }
        
        // element
        // .closest('.label_option.prompt.container.active')
        // .nextElementSibling
        // .className = 'label_option button container active'

        prompt_container = element
        .closest('.label_option.prompt.container.active')


        prompt_container.className = 'label_option prompt container closed'
        prompt_container.style.opacity = .35        

        // element
        // .closest('.label_option.prompt.container.active')
        // .style.opacity = .25

        element
        .closest('.listing.light.container.active')
        .className = 'listing light container closed'

        // element
        // .className = 'label_option button container'

        open_listing_containers = document
        .querySelectorAll('.listing.light.container.open, .listing.light.container.test_question')

        if (open_listing_containers.length > 0) {

            open_listing_container = open_listing_containers[0]
            activate_listing_container(open_listing_container)

        } else {

            //wiht no more open listing containers show the sumbit button for leaving page
            document.querySelector('.submit.button.container').style.display = 'grid'
            document.querySelector('.submit.button.container').scrollIntoView({ behavior: 'smooth', block: 'center' });

        }
    }


}


function reset_responses(event){

    let activeElements = document.querySelectorAll('[class*="active"]');

    activeElements.forEach(element => {
        element.className = element.className.replace(/active/g, 'open');
    });


    listing_container = event.target.closest('.listing.light.container')
    listing_container.scrollIntoView({ behavior: 'smooth', block: 'center' });

    prompt_container = listing_container.querySelector('.label_option.prompt.container')

    prompt_container.className = 'label_option prompt container open'
    prompt_container.style.opacity = 1

    prompts = prompt_container.querySelectorAll('.label_option.rule_validator')

    prompts.forEach(prompt => {

        prompt.className = 'label_option rule_validator open'

        prompt.querySelectorAll('.radio_button').forEach(radio_button =>{

            if (radio_button.getAttribute('data-hotkey')==='3'){
                radio_button.checked = true;
            }

        })

    })


    // button_container = listing_container.querySelector('.label_option.button.container')

    // button_container.className ='label_option button container open'

    // button_container.querySelectorAll('button.label_option.button')
    // .forEach(button =>{button.className = 'button label_option button'})

    activate_listing_container(listing_container)

    document.querySelector('.submit.button.container').style.display = 'none'

    //hit api to remove entries in database
    listing_data = listing_container.querySelector('.collection_data')

    api_remove_prompt_responses(listing_data.getAttribute('asset_id'),
                                listing_data.getAttribute('labeler_id'))


}

//Seetup conditinals to skip question based on response on current question 
//Example if the labler says the iamge is a picture dont't ask any more questions about the image. 
document.addEventListener('DOMContentLoaded', function(){

    // Select all radio buttons within the switch3-container
    // const radio_buttons = document.querySelectorAll('.switch3');

    // radio_buttons.forEach(radio_button => {

    //     rule_index = radio_button
    //     .closest('.label_option.rule_validator')
    //     .getAttribute('rule_index')

    //     if (rule_index === '1') {

    //         radio_button.addEventListener('change', function() {
    //             if (radio_button.querySelector('#switch3-radio1').checked) {
    //                 close_listing_container(radio_button)    
    //              }
    //         });

    //     } else if (rule_index == '2') {

    //         radio_button.addEventListener('change', function() {
    //             if (radio_button.querySelector('#switch3-radio1').checked) {
    //                 close_listing_container(radio_button)
    //             }
    //         });

    //     } else if (rule_index === '3') {

    //         radio_button.addEventListener('change', function() {
    //             if (radio_button.querySelector('#switch3-radio1').checked) {
    //                 close_listing_container(radio_button)
    //             }
    //         });
            
    //     } else if (rule_index === '4') {

    //         radio_button.addEventListener('change', function() {
    //             if (radio_button.querySelector('#switch3-radio3').checked) {
    //                 close_listing_container(radio_button)
    //             }
    //         });
            
    //     }

    // })

})

//hide listings --> user will hit a ready button to show them
document.addEventListener('DOMContentLoaded', function(){
    
    const listing_containers = 
         document.querySelectorAll(
            '.listing.light.container.open, \
             .listing.light.container.active, \
             .listing.light.container.test_question');

    activate_listing_container(listing_containers[0])


    listing_containers.forEach((listing_container, index) =>{

            listing_container.id = 'listing_container_' + index
            listing_container.style.display = 'none'

    })

})

//function to show the listings when a user hits the ready button
function show_listings(){
    const listing_containers = 
         document.querySelectorAll('.listing.light.container.open, \
                                    .listing.light.container.active, \
                                    .listing.light.container.test_question');

    listing_containers.forEach(listing_container =>{
        listing_container.style.display = 'grid'        
    })

    first_listing_container = document.querySelector('.listing.light.container.active')
    first_listing_container.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

//Utiltiy Functions
function sum_array(array){
    sum = 0
    for (let i = 0; i < array.length; i++ ) {
        sum += array[i];
    }
    return sum
}

function check_responses(prompts) {

    correct_responses = []

    prompts.forEach(prompt => {

        responses = prompt.querySelectorAll('.radio_button')
        responses.forEach(response => {
            if (response.checked) {
                user_response = response.getAttribute('prompt_response')
                
            } 
        })

        if (user_response == prompt.getAttribute('correct_response')) {
            correct_responses.push(1)
        } else {
            correct_responses.push(0)
        }

    })

    if (sum_array(correct_responses) == prompts.length) {
        result = 'correct'
    } else {
        result = 'incorrect'
    }

    return result
}