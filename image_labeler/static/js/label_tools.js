

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
            prompt_response:reponse
    }

    api_collect_prompt(data)

}

function direct_hotkey_action(hotkey) {

        //get list of active elements 

        active_elements = document.querySelectorAll('[class*="active"]')

        priority_element = select_element(Array.from(active_elements))

        console.log(priority_element)

        response = hotkey === '1' ? 'yes' : 'no'

        if (priority_element.type === 'prompt') {

            update_prompt(hotkey,priority_element.element)
            collect_prompt(priority_element.element, response)

        } else if (priority_element.type === 'button_container'){

            update_button(hotkey, priority_element.element)
            collect_label(priority_element.element, response)

        } else {

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
document.addEventListener('DOMContentLoaded', function(){

    first_listing_container = document.getElementById('listing_container_0')

    activate_listing_container(first_listing_container)

})


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
    if (!selectedElement) {
        selectedElement = elements.find(el => el.classList.contains('button'));
        type = 'button_container'
    }
    
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

    listing_container.scrollIntoView({ behavior: 'smooth', block: 'center' });

}

function update_prompt(hotkey, element) {

    const radioButton = element.querySelector(`input.radio_button[data-hotkey="${hotkey}"]`);
            
    if (radioButton) {
        radioButton.click();  // Select the radio button
    }

    element.className = 'label_option rule_validator closed'

    open_prompt_count = element
    .closest('.label_option.prompt.container.active')
    .querySelectorAll('[class*="open"]')
    .length

    if (open_prompt_count > 0) {
    
        element
        .nextElementSibling
        .className = 'label_option rule_validator active'

    } else {

        element
        .closest('.label_option.prompt.container.active')
        .nextElementSibling
        .className = 'label_option button container active'

        element
        .closest('.label_option.prompt.container.active')
        .className = 'label_option prompt container closed'

    }

}

function update_button(hotkey, element){ 

    if (hotkey === '1') {
        const yesButton = element.querySelector('button[onclick*="yes"]');
        // collect_label({ target: yesButton }, "yes");
        yesButton.className = 'button label_option button yes'

    } else if (hotkey === '2') {
        const noButton = element.querySelector('button[onclick*="no"]');
        // collect_label({ target: noButton }, "no");
        noButton.className = 'button label_option button no'
    }


    element
    .closest('.listing.light.container.active')
    .className = 'listing light container closed'

    element
    .className = 'label_option button container'

    open_listing_containers = document
    .querySelectorAll('.listing.light.container.open')

    console.log(open_listing_containers.length)

    if (open_listing_containers.length > 0) {

        open_listing_container = open_listing_containers[0]
        activate_listing_container(open_listing_container)

    } else {

        //wiht no more open listing containers show the sumbit button for leaving page
        document.querySelector('.submit.button.container').style.display = 'grid'
        document.querySelector('.submit.button.container').scrollIntoView({ behavior: 'smooth', block: 'center' });

    }

}

function reset_responses(event){

    let activeElements = document.querySelectorAll('[class*="active"]');

    activeElements.forEach(element => {
        element.className = element.className.replace(/active/g, 'open');
    });


    listing_container = event.target.closest('.listing.light.container')

    prompt_container = listing_container.querySelector('.label_option.prompt.container')

    prompt_container.className = 'label_option prompt container open'

    prompts = prompt_container.querySelectorAll('.label_option.rule_validator')

    prompts.forEach(prompt => {

        prompt.className = 'label_option rule_validator open'

        prompt.querySelectorAll('.radio_button').forEach(radio_button =>{

            if (radio_button.getAttribute('data-hotkey')==='3'){
                radio_button.checked = true;
            }

        })

    })


    button_container = listing_container.querySelector('.label_option.button.container')

    button_container.className ='label_option button container open'

    button_container.querySelectorAll('button.label_option.button')
    .forEach(button =>{button.className = 'button label_option button'})

    activate_listing_container(listing_container)

    document.querySelector('.submit.button.container').style.display = 'none'

}


// document.addEventListener('DOMContentLoaded', function(){

//     // Select all radio buttons within the switch3-container
//     const radioButtons = document.querySelectorAll('.switch3-container .radio_button');

//     // Add an event listener to each radio button
//     radioButtons.forEach((radio) => {

//         radio.addEventListener('change', (event) => {
//             const selectedRadio = event.target;
           
//             response = selectedRadio.getAttribute('prompt_response') === 'yes' ? '1' : '2'

//             direct_hotkey_action(response)

//         });
//     });

// })