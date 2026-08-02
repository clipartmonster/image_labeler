

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

    if (!window._trainingAnswers) {
        api_collect_label(data)
    }

}

function collect_prompt(element, reponse){

    console.log(element)
    console.log('executing collect prompt function')
    
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

     if (!window._trainingAnswers) {
         api_collect_prompt(data)
     }

}

function collect_mismatch_prompt(element, reponse){
    
    collection_data = element
    .closest('.listing.light.container')
    .querySelector('.collection_data')

    data = {task_type:collection_data.getAttribute('task_type'),
            rule_index:parseInt(element.getAttribute('rule_index')),
            asset_id:parseInt(collection_data.getAttribute('asset_id'))
    }

    if (!window._trainingAnswers) {
        api_collect_mismatch_prompt(data)
    }

    data = {task_type:collection_data.getAttribute('task_type'),
            rule_index:parseInt(element.getAttribute('rule_index')),
            asset_id:parseInt(collection_data.getAttribute('asset_id')),
            labeler_source:collection_data.getAttribute('labeler_source'),
            labeler_id:collection_data.getAttribute('labeler_id'),
            modified_prompt_response:reponse
        }

    if (!window._trainingAnswers) {
        api_collect_modified_prompt(data)
    }

}


function direct_hotkey_action(hotkey) {

        //get list of active elements 

        active_elements = document.querySelectorAll('[class*="active"]')

        priority_element = select_element(Array.from(active_elements))

        if (priority_element.type === 'prompt') {

            // Resolve the response from the radio bound to this hotkey. This
            // supports both the binary yes/no control (hotkeys 1/2) and the
            // ordinal 0-3 control for color_fill_type rule 5 (hotkeys 1-4).
            var radio = priority_element.element.querySelector('input.radio_button[data-hotkey="' + hotkey + '"]')
            var response = radio ? radio.getAttribute('prompt_response') : null
            if (!response || response === 'none') return  // key not valid for this control

            if (priority_element.element.getAttribute('prompt_type') == 'mismatch') {
                collect_mismatch_prompt(priority_element.element, response)
                update_prompt(hotkey,priority_element.element, response)
            }else{
                collect_prompt(priority_element.element, response)
                update_prompt(hotkey,priority_element.element, response)
            }

        } else if (priority_element.type === 'button_container'){

            if (hotkey !== '1' && hotkey !== '2') return
            var response = hotkey === '1' ? 'yes' : 'no'
            update_button(hotkey, priority_element.element)
            collect_label(priority_element.element, response)

        } else {

            if (hotkey !== '1' && hotkey !== '2') return

            collection_data = document
            .getElementsByClassName('collection_data')

            assignment_id = collection_data[0].getAttribute('assignment_id')
            labeler_source = collection_data[0].getAttribute('labeler_source')

            if (window._trainingAnswers && window._trainingMeta) {
                var stats = window._trainingStats || { correct: 0, total: 0, startTime: Date.now() };
                var elapsed = Math.round((Date.now() - stats.startTime) / 1000);
                var fd = new FormData();
                fd.append('task_type', window._trainingMeta.taskType);
                fd.append('rule_index', window._trainingMeta.ruleIndex);
                fd.append('correct', stats.correct);
                fd.append('total', stats.total);
                fd.append('time_seconds', elapsed);
                fd.append('answers', JSON.stringify(stats.answers || []));
                fetch('/label_images/complete_training/', { method: 'POST', body: fd })
                    .finally(function() {
                        window.location.href = '/label_images/setup_session/';
                    });
                return;
            }

            api_update_submission_status(assignment_id)
   
            //advance the page where next page is determined by mturk or not
            const form = document.getElementById('submit_labels')

            if (form.getAttribute('labeler_source') === 'MTurk')
                form.submit()
            else{
                console.log('here')

                const form = document.getElementById('submit_labels');
                const baseUrl = `${window.location.protocol}//${window.location.host}`;
              
                form.action = `${baseUrl}/label_images/setup_session`;
                form.submit()

            }

        }

}

document.addEventListener('keydown', function(event) {
    const hotkey = event.key;
    if (document.querySelector('.training-paused')) return;
    // Don't hijack keystrokes while typing in a text field.
    var ae = document.activeElement;
    if (ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA')) return;
    // When the color_fill_type rule 5 depth control is active, 0-9 enter the layer
    // count (0 = Flat, 9 = "9+"), F = Flat, G = Gradient. Checked first so digits
    // route to the depth control rather than the binary yes/no handler.
    if (depth_hotkey(hotkey)) return;
    // 1-2 drive the binary yes/no control.
    if (hotkey === '1' || hotkey === '2' || hotkey === '3' || hotkey === '4') {
        direct_hotkey_action(hotkey)
    }
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

    // === OPTIMIZATION: Lazy Load Images ===
    // 1. Load image for current container
    let img = listing_container.querySelector('img.design');
    if (img && img.dataset.src) {
        img.src = img.dataset.src;
        img.removeAttribute('data-src');
    }
    if (img) {
        img.onerror = function() {
            var cd = listing_container.querySelector('.collection_data');
            var rv = listing_container.querySelector('.label_option.rule_validator');
            if (cd && rv) {
                var flagData = {
                    asset_id: cd.getAttribute('asset_id'),
                    task_type: cd.getAttribute('task_type'),
                    rule_index: rv.getAttribute('rule_index'),
                    labeler_id: cd.getAttribute('labeler_id') || new URLSearchParams(window.location.search).get('labeler_id') || ''
                };
                if (!window._trainingAnswers) {
                    api_collect_label_issue(flagData);
                }
            }
            var keyEvt = new KeyboardEvent('keydown', { key: '2', code: 'Digit2', keyCode: 50, bubbles: true, cancelable: true });
            document.dispatchEvent(keyEvt);
        };
    }

    // 2. Preload image for the NEXT container (to reduce waiting time)
    // Find the next sibling that is a listing container
    let nextContainer = listing_container.nextElementSibling;
    while (nextContainer && !nextContainer.classList.contains('listing')) {
        nextContainer = nextContainer.nextElementSibling;
    }
    
    if (nextContainer) {
        let nextImg = nextContainer.querySelector('img.design');
        if (nextImg && nextImg.dataset.src) {
            nextImg.src = nextImg.dataset.src;
            nextImg.removeAttribute('data-src');
        }
    }
    // === END OPTIMIZATION ===

    if (window.matchMedia('(max-width: 768px)').matches) {
        mobile_keyboard = document.querySelector('#mobile_keyboard')
        mobile_keyboard.style.display = 'flex'

        prompt_container = listing_container.querySelector('.label_option.prompt.container')
        prompt_container.append(mobile_keyboard)    
    }

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

}


// Close the given rule_validator and advance, mirroring update_prompt's tail.
// Used by the color_fill_type rule 5 depth control, which submits a free-form
// value (Flat=0, Gradient, or a typed layer count) instead of clicking a radio.
function advance_after_prompt(element) {
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
}

// Record a depth response ("0" for Flat, "gradient" for Gradient) then advance.
function submit_depth(el, value) {
    var rv = el.closest('.label_option.rule_validator')
    if (!rv) return
    if (rv.getAttribute('prompt_type') == 'mismatch') {
        collect_mismatch_prompt(rv, value)
    } else {
        collect_prompt(rv, value)
    }
    advance_after_prompt(rv)
}

// Skip the current asset (color_fill_type rule 5) without recording an answer,
// mirroring the line-width Skip: just advance to the next asset.
function skip_depth(el) {
    var rv = el.closest('.label_option.rule_validator')
    if (!rv) return
    advance_after_prompt(rv)
}

// Keyboard shortcuts for the depth control (color_fill_type rule 5): digits 0-5
// enter the layer count directly (0 = Flat, 5 = "5+"), F = Flat, G = Gradient,
// S = Skip. Only acts when a depth rule_validator is active. Returns true if it
// handled the key so the caller can skip the binary yes/no handler.
function depth_hotkey(key) {
    var rv = document.querySelector('.label_option.rule_validator.active')
    if (!rv || !rv.querySelector('.depth-controls')) return false
    if (key >= '0' && key <= '5') { submit_depth(rv, key); return true }
    if (key === 'f' || key === 'F') { submit_depth(rv, '0'); return true }
    if (key === 'g' || key === 'G') { submit_depth(rv, 'gradient'); return true }
    if (key === 's' || key === 'S') { skip_depth(rv); return true }
    return false
}


function _advanceAfterClose() {
    var open_listing_containers = document
        .querySelectorAll('.listing.light.container.open, .listing.light.container.test_question');

    if (open_listing_containers.length > 0) {
        activate_listing_container(open_listing_containers[0]);
    } else {
        document.querySelector('.submit.button.container').style.display = 'grid';
        document.querySelector('.submit.button.container').scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function close_listing_container(element){

    teardownMeasureOverlay();

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

    var listingContainer = element.closest('.listing.light.container.active');

    prompt_container.className = 'label_option prompt container closed'
    prompt_container.style.opacity = .35        

    // Training feedback: show correct answer before advancing
    if (window._trainingAnswers && listingContainer) {
        var assetId = listingContainer.querySelector('.collection_data').getAttribute('asset_id');
        var correctLabel = window._trainingAnswers[assetId];
        if (correctLabel !== undefined) {
            var userResponses = prompt_container.querySelectorAll('.label_option.rule_validator.closed');
            var userAnswer = null;
            if (userResponses.length > 0) {
                var checked = userResponses[0].querySelector('input.radio_button:checked');
                if (checked) userAnswer = checked.getAttribute('prompt_response');
            }
            var correctText = correctLabel === 1 ? 'YES' : 'NO';
            var isCorrect = (correctLabel === 1 && userAnswer === 'yes') || (correctLabel === 0 && userAnswer === 'no');

            if (window._trainingStats) {
                window._trainingStats.total++;
                if (isCorrect) window._trainingStats.correct++;
                window._trainingStats.answers.push({
                    asset_id: assetId,
                    answer: userAnswer || 'none',
                    is_correct: isCorrect
                });
            }

            var fb = document.createElement('div');
            fb.className = 'training-feedback-overlay';
            fb.style.cssText = 'position:absolute; inset:0; z-index:50; display:flex; flex-direction:column; align-items:center; justify-content:center; background:rgba(0,0,0,0.75); border-radius:8px;';
            fb.innerHTML = '<div style="text-align:center; padding:24px;">'
                + '<p style="font-size:22px; font-weight:700; margin:0 0 8px; color:' + (isCorrect ? '#a0e0a0' : '#e06060') + ';">'
                + (isCorrect ? 'Correct!' : 'Incorrect') + '</p>'
                + '<p style="font-size:16px; color:#d2e2e2; margin:0 0 16px;">The correct answer is <strong>' + correctText + '</strong></p>'
                + '<p style="font-size:13px; color:#a0b8b8; margin:0;">Press any key to continue</p>'
                + '</div>';

            listingContainer.style.position = 'relative';
            listingContainer.appendChild(fb);
            listingContainer.className = 'listing light container training-paused';
            listingContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });

            function onTrainingContinue(e) {
                document.removeEventListener('keydown', onTrainingContinue);
                fb.remove();
                listingContainer.className = 'listing light container closed';
                _advanceAfterClose();
            }
            document.addEventListener('keydown', onTrainingContinue);
            return;
        }
    }

    listingContainer.className = 'listing light container closed';
    _advanceAfterClose();

    
    // if (is_test_question == 'yes'){
    //     result = check_responses(prompts)
    // } 

    // if (result == 'incorrect') {
        
    //     console.log('here')

    //     feedback_container.style.display = 'grid'

    //     console.log(element.closest('.listing.light.container.active'))

    //     element
    //     .closest('.listing.light.container.closed')
    //     .querySelector('.label_option.reset.button')
    //     .click()
    
    // } else {

    //     if (feedback_container != null){
    //         feedback_container.style.display = 'none'
    //     }
        
    //     // element
    //     // .closest('.label_option.prompt.container.active')
    //     // .nextElementSibling
    //     // .className = 'label_option button container active'

    //     prompt_container = element
    //     .closest('.label_option.prompt.container.active')


    //     prompt_container.className = 'label_option prompt container closed'
    //     prompt_container.style.opacity = .35        

    //     // element
    //     // .closest('.label_option.prompt.container.active')
    //     // .style.opacity = .25

    //     element
    //     .closest('.listing.light.container.active')
    //     .className = 'listing light container closed'

    //     // element
    //     // .className = 'label_option button container'

    //     open_listing_containers = document
    //     .querySelectorAll('.listing.light.container.open, .listing.light.container.test_question')

    //     if (open_listing_containers.length > 0) {

    //         open_listing_container = open_listing_containers[0]
    //         activate_listing_container(open_listing_container)

    //     } else {

    //         //wiht no more open listing containers show the sumbit button for leaving page
    //         document.querySelector('.submit.button.container').style.display = 'grid'
    //         document.querySelector('.submit.button.container').scrollIntoView({ behavior: 'smooth', block: 'center' });

    //     }
    // }


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

    //get active prompt to get the rule index attribute 
    active_prompt = prompt_container.querySelector('.label_option.rule_validator')
    
  
    prompts = prompt_container.querySelectorAll('.label_option.rule_validator')

    prompts.forEach(prompt => {

        prompt.className = 'label_option rule_validator open'

        prompt.querySelectorAll('.radio_button').forEach(radio_button =>{

            if (radio_button.getAttribute('data-hotkey')==='3'){
                radio_button.checked = true;
            }

        })

    })

    activate_listing_container(listing_container)

    //hit api to remove entries in database
    listing_data = listing_container.querySelector('.collection_data')

    if (active_prompt.getAttribute('prompt_type') == 'mismatch') {

        console.log("reset mismatch")
        
        data = {asset_id:listing_data.getAttribute('asset_id'), 
                task_type:listing_data.getAttribute('task_type'),
                rule_index:active_prompt.getAttribute('rule_index')
        }

        api_remove_modified_prompt(data)
        api_reset_mismatch_prompt(data)


    }else{

        console.log("just remove prompt")

        if (!window._trainingAnswers) {
            api_remove_prompt_responses(listing_data.getAttribute('asset_id'),
                                        listing_data.getAttribute('labeler_id'),
                                        listing_data.getAttribute('labeler_source'),
                                        listing_data.getAttribute('task_type'),
                                        active_prompt.getAttribute('rule_index'))
        }

    }

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

    if (listing_containers.length === 0) return;

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

    if (listing_containers.length === 0) return;

    listing_containers.forEach(function(listing_container) {
        listing_container.style.display = 'grid';
        var img = listing_container.querySelector('img.design');
        if (img && img.dataset.src) {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        }
    });

    first_listing_container = document.querySelector('.listing.light.container.active')
    if (first_listing_container) {
        first_listing_container.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
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


function flag_asset_issue(event){

    button = event.target

    collection_data = button
    .closest('.listing.light.container')
    .querySelector('.collection_data')

    rule_validator = button
    .closest('.listing.light.container')
    .querySelector('.label_option.rule_validator')

    console.log(collection_data)
    console.log(rule_validator)

    button.style.opacity = .25

    data = {asset_id:collection_data.getAttribute('asset_id'), 
            task_type:collection_data.getAttribute('task_type'),
            rule_index:rule_validator.getAttribute('rule_index'),
            labeler_id:collection_data.getAttribute('labeler_id') || new URLSearchParams(window.location.search).get('labeler_id') || ''
            }


    if (!window._trainingAnswers) {
        api_collect_label_issue(data)
    }

    // The graded depth control (color_fill_type rule 5) has no yes/no radio, so
    // the synthetic "2" keypress used to record + advance for binary rules does
    // nothing there. Record a "flag" entry directly and advance instead.
    var depthControls = button
        .closest('.listing.light.container')
        .querySelector('.label_option.rule_validator .depth-controls')

    if (depthControls) {
        var rv = depthControls.closest('.label_option.rule_validator')
        collect_prompt(rv, 'flag')
        advance_after_prompt(rv)
        return
    }

    const key_event = new KeyboardEvent('keydown', {
        key: '2',        // Key value
        code: 'Digit2',  // Physical key on the keyboard
        keyCode: 50,     // Deprecated but still used in some environments
        charCode: 50,    // Deprecated but occasionally useful
        which: 50,       // Deprecated but some older systems use it
        bubbles: true,   // Ensures the event bubbles up
        cancelable: true // Allows the event to be canceled
    });

    document.dispatchEvent(key_event);


}

document.addEventListener('DOMContentLoaded', function(){
   
    mobile_buttons = document.querySelectorAll('div.button.mobile_keyboard')

    mobile_buttons.forEach(button => {
        button.addEventListener('click', function(){

            console.log('hello')

            const keyStroke = button.getAttribute('key_stroke');

            const key_event = new KeyboardEvent('keydown', {
                key: keyStroke,  // Use the retrieved key stroke
                bubbles: true,   // Ensures the event bubbles up
                cancelable: true // Allows the event to be canceled
            });
        
            document.dispatchEvent(key_event); 

        } )
    })

    // --- Session timing for rate tracking ---
    if (!sessionStorage.getItem('labeling_session_start')) {
        sessionStorage.setItem('labeling_session_start', new Date().toISOString());
        sessionStorage.setItem('labeling_session_count', '0');
        sessionStorage.setItem('labeling_session_stamps', JSON.stringify([Date.now()]));
    }
})


// Increment label count and record timestamp on each prompt submission
var _originalCollectPrompt = typeof api_collect_prompt === 'function' ? api_collect_prompt : null;
function _incrementSessionCount() {
    var count = parseInt(sessionStorage.getItem('labeling_session_count') || '0');
    sessionStorage.setItem('labeling_session_count', String(count + 1));
    var stamps = JSON.parse(sessionStorage.getItem('labeling_session_stamps') || '[]');
    stamps.push(Date.now());
    sessionStorage.setItem('labeling_session_stamps', JSON.stringify(stamps));
}

// Hook into collect_prompt to track label submissions
var _origCollectPromptFn = window.collect_prompt;
if (_origCollectPromptFn) {
    window.collect_prompt = function(element, response) {
        _incrementSessionCount();
        return _origCollectPromptFn(element, response);
    };
}

// ---------------------------------------------------------------------------
// Line-width auto-measure overlay
// Click ON a line to auto-detect its width. Right-click to undo.
// Loads image through a same-origin proxy to guarantee pixel access.
// ---------------------------------------------------------------------------
var _measureState = null;

function initMeasureOverlay(imgEl, options) {
    if (_measureState) teardownMeasureOverlay();

    options = options || {};
    var showAddButton = options.showAddButton !== false;
    var gridSections = options.gridSections || 0;
    var samplesPerSection = options.samplesPerSection || 0;
    var externalStatsTarget = options.statsTarget || null;
    var measureTableTarget = options.measureTableTarget || null;
    var measureHistogramTarget = options.measureHistogramTarget || null;
    var measureStatsTarget = options.measureStatsTarget || null;
    var loupeCanvasEl = options.loupeCanvas || null;
    var toolsContainer = options.toolsContainer || null;
    var thresholdContainer = options.thresholdContainer || null;
    var onToolChange = options.onToolChange || null;
    var inlineLoupe = !!options.inlineLoupe;
    var useFixedLoupe = !!(loupeCanvasEl && externalStatsTarget);
    var activeTool = options.defaultTool || 'fit';
    var circleRadius = 12;
    var fitCircleRadius = 18;
    var FIT_CIRCLE_MIN = 8;
    var FIT_CIRCLE_MAX = 140;
    var FIT_CIRCLE_LOUPE_PAD = 3;
    var lastMouse = null;
    var measureIdCounter = 0;
    var hoveredMeasureId = null;
    var latestMeasureId = null;
    var thresholdMode = 'auto';
    var thresholdManual = 128;
    var previewMeasurement = null;
    var lastAutoThreshold = null;

    var container = imgEl.parentElement;
    container.style.position = 'relative';

    var INLINE_LOUPE_MARGIN = 84;
    var imageMargin = inlineLoupe ? INLINE_LOUPE_MARGIN : 0;
    if (imageMargin) {
        container.classList.add('mlw-img-wrap--loupe');
        container.style.padding = imageMargin + 'px';
    }
    imgEl.style.position = 'relative';
    imgEl.style.zIndex = '1';

    var w = imgEl.offsetWidth;
    var h = imgEl.offsetHeight;
    var imgOx = imgEl.offsetLeft;
    var imgOy = imgEl.offsetTop;
    var canvasW = imageMargin ? container.clientWidth : w;
    var canvasH = imageMargin ? container.clientHeight : h;
    var natW = imgEl.naturalWidth || w;
    var natH = imgEl.naturalHeight || h;
    var scaleX = natW / w;
    var scaleY = natH / h;

    var canvas = document.createElement('canvas');
    canvas.width = canvasW;
    canvas.height = canvasH;
    if (imageMargin) {
        canvas.style.cssText = 'position:absolute; top:0; left:0; width:' + canvasW + 'px; height:' + canvasH
            + 'px; z-index:20; cursor:crosshair;';
    } else {
        canvas.style.cssText = 'position:absolute; top:' + imgOy + 'px; left:' + imgOx + 'px; width:' + w
            + 'px; height:' + h + 'px; z-index:10; cursor:crosshair;';
    }

    container.appendChild(canvas);
    var ctx = canvas.getContext('2d');

    var srcCanvas = document.createElement('canvas');
    srcCanvas.width = natW;
    srcCanvas.height = natH;
    var srcCtx = srcCanvas.getContext('2d');
    var srcReady = false;
    var imgData = null;
    var hasTransparency = false;

    var loadingBanner = document.createElement('div');
    loadingBanner.style.cssText = 'position:absolute; top:' + imgOy + 'px; left:' + imgOx + 'px; '
        + 'width:' + w + 'px; text-align:center; padding:8px 0; z-index:15; '
        + 'background:rgba(0,0,0,0.7); color:#fff; font:600 13px sans-serif; '
        + 'border-radius:0 0 6px 6px; pointer-events:none;';
    loadingBanner.textContent = 'Loading pixel data…';
    container.appendChild(loadingBanner);

    function invokeRedraw(p) {
        if (!p) {
            redraw();
            return;
        }
        var ix = p.onImage !== false ? p.x : undefined;
        var iy = p.onImage !== false ? p.y : undefined;
        var cx = p.cx !== undefined ? p.cx : (p.x + imgOx);
        var cy = p.cy !== undefined ? p.cy : (p.y + imgOy);
        redraw(ix, iy, cx, cy);
    }

    function onPixelDataReady() {
        if (loadingBanner.parentNode) loadingBanner.remove();
        if (lastMouse) invokeRedraw(lastMouse);
        else redraw();
    }
    function onPixelDataFailed() {
        loadingBanner.textContent = 'Pixel data unavailable – clicks may not register';
        loadingBanner.style.background = 'rgba(176,48,48,0.85)';
    }

    var proxyUrl = '/label_images/image_proxy/?url=' + encodeURIComponent(imgEl.src);
    var img2 = new Image();
    img2.onload = function() {
        srcCtx.drawImage(img2, 0, 0, natW, natH);
        try {
            imgData = srcCtx.getImageData(0, 0, natW, natH);
            srcReady = true;
            var d = imgData.data;
            for (var i = 3; i < d.length; i += 16) {
                if (d[i] < 250) { hasTransparency = true; break; }
            }
            onPixelDataReady();
        } catch(e) {
            console.warn('Measure overlay: cannot read pixel data', e);
            onPixelDataFailed();
        }
    };
    img2.onerror = function() {
        console.warn('Measure overlay: proxy image load failed, trying direct');
        var img3 = new Image();
        img3.crossOrigin = 'anonymous';
        img3.onload = function() {
            srcCtx.drawImage(img3, 0, 0, natW, natH);
            try {
                imgData = srcCtx.getImageData(0, 0, natW, natH);
                srcReady = true;
                var d = imgData.data;
                for (var i = 3; i < d.length; i += 16) {
                    if (d[i] < 250) { hasTransparency = true; break; }
                }
                onPixelDataReady();
            } catch(e2) {
                console.warn('Measure overlay: direct load also failed', e2);
                onPixelDataFailed();
            }
        };
        img3.onerror = function() {
            console.warn('Measure overlay: direct load also failed');
            onPixelDataFailed();
        };
        img3.src = imgEl.src;
    };
    img2.src = proxyUrl;

    var GROUP_COLORS = ['#ff3366', '#33aaff', '#44cc66', '#ff9933', '#cc66ff', '#ffcc00'];
    var measureGroups = [[]];
    var currentGroup = 0;
    // Sections marked by the labeler as "no lines here" — counted as satisfied
    // for save validation. Keyed by "row,col".
    var ignoredSections = {};

    function toggleSectionIgnored(r, c) {
        var k = r + ',' + c;
        if (ignoredSections[k]) delete ignoredSections[k];
        else ignoredSections[k] = true;
        updateStatsBar();
        redraw();
    }

    // Stats bar: either the caller's element, or a floating overlay on the image.
    var statsBar;
    if (externalStatsTarget) {
        statsBar = externalStatsTarget;
        statsBar.innerHTML = '';
    } else {
        statsBar = document.createElement('div');
        statsBar.style.cssText = 'position:absolute; top:' + imgOy + 'px; left:' + imgOx + 'px; '
            + 'z-index:12; display:flex; align-items:center; gap:6px; padding:4px 8px; '
            + 'background:rgba(0,0,0,0.82); border-radius:0 0 6px 0; font:bold 11px sans-serif; color:#fff; '
            + 'pointer-events:auto; user-select:none; flex-wrap:wrap; max-width:' + w + 'px;';
        statsBar.innerHTML = '';
        container.appendChild(statsBar);
    }

    var addBtn = document.createElement('button');
    addBtn.textContent = '+';
    addBtn.title = 'Start a new measurement group to compare a different section';
    addBtn.style.cssText = 'background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.3); '
        + 'color:#fff; font:bold 14px sans-serif; width:22px; height:22px; border-radius:4px; '
        + 'cursor:pointer; display:flex; align-items:center; justify-content:center; padding:0; flex-shrink:0;';
    addBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        measureGroups.push([]);
        currentGroup = measureGroups.length - 1;
        updateStatsBar();
    });

    function groupStats(group) {
        if (!group.length) return null;
        var widths = group.map(function(m) { return m.width; });
        var mn = Math.min.apply(null, widths);
        var mx = Math.max.apply(null, widths);
        var avg = Math.round(widths.reduce(function(a, b) { return a + b; }, 0) / widths.length * 2) / 2;
        return { min: mn, max: mx, avg: avg, n: widths.length };
    }

    function renderSectionPanel() {
        var counts = getSectionCounts();
        var needed = samplesPerSection;
        var totalSections = gridSections * gridSections;
        var ignoredCount = 0;
        for (var ik in ignoredSections) ignoredCount += 1;
        var activeSections = totalSections - ignoredCount;
        var totalNeeded = activeSections * needed;
        var totalDone = 0;
        var sectionsDone = 0;
        for (var k in counts) {
            if (ignoredSections[k]) continue;
            totalDone += Math.min(counts[k], needed);
            if (counts[k] >= needed) sectionsDone += 1;
        }
        var pct = totalNeeded > 0 ? Math.round(100 * totalDone / totalNeeded) : 100;

        var html = '<div class="mlw-panel-section">'
            + '<div class="mlw-panel-title">Progress</div>'
            + '<div class="mlw-panel-meter">'
            +   '<div class="mlw-panel-meter-fill" style="width:' + pct + '%;"></div>'
            + '</div>'
            + '<div class="mlw-panel-meter-label">'
            +   sectionsDone + ' / ' + activeSections + ' sections complete '
            +   '<span style="opacity:0.6;">(' + totalDone + ' / ' + totalNeeded + ' samples'
            +   (ignoredCount ? ', ' + ignoredCount + ' skipped' : '') + ')</span>'
            + '</div>'
            + '<div class="mlw-panel-grid">';
        for (var r = 0; r < gridSections; r++) {
            for (var c = 0; c < gridSections; c++) {
                var key = r + ',' + c;
                var n = counts[key];
                var cls, content;
                if (ignoredSections[key]) {
                    cls = 'mlw-cell-skip';
                    content = '—';
                } else if (n >= needed) {
                    cls = 'mlw-cell-done';
                    content = '✓';
                } else {
                    cls = n > 0 ? 'mlw-cell-partial' : 'mlw-cell-empty';
                    content = n + '/' + needed;
                }
                html += '<div class="mlw-cell ' + cls + '" data-section="' + key
                    + '" title="Click to ' + (ignoredSections[key] ? 'include' : 'skip')
                    + ' this section">' + content + '</div>';
            }
        }
        html += '</div>'
            + '<div class="mlw-panel-hint">Click a section to skip it if there are no lines there.</div>'
            + '</div>';

        statsBar.innerHTML = html;

        var cellEls = statsBar.querySelectorAll('.mlw-cell[data-section]');
        for (var ci = 0; ci < cellEls.length; ci++) {
            cellEls[ci].addEventListener('click', (function(sec) {
                return function() {
                    var parts = sec.split(',');
                    toggleSectionIgnored(parseInt(parts[0]), parseInt(parts[1]));
                };
            })(cellEls[ci].getAttribute('data-section')));
        }
    }

    function renderMeasureStats() {
        if (!measureStatsTarget) return;

        var allWidths = [];
        for (var gi = 0; gi < measureGroups.length; gi++) {
            for (var mi = 0; mi < measureGroups[gi].length; mi++) {
                allWidths.push(measureGroups[gi][mi].width);
            }
        }

        if (!allWidths.length) {
            measureStatsTarget.innerHTML = '<div class="mlw-measures-stat-empty">No samples yet</div>';
            return;
        }

        var mn = Math.min.apply(null, allWidths);
        var mx = Math.max.apply(null, allWidths);
        var avg = Math.round(allWidths.reduce(function(a, b) { return a + b; }, 0) / allWidths.length * 2) / 2;
        measureStatsTarget.innerHTML =
            '<div class="mlw-measures-stat"><span>Count</span><strong>' + allWidths.length + '</strong></div>'
            + '<div class="mlw-measures-stat"><span>Min</span><strong>' + mn + ' px</strong></div>'
            + '<div class="mlw-measures-stat"><span>Avg</span><strong>' + avg + ' px</strong></div>'
            + '<div class="mlw-measures-stat"><span>Max</span><strong>' + mx + ' px</strong></div>';
    }

    function alignLabel(contrastAlign) {
        if (contrastAlign === 'parallel') return 'Parallel';
        if (contrastAlign === 'perpendicular') return 'Perpendicular';
        if (contrastAlign === 'unclear') return 'Unclear';
        return '—';
    }

    function ensureMeasureId(m) {
        if (!m._id) m._id = ++measureIdCounter;
        return m._id;
    }

    function getMeasurementById(id) {
        if (id === null || id === undefined) return null;
        for (var gi = 0; gi < measureGroups.length; gi++) {
            for (var mi = 0; mi < measureGroups[gi].length; mi++) {
                if (measureGroups[gi][mi]._id === id) return measureGroups[gi][mi];
            }
        }
        return null;
    }

    function collectMeasureRows() {
        var rows = [];
        for (var gi = 0; gi < measureGroups.length; gi++) {
            for (var mi = 0; mi < measureGroups[gi].length; mi++) {
                var m = measureGroups[gi][mi];
                ensureMeasureId(m);
                rows.push(m);
            }
        }
        return rows;
    }

    function getDisplayedMeasure(rows) {
        rows = rows || collectMeasureRows();
        if (hoveredMeasureId !== null) {
            var hovered = getMeasurementById(hoveredMeasureId);
            if (hovered) return hovered;
        }
        if (latestMeasureId !== null) {
            var latest = getMeasurementById(latestMeasureId);
            if (latest) return latest;
        }
        return rows.length ? rows[rows.length - 1] : null;
    }

    function getLoupeCenter(mouseX, mouseY) {
        var hovered = getMeasurementById(hoveredMeasureId);
        if (hovered) return { x: hovered.cx, y: hovered.cy };
        if (mouseX !== undefined && mouseY !== undefined) return { x: mouseX, y: mouseY };
        if (lastMouse) return { x: lastMouse.x, y: lastMouse.y };
        var latest = getMeasurementById(latestMeasureId);
        if (latest) return { x: latest.cx, y: latest.cy };
        return null;
    }

    function syncMeasureHoverUI(id) {
        if (measureHistogramTarget) {
            var ptEls = measureHistogramTarget.querySelectorAll('.mlw-histogram-point[data-measure-id]');
            for (var pi = 0; pi < ptEls.length; pi++) {
                var pid = parseInt(ptEls[pi].getAttribute('data-measure-id'), 10);
                if (pid === id) {
                    ptEls[pi].classList.add('mlw-hist-hover');
                    ptEls[pi].setAttribute('r', '7');
                } else {
                    ptEls[pi].classList.remove('mlw-hist-hover');
                    ptEls[pi].setAttribute('r', '5');
                }
            }
            var barEls = measureHistogramTarget.querySelectorAll('.mlw-hist-bar[data-bin]');
            for (var bi = 0; bi < barEls.length; bi++) {
                barEls[bi].classList.remove('mlw-hist-bar-hover');
            }
            if (id !== null) {
                var hoveredPt = measureHistogramTarget.querySelector('.mlw-histogram-point.mlw-hist-hover[data-bin]');
                if (hoveredPt) {
                    var binKey = hoveredPt.getAttribute('data-bin');
                    var bar = measureHistogramTarget.querySelector('.mlw-hist-bar[data-bin="' + binKey + '"]');
                    if (bar) bar.classList.add('mlw-hist-bar-hover');
                }
            }
        }
    }

    function setHoveredMeasure(id) {
        if (hoveredMeasureId === id) return;
        hoveredMeasureId = id;
        syncMeasureHoverUI(id);
        renderMeasureDetailOnly();
        if (lastMouse) invokeRedraw(lastMouse);
        else redraw();
        updateThresholdPreview();
    }

    function removeMeasurementById(id) {
        for (var gi = 0; gi < measureGroups.length; gi++) {
            for (var mi = 0; mi < measureGroups[gi].length; mi++) {
                if (measureGroups[gi][mi]._id === id) {
                    measureGroups[gi].splice(mi, 1);
                    if (hoveredMeasureId === id) hoveredMeasureId = null;
                    if (latestMeasureId === id) {
                        var remaining = collectMeasureRows();
                        latestMeasureId = remaining.length ? remaining[remaining.length - 1]._id : null;
                    }
                    updateStatsBar();
                    if (lastMouse) invokeRedraw(lastMouse);
                    else redraw();
                    return;
                }
            }
        }
    }

    function widthToBin(w, maxBin) {
        var bin = Math.round(w);
        if (bin < 1) bin = 1;
        if (bin > maxBin) bin = maxBin;
        return bin;
    }

    function renderMeasureHistogram(rows) {
        if (!measureHistogramTarget) return;

        if (!rows.length) {
            measureHistogramTarget.innerHTML = '<div class="mlw-table-empty">No samples yet.</div>';
            return;
        }

        var maxBin = 12;
        var maxW = 0;
        for (var wi = 0; wi < rows.length; wi++) {
            if (rows[wi].width > maxW) maxW = rows[wi].width;
        }
        if (maxW > 12) maxBin = Math.ceil(maxW);

        var bins = {};
        for (var bi = 1; bi <= maxBin; bi++) bins[bi] = [];
        for (var ri = 0; ri < rows.length; ri++) {
            var bin = widthToBin(rows[ri].width, maxBin);
            bins[bin].push(rows[ri]);
        }

        var maxCount = 1;
        for (var bc = 1; bc <= maxBin; bc++) {
            if (bins[bc].length > maxCount) maxCount = bins[bc].length;
        }

        var svgW = 210;
        var svgH = 132;
        var margin = { l: 30, r: 8, t: 10, b: 24 };
        var plotW = svgW - margin.l - margin.r;
        var plotH = svgH - margin.t - margin.b;
        var baseY = margin.t + plotH;
        var binW = plotW / maxBin;

        function countHeight(count) {
            return count > 0 ? (count / maxCount) * plotH : 0;
        }

        function binCenterX(binNum) {
            return margin.l + (binNum - 0.5) * binW;
        }

        var html = '<svg class="mlw-histogram" viewBox="0 0 ' + svgW + ' ' + svgH + '" role="img" aria-label="Line width histogram">'
            + '<line class="mlw-hist-tick" x1="' + margin.l + '" y1="' + baseY + '" x2="' + (margin.l + plotW) + '" y2="' + baseY + '"/>'
            + '<line class="mlw-hist-tick" x1="' + margin.l + '" y1="' + margin.t + '" x2="' + margin.l + '" y2="' + baseY + '"/>';

        for (var yi = 0; yi <= maxCount; yi++) {
            var ty = baseY - (yi / maxCount) * plotH;
            html += '<line class="mlw-hist-tick" x1="' + (margin.l - 3) + '" y1="' + ty + '" x2="' + margin.l + '" y2="' + ty + '"/>';
            html += '<text class="mlw-hist-axis" x="' + (margin.l - 5) + '" y="' + (ty + 3) + '" text-anchor="end">' + yi + '</text>';
        }
        html += '<text class="mlw-hist-axis" x="10" y="' + (margin.t + plotH / 2) + '" text-anchor="middle" transform="rotate(-90 10 ' + (margin.t + plotH / 2) + ')">count</text>';

        for (var b = 1; b <= maxBin; b++) {
            var items = bins[b];
            var count = items.length;
            var bh = countHeight(count);
            var bx = margin.l + (b - 1) * binW + 1;
            var barHover = false;
            for (var hi = 0; hi < items.length; hi++) {
                if (items[hi]._id === hoveredMeasureId) { barHover = true; break; }
            }
            if (count > 0) {
                html += '<rect class="mlw-hist-bar' + (barHover ? ' mlw-hist-bar-hover' : '') + '" data-bin="' + b
                    + '" x="' + bx.toFixed(1) + '" y="' + (baseY - bh).toFixed(1) + '" width="' + (binW - 2).toFixed(1)
                    + '" height="' + bh.toFixed(1) + '"/>';
            }
            var tx = binCenterX(b);
            html += '<line class="mlw-hist-tick" x1="' + tx + '" y1="' + (baseY - 3) + '" x2="' + tx + '" y2="' + baseY + '"/>';
            html += '<text class="mlw-hist-axis" x="' + tx + '" y="' + (baseY + 12) + '" text-anchor="middle">' + b + '</text>';

            for (var ji = 0; ji < items.length; ji++) {
                var m = items[ji];
                var cx = binCenterX(b);
                var cy = count > 0
                    ? baseY - bh + ((ji + 0.5) / count) * bh
                    : baseY - 8;
                var alignCls = m.contrastAlign || 'unknown';
                var hoverCls = m._id === hoveredMeasureId ? ' mlw-hist-hover' : '';
                var r = hoverCls ? 7 : 5;
                html += '<circle class="mlw-histogram-point ' + alignCls + hoverCls + '" data-measure-id="' + m._id
                    + '" data-bin="' + b + '" cx="' + cx.toFixed(1) + '" cy="' + cy.toFixed(1) + '" r="' + r + '">'
                    + '<title>Click to remove · ' + m.width + ' px · bin ' + b + ' · ' + alignLabel(m.contrastAlign) + '</title></circle>';
            }
        }

        html += '<text class="mlw-hist-axis" x="' + (margin.l + plotW / 2) + '" y="' + (svgH - 2) + '" text-anchor="middle">line width (px)</text>';
        html += '</svg>';
        measureHistogramTarget.innerHTML = html;

        var ptEls = measureHistogramTarget.querySelectorAll('.mlw-histogram-point[data-measure-id]');
        for (var pj = 0; pj < ptEls.length; pj++) {
            var ptId = parseInt(ptEls[pj].getAttribute('data-measure-id'), 10);
            ptEls[pj].addEventListener('mouseenter', (function(id) {
                return function() { setHoveredMeasure(id); };
            })(ptId));
            ptEls[pj].addEventListener('mouseleave', function() { setHoveredMeasure(null); });
            ptEls[pj].addEventListener('click', (function(id) {
                return function(e) {
                    e.stopPropagation();
                    e.preventDefault();
                    removeMeasurementById(id);
                };
            })(ptId));
        }
    }

    function buildMeasureDetailHtml(m, rows) {
        if (!m) {
            return '<div class="mlw-table-empty">Click on a line to add measurements.</div>';
        }

        var idx = 0;
        for (var i = 0; i < rows.length; i++) {
            if (rows[i]._id === m._id) {
                idx = i + 1;
                break;
            }
        }

        var caption = hoveredMeasureId !== null ? 'Hovered sample' : 'Latest sample';
        var hoverCls = hoveredMeasureId !== null ? ' class="mlw-row-hover"' : '';
        var sec = getGridSection(m.cx, m.cy) || '—';
        var alignCls = m.contrastAlign || 'unknown';

        return '<div class="mlw-measure-detail-caption">' + caption + '</div>'
            + '<table class="mlw-measure-table"><thead><tr>'
            + '<th>#</th><th>Section</th><th>X</th><th>Y</th><th>Width</th><th>Indicator</th>'
            + '<th class="mlw-th-actions"></th>'
            + '</tr></thead><tbody>'
            + '<tr data-measure-id="' + m._id + '"' + hoverCls + '>'
            + '<td>' + idx + '</td>'
            + '<td>' + sec + '</td>'
            + '<td>' + Math.round(m.nx) + '</td>'
            + '<td>' + Math.round(m.ny) + '</td>'
            + '<td><strong>' + m.width + ' px</strong></td>'
            + '<td><span class="mlw-align-dot ' + alignCls + '"></span>'
            + alignLabel(m.contrastAlign) + '</td>'
            + '<td class="mlw-td-actions">'
            + '<button type="button" class="mlw-row-remove" data-measure-id="' + m._id
            + '" title="Remove measurement" aria-label="Remove measurement">&times;</button>'
            + '</td>'
            + '</tr></tbody></table>';
    }

    function bindMeasureDetailRemove() {
        if (!measureTableTarget) return;
        var removeBtn = measureTableTarget.querySelector('.mlw-row-remove');
        if (!removeBtn) return;
        removeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            e.preventDefault();
            removeMeasurementById(parseInt(this.getAttribute('data-measure-id'), 10));
        });
    }

    function renderMeasureDetailOnly() {
        if (!measureTableTarget) return;
        var rows = collectMeasureRows();
        if (!rows.length) {
            measureTableTarget.innerHTML = '<div class="mlw-table-empty">Click on a line to add measurements.</div>';
            return;
        }
        measureTableTarget.innerHTML = buildMeasureDetailHtml(getDisplayedMeasure(rows), rows);
        bindMeasureDetailRemove();
    }

    function renderMeasureTable() {
        if (!measureTableTarget) return;

        var rows = collectMeasureRows();

        if (rows.length === 0) {
            measureTableTarget.innerHTML = '<div class="mlw-table-empty">Click on a line to add measurements.</div>';
            renderMeasureHistogram([]);
            return;
        }

        measureTableTarget.innerHTML = buildMeasureDetailHtml(getDisplayedMeasure(rows), rows);
        bindMeasureDetailRemove();
        renderMeasureHistogram(rows);
    }

    function updateStatsBar() {
        // Rich per-section panel (rule-2 measurement page).
        if (externalStatsTarget && gridSections && samplesPerSection) {
            renderSectionPanel();
            renderMeasureStats();
            renderMeasureTable();
            return;
        }

        var parts = [];
        for (var gi = 0; gi < measureGroups.length; gi++) {
            var s = groupStats(measureGroups[gi]);
            var c = GROUP_COLORS[gi % GROUP_COLORS.length];
            var label = measureGroups.length > 1 ? 'G' + (gi + 1) : '';
            var active = gi === currentGroup ? 'border-bottom:2px solid ' + c + ';' : 'opacity:0.6;';
            if (!s) {
                parts.push('<span style="color:' + c + '; padding:2px 4px; cursor:pointer; ' + active + '" data-gidx="' + gi + '">'
                    + label + (label ? ' ' : '') + '(click to measure)</span>');
            } else {
                parts.push('<span style="color:' + c + '; padding:2px 4px; cursor:pointer; ' + active + '" data-gidx="' + gi + '">'
                    + (label ? label + ': ' : '')
                    + 'Min ' + s.min + ' | Avg ' + s.avg + ' | Max ' + s.max
                    + '  <span style="opacity:0.5;">(' + s.n + ')</span></span>');
            }
        }
        statsBar.innerHTML = parts.join('<span style="opacity:0.25;">|</span>');
        if (showAddButton) statsBar.appendChild(addBtn);

        // Click on a group label to switch to it
        var spans = statsBar.querySelectorAll('[data-gidx]');
        for (var i = 0; i < spans.length; i++) {
            spans[i].addEventListener('click', (function(idx) {
                return function(e) {
                    e.stopPropagation();
                    currentGroup = idx;
                    updateStatsBar();
                };
            })(parseInt(spans[i].getAttribute('data-gidx'))));
        }
    }
    updateStatsBar();

    function setActiveTool(tool) {
        activeTool = tool;
        previewMeasurement = null;
        if (toolsContainer) {
            toolsContainer.querySelectorAll('.mlw-tool-btn').forEach(function(btn) {
                btn.classList.toggle('active', btn.getAttribute('data-tool') === tool);
            });
        }
        canvas.style.cursor = 'crosshair';
        if (onToolChange) onToolChange(tool);
        if (thresholdContainer) {
            updateThresholdPreview();
            updateFitCircleReadout();
        }
        if (lastMouse) invokeRedraw(lastMouse);
        else redraw();
    }

    if (toolsContainer) {
        toolsContainer.innerHTML =
            '<button type="button" class="mlw-tool-btn" data-tool="click" title="Click on a line to auto-measure">'
            + 'Click</button>'
            + '<button type="button" class="mlw-tool-btn" data-tool="circle" title="Center circle on line, scroll to resize">'
            + 'Circle</button>'
            + '<button type="button" class="mlw-tool-btn" data-tool="fit" title="Fit circle over line; stroke spans side to side">'
            + 'Fit</button>';
        toolsContainer.querySelectorAll('.mlw-tool-btn').forEach(function(btn) {
            btn.classList.toggle('active', btn.getAttribute('data-tool') === activeTool);
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                setActiveTool(btn.getAttribute('data-tool'));
            });
        });
    } else if (onToolChange) {
        onToolChange(activeTool);
    }

    function updateThresholdReadout() {
        if (!thresholdContainer) return;
        var readout = thresholdContainer.querySelector('.mlw-threshold-auto-readout');
        if (!readout) return;
        if (thresholdMode === 'auto') {
            readout.textContent = lastAutoThreshold !== null
                ? 'Auto at cursor: ' + lastAutoThreshold
                : 'Auto at cursor: —';
        } else {
            readout.textContent = 'Using manual: ' + thresholdManual;
        }
    }

    function updateThresholdPreview() {
        var pt = getLoupeCenter();
        if (!pt || !srcReady) {
            previewMeasurement = null;
            return;
        }
        if (activeTool === 'fit') {
            previewMeasurement = measureWidthInCircle(pt.x, pt.y, fitCircleRadius);
        } else {
            previewMeasurement = measureWidthAt(pt.x, pt.y);
        }
    }

    function setThresholdMode(mode) {
        thresholdMode = mode;
        if (!thresholdContainer) return;
        var slider = thresholdContainer.querySelector('.mlw-threshold-slider');
        thresholdContainer.querySelectorAll('.mlw-threshold-mode').forEach(function(btn) {
            btn.classList.toggle('active', btn.getAttribute('data-mode') === mode);
        });
        if (slider) slider.disabled = mode !== 'manual';
        updateThresholdReadout();
        updateThresholdPreview();
        if (lastMouse) invokeRedraw(lastMouse);
        else redraw();
    }

    function updateFitCircleReadout() {
        if (!thresholdContainer) return;
        var el = thresholdContainer.querySelector('.mlw-fit-radius-readout');
        if (!el) return;
        el.textContent = 'Measure circle: ' + Math.round(fitCircleRadius) + 'px — scroll on image to resize';
    }

    function initThresholdPanel() {
        if (!thresholdContainer) return;
        thresholdContainer.innerHTML =
            '<div class="mlw-panel-title">Edge threshold</div>'
            + '<div class="mlw-threshold-modes">'
            + '<button type="button" class="mlw-tool-btn mlw-threshold-mode active" data-mode="auto">Auto</button>'
            + '<button type="button" class="mlw-tool-btn mlw-threshold-mode" data-mode="manual">Manual</button>'
            + '</div>'
            + '<div class="mlw-threshold-slider-row">'
            + '<input type="range" class="mlw-threshold-slider" min="0" max="255" step="1" value="128" disabled>'
            + '<span class="mlw-threshold-value">128</span>'
            + '</div>'
            + '<div class="mlw-threshold-auto-readout">Auto at cursor: —</div>'
            + '<div class="mlw-fit-radius-readout mlw-threshold-auto-readout" style="margin-top:8px;">Measure circle: 18px — scroll on image to resize</div>'
            + '<p class="mlw-threshold-hint">Brightness cutoff for edge detection. Tune if widths look too wide or narrow.</p>';

        var slider = thresholdContainer.querySelector('.mlw-threshold-slider');
        var valueEl = thresholdContainer.querySelector('.mlw-threshold-value');

        thresholdContainer.querySelectorAll('.mlw-threshold-mode').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                setThresholdMode(btn.getAttribute('data-mode'));
            });
        });

        slider.addEventListener('input', function() {
            thresholdManual = parseInt(slider.value, 10);
            if (valueEl) valueEl.textContent = thresholdManual;
            updateThresholdReadout();
            updateThresholdPreview();
            if (lastMouse) invokeRedraw(lastMouse);
            else redraw();
        });
        updateFitCircleReadout();
    }

    initThresholdPanel();

    var LOUPE_SIZE = 160;
    var INLINE_LOUPE_SIZE = 128;
    var LOUPE_ZOOM = 6;
    var LOUPE_MARGIN = 12;
    var LOUPE_FIT_RADIUS_SCALE = 0.8;
    var LOUPE_RING_ALPHA = 0.2;
    var LOUPE_TINT_ALPHA = 0.05;
    var MAX_SCAN = Math.floor(LOUPE_SIZE / 2 / LOUPE_ZOOM);

    function getMaxFitCircleRadius() {
        var loupePx = inlineLoupe ? INLINE_LOUPE_SIZE : (useFixedLoupe ? LOUPE_SIZE : null);
        if (loupePx) {
            return Math.max(FIT_CIRCLE_MIN, Math.floor(loupePx / 2) - FIT_CIRCLE_LOUPE_PAD);
        }
        return FIT_CIRCLE_MAX;
    }

    fitCircleRadius = Math.min(fitCircleRadius, getMaxFitCircleRadius());

    function getPixel(px, py) {
        if (px < 0 || py < 0 || px >= natW || py >= natH) return { r: 255, g: 255, b: 255, a: 0 };
        var idx = (py * natW + px) * 4;
        var d = imgData.data;
        return { r: d[idx], g: d[idx+1], b: d[idx+2], a: d[idx+3] };
    }

    function brightness(px, py) {
        var p = getPixel(px, py);
        return 0.299 * p.r + 0.587 * p.g + 0.114 * p.b;
    }

    function alpha(px, py) {
        return getPixel(px, py).a;
    }

    // Bilinear interpolated brightness for sub-pixel accuracy
    function brightnessAt(fx, fy) {
        var x0 = Math.floor(fx), y0 = Math.floor(fy);
        var x1 = x0 + 1, y1 = y0 + 1;
        var dx = fx - x0, dy = fy - y0;
        var b00 = brightness(x0, y0), b10 = brightness(x1, y0);
        var b01 = brightness(x0, y1), b11 = brightness(x1, y1);
        return b00 * (1 - dx) * (1 - dy) + b10 * dx * (1 - dy) + b01 * (1 - dx) * dy + b11 * dx * dy;
    }

    function alphaAt(fx, fy) {
        var x0 = Math.floor(fx), y0 = Math.floor(fy);
        var x1 = x0 + 1, y1 = y0 + 1;
        var dx = fx - x0, dy = fy - y0;
        var a00 = alpha(x0, y0), a10 = alpha(x1, y0);
        var a01 = alpha(x0, y1), a11 = alpha(x1, y1);
        return a00 * (1 - dx) * (1 - dy) + a10 * dx * (1 - dy) + a01 * (1 - dx) * dy + a11 * dx * dy;
    }

    function getCenterContrastGradient(canvasX, canvasY) {
        var cx = Math.floor(canvasX * scaleX);
        var cy = Math.floor(canvasY * scaleY);
        if (cx < 1 || cy < 1 || cx >= natW - 1 || cy >= natH - 1) {
            return { gx: 0, gy: 0, mag: 0, angle: 0 };
        }

        var gxB = brightness(cx + 1, cy) - brightness(cx - 1, cy);
        var gyB = brightness(cx, cy + 1) - brightness(cx, cy - 1);
        var magB = Math.sqrt(gxB * gxB + gyB * gyB);

        var gxA = alpha(cx + 1, cy) - alpha(cx - 1, cy);
        var gyA = alpha(cx, cy + 1) - alpha(cx, cy - 1);
        var magA = Math.sqrt(gxA * gxA + gyA * gyA);

        if (hasTransparency && magA > magB && magA >= 10) {
            return { gx: gxA, gy: gyA, mag: magA, angle: Math.atan2(gyA, gxA) };
        }
        return { gx: gxB, gy: gyB, mag: magB, angle: Math.atan2(gyB, gxB) };
    }

    function angleDiffRad(a, b) {
        var d = Math.abs(a - b) % Math.PI;
        if (d > Math.PI / 2) d = Math.PI - d;
        return d;
    }

    // Width segment should run parallel to local contrast gradient (across the stroke).
    function classifyLineVsGradient(measAngle, gradAngle, gradMag) {
        if (gradMag < 8) return 'unclear';
        var d = angleDiffRad(measAngle, gradAngle);
        if (d <= Math.PI / 6) return 'parallel';
        if (d >= Math.PI / 3) return 'perpendicular';
        return 'unclear';
    }

    function measureWidthAt(canvasX, canvasY) {
        if (!srcReady || !imgData) return null;

        var cx = Math.floor(canvasX * scaleX);
        var cy = Math.floor(canvasY * scaleY);
        if (cx < 0 || cy < 0 || cx >= natW || cy >= natH) return null;

        var centerBright = brightness(cx, cy);
        var centerAlpha = alpha(cx, cy);

        // Estimate background from within the loupe's visible radius
        var bgSamples = [];
        var bgAlphaSamples = [];
        var bgMinR = Math.max(2, Math.ceil(MAX_SCAN * 0.4));
        var bgMaxR = MAX_SCAN;
        for (var sd = 0; sd < 16; sd++) {
            var sa = sd * Math.PI / 8;
            for (var sr = bgMinR; sr <= bgMaxR; sr += 1) {
                var spx = Math.round(cx + Math.cos(sa) * sr);
                var spy = Math.round(cy + Math.sin(sa) * sr);
                if (spx >= 0 && spy >= 0 && spx < natW && spy < natH) {
                    bgSamples.push(brightness(spx, spy));
                    bgAlphaSamples.push(alpha(spx, spy));
                }
            }
        }
        bgSamples.sort(function(a, b) { return b - a; });

        // Decide detection mode. Only use alpha-edge detection when the LOCAL
        // background is actually transparent (opaque line on transparent bg).
        // A global "any transparent pixel" flag wrongly flips opaque-white-bg
        // line art into alpha mode, where no alpha edge exists and every ray
        // fails to find the line.
        var bgAlphaMedian = 255;
        if (bgAlphaSamples.length) {
            var bgAlphaSorted = bgAlphaSamples.slice().sort(function(a, b) { return a - b; });
            bgAlphaMedian = bgAlphaSorted[Math.floor(bgAlphaSorted.length / 2)];
        }
        var useAlphaMode = hasTransparency && centerAlpha > 128 && bgAlphaMedian < 128;

        var bgBrightHigh = bgSamples.length > 8 ? bgSamples[Math.floor(bgSamples.length * 0.15)] : 255;
        var bgBrightLow = bgSamples.length > 8 ? bgSamples[Math.floor(bgSamples.length * 0.85)] : 0;

        // Determine if we have a dark line on light background or vice versa
        var isDarkLine = centerBright < (bgBrightHigh + bgBrightLow) / 2;
        var bgBright = isDarkLine ? bgBrightHigh : bgBrightLow;
        var contrast = Math.abs(centerBright - bgBright);

        // Threshold at half the contrast (or manual override)
        var autoThreshold = (centerBright + bgBright) / 2;
        lastAutoThreshold = Math.round(autoThreshold);
        updateThresholdReadout();
        var threshold = useAlphaMode
            ? 128
            : (thresholdMode === 'manual' ? thresholdManual : autoThreshold);

        // Bail if there's almost no contrast (clicked on background, not a line)
        if (!useAlphaMode && contrast < 15 && thresholdMode === 'auto') return null;

        var angles = [];
        for (var deg = 0; deg < 180; deg += 3) {
            angles.push(deg * Math.PI / 180);
        }

        var PARALLEL_OFFSETS = [-3, -2, -1, 0, 1, 2, 3];

        var bestWidth = Infinity;
        var bestA = null, bestB = null;

        for (var ai = 0; ai < angles.length; ai++) {
            var ang = angles[ai];
            var dx = Math.cos(ang);
            var dy = Math.sin(ang);
            var perpDx = -dy;
            var perpDy = dx;

            var rayWidths = [];
            var rayAs = [];
            var rayBs = [];

            for (var oi = 0; oi < PARALLEL_OFFSETS.length; oi++) {
                var off = PARALLEL_OFFSETS[oi];
                var ox = cx + perpDx * off;
                var oy = cy + perpDy * off;

                var posD = findEdge(ox, oy, dx, dy, isDarkLine, threshold, useAlphaMode);
                var negD = findEdge(ox, oy, -dx, -dy, isDarkLine, threshold, useAlphaMode);

                if (posD !== null && negD !== null) {
                    var totalW = posD + negD;
                    if (totalW >= 0.5 && totalW < MAX_SCAN * 1.5) {
                        rayWidths.push(totalW);
                        rayAs.push({ x: (ox + dx * posD) / scaleX, y: (oy + dy * posD) / scaleY });
                        rayBs.push({ x: (ox - dx * negD) / scaleX, y: (oy - dy * negD) / scaleY });
                    }
                }
            }

            if (rayWidths.length < 3) continue;

            // Trim outliers then take median for robustness
            var sorted = rayWidths.slice().sort(function(a, b) { return a - b; });
            var q1 = sorted[Math.floor(sorted.length * 0.25)];
            var q3 = sorted[Math.floor(sorted.length * 0.75)];
            var iqr = q3 - q1;
            var lo = q1 - 1.5 * iqr, hi = q3 + 1.5 * iqr;

            var filtered = [];
            var filteredIdx = [];
            for (var fi = 0; fi < rayWidths.length; fi++) {
                if (rayWidths[fi] >= lo && rayWidths[fi] <= hi) {
                    filtered.push(rayWidths[fi]);
                    filteredIdx.push(fi);
                }
            }
            if (filtered.length < 2) continue;

            filtered.sort(function(a, b) { return a - b; });
            var medIdx = Math.floor(filtered.length / 2);
            var medWidth = filtered[medIdx];

            // Find the original index for the median value
            var origIdx = filteredIdx[medIdx];

            if (medWidth < bestWidth) {
                bestWidth = medWidth;
                bestA = rayAs[origIdx];
                bestB = rayBs[origIdx];
            }
        }

        if (bestWidth === Infinity || bestWidth < 0.5) return null;

        var measAngle = Math.atan2(bestB.y - bestA.y, bestB.x - bestA.x);
        var grad = getCenterContrastGradient(canvasX, canvasY);
        var contrastAlign = classifyLineVsGradient(measAngle, grad.angle, grad.mag);

        // cx/cy here are native source pixels (click snapped to pixel grid).
        // canvasX/canvasY are display-space for overlay drawing.
        return {
            width: Math.round(bestWidth * 2) / 2,
            ax: bestA.x, ay: bestA.y,
            bx: bestB.x, by: bestB.y,
            cx: canvasX, cy: canvasY,
            nx: cx, ny: cy,
            contrastAlign: contrastAlign,
            gradAngle: grad.angle,
            measAngle: measAngle
        };
    }

    function measureWidthInCircle(canvasX, canvasY, displayRadius) {
        if (!srcReady || !imgData) return null;

        var natCx = canvasX * scaleX;
        var natCy = canvasY * scaleY;
        var natR = Math.max(5, displayRadius * ((scaleX + scaleY) / 2));

        var bgSamples = [];
        var centerSamples = [];
        for (var si = 0; si < 32; si++) {
            var sa = si * Math.PI / 16;
            for (var sr = Math.ceil(natR * 0.72); sr <= Math.ceil(natR * 0.95); sr++) {
                var spx = Math.round(natCx + Math.cos(sa) * sr);
                var spy = Math.round(natCy + Math.sin(sa) * sr);
                if (spx >= 0 && spy >= 0 && spx < natW && spy < natH) {
                    bgSamples.push(brightness(spx, spy));
                }
            }
        }
        for (var cdx = -1; cdx <= 1; cdx++) {
            for (var cdy = -1; cdy <= 1; cdy++) {
                var cpx = Math.round(natCx) + cdx;
                var cpy = Math.round(natCy) + cdy;
                if (cpx >= 0 && cpy >= 0 && cpx < natW && cpy < natH) {
                    centerSamples.push(brightness(cpx, cpy));
                }
            }
        }
        bgSamples.sort(function(a, b) { return b - a; });
        centerSamples.sort(function(a, b) { return a - b; });

        var centerBright = centerSamples.length
            ? centerSamples[Math.floor(centerSamples.length / 2)]
            : brightness(Math.round(natCx), Math.round(natCy));
        var bgBrightHigh = bgSamples.length > 8 ? bgSamples[Math.floor(bgSamples.length * 0.15)] : 255;
        var bgBrightLow = bgSamples.length > 8 ? bgSamples[Math.floor(bgSamples.length * 0.85)] : 0;
        var isDarkLine = centerBright < (bgBrightHigh + bgBrightLow) / 2;
        var bgBright = isDarkLine ? bgBrightHigh : bgBrightLow;
        var contrast = Math.abs(centerBright - bgBright);
        var autoThreshold = (centerBright + bgBright) / 2;
        lastAutoThreshold = Math.round(autoThreshold);
        updateThresholdReadout();
        var threshold = thresholdMode === 'manual' ? thresholdManual : autoThreshold;
        if (contrast < 10 && thresholdMode === 'auto') return null;

        function isStrokeAt(fx, fy) {
            var ddx = fx - natCx;
            var ddy = fy - natCy;
            if (ddx * ddx + ddy * ddy > natR * natR) return false;
            var b = brightnessAt(fx, fy);
            return isDarkLine ? b < threshold : b > threshold;
        }

        var candidates = [];
        for (var deg = 0; deg < 180; deg += 2) {
            var ang = deg * Math.PI / 180;
            var dx = Math.cos(ang);
            var dy = Math.sin(ang);
            var tMin = null;
            var tMax = null;
            var inStroke = false;
            var runMin = 0;
            var runMax = 0;

            for (var t = -natR * 0.98; t <= natR * 0.98; t += 0.25) {
                var px = natCx + dx * t;
                var py = natCy + dy * t;
                var dist2 = (px - natCx) * (px - natCx) + (py - natCy) * (py - natCy);
                if (dist2 > natR * natR) continue;
                var stroke = isStrokeAt(px, py);
                if (stroke) {
                    if (!inStroke) {
                        runMin = t;
                        inStroke = true;
                    }
                    runMax = t;
                } else if (inStroke) {
                    if (0 >= runMin && 0 <= runMax) {
                        tMin = runMin;
                        tMax = runMax;
                    }
                    inStroke = false;
                }
            }
            if (inStroke && 0 >= runMin && 0 <= runMax) {
                tMin = runMin;
                tMax = runMax;
            }
            if (tMin === null) continue;

            var widthProf = tMax - tMin;
            if (widthProf < 0.5) continue;

            var endA_bg = !isStrokeAt(natCx + dx * (tMin - 0.75), natCy + dy * (tMin - 0.75));
            var endB_bg = !isStrokeAt(natCx + dx * (tMax + 0.75), natCy + dy * (tMax + 0.75));

            candidates.push({
                ang: ang, widthProf: widthProf, tMin: tMin, tMax: tMax,
                endA_bg: endA_bg, endB_bg: endB_bg
            });
        }

        if (!candidates.length) return null;

        // Longest stroke run through center ≈ direction along the line (tangent).
        var tangentAng = candidates[0].ang;
        var maxProf = 0;
        for (var ti = 0; ti < candidates.length; ti++) {
            if (candidates[ti].widthProf > maxProf) {
                maxProf = candidates[ti].widthProf;
                tangentAng = candidates[ti].ang;
            }
        }

        // Width is measured perpendicular to tangent (across the stroke).
        var widthAng = tangentAng + Math.PI / 2;
        if (widthAng >= Math.PI) widthAng -= Math.PI;

        var grad = getCenterContrastGradient(canvasX, canvasY);
        if (grad.mag >= 8) {
            var gradWidthAng = grad.angle % Math.PI;
            if (gradWidthAng < 0) gradWidthAng += Math.PI;
            if (angleDiffRad(widthAng, gradWidthAng) > Math.PI / 6) {
                widthAng = gradWidthAng;
            }
        }

        var widthDx = Math.cos(widthAng);
        var widthDy = Math.sin(widthAng);
        var perpDx = -widthDy;
        var perpDy = widthDx;
        var ecx = Math.round(natCx);
        var ecy = Math.round(natCy);
        var PARALLEL_OFFSETS = [-2, -1, 0, 1, 2];
        var rayWidths = [];
        var rayAs = [];
        var rayBs = [];

        for (var oi = 0; oi < PARALLEL_OFFSETS.length; oi++) {
            var off = PARALLEL_OFFSETS[oi];
            var ox = ecx + perpDx * off;
            var oy = ecy + perpDy * off;
            var posD = findEdge(ox, oy, widthDx, widthDy, isDarkLine, threshold, false);
            var negD = findEdge(ox, oy, -widthDx, -widthDy, isDarkLine, threshold, false);
            if (posD !== null && negD !== null) {
                var totalW = posD + negD;
                if (totalW >= 0.5 && totalW <= natR * 1.8) {
                    rayWidths.push(totalW);
                    rayAs.push({ x: (ox + widthDx * posD) / scaleX, y: (oy + widthDy * posD) / scaleY });
                    rayBs.push({ x: (ox - widthDx * negD) / scaleX, y: (oy - widthDy * negD) / scaleY });
                }
            }
        }

        var bestWidth = Infinity;
        var bestA = null;
        var bestB = null;
        var bestAng = widthAng;

        if (rayWidths.length >= 1) {
            var pairs = [];
            for (var ri = 0; ri < rayWidths.length; ri++) {
                pairs.push({ w: rayWidths[ri], a: rayAs[ri], b: rayBs[ri] });
            }
            pairs.sort(function(a, b) { return a.w - b.w; });
            var med = pairs[Math.floor(pairs.length / 2)];
            bestWidth = med.w;
            bestA = med.a;
            bestB = med.b;
        } else {
            // Fallback: narrowest profile near the perpendicular direction.
            var nearPerp = [];
            for (var ni = 0; ni < candidates.length; ni++) {
                var c = candidates[ni];
                if (angleDiffRad(c.ang, widthAng) <= Math.PI / 9) {
                    nearPerp.push(c);
                }
            }
            if (!nearPerp.length) {
                candidates.sort(function(a, b) { return a.widthProf - b.widthProf; });
                nearPerp = [candidates[0]];
            } else {
                nearPerp.sort(function(a, b) { return a.widthProf - b.widthProf; });
            }
            var pick = nearPerp[0];
            bestWidth = pick.widthProf;
            bestAng = pick.ang;
            var fdx = Math.cos(pick.ang);
            var fdy = Math.sin(pick.ang);
            bestA = { x: (natCx + fdx * pick.tMin) / scaleX, y: (natCy + fdy * pick.tMin) / scaleY };
            bestB = { x: (natCx + fdx * pick.tMax) / scaleX, y: (natCy + fdy * pick.tMax) / scaleY };
        }

        if (bestWidth === Infinity || bestWidth < 0.5) return null;

        var measAngle = Math.atan2(bestB.y - bestA.y, bestB.x - bestA.x);
        var contrastAlign = classifyLineVsGradient(measAngle, grad.angle, grad.mag);

        return {
            width: Math.round(bestWidth * 2) / 2,
            ax: bestA.x, ay: bestA.y,
            bx: bestB.x, by: bestB.y,
            cx: canvasX, cy: canvasY,
            nx: Math.round(natCx), ny: Math.round(natCy),
            contrastAlign: contrastAlign,
            gradAngle: grad.angle,
            measAngle: measAngle,
            widthAng: widthAng,
            tangentAng: tangentAng
        };
    }

    function findEdge(startX, startY, dx, dy, isDarkLine, threshold, useAlphaMode) {
        var prevVal, curVal;

        if (useAlphaMode) {
            prevVal = alphaAt(startX, startY);
            for (var step = 0.5; step <= MAX_SCAN; step += 0.5) {
                var fx = startX + dx * step;
                var fy = startY + dy * step;
                if (fx < 0 || fy < 0 || fx >= natW - 1 || fy >= natH - 1) {
                    return step;
                }
                curVal = alphaAt(fx, fy);
                if (prevVal >= 128 && curVal < 128) {
                    var range = Math.abs(prevVal - curVal);
                    if (range < 1) return step - 0.25;
                    return (step - 0.5) + (prevVal - 128) / range * 0.5;
                }
                prevVal = curVal;
            }
            return null;
        }

        // Brightness-based edge detection with sub-pixel stepping
        prevVal = brightnessAt(startX, startY);
        var maxGrad = 0;
        var maxGradStep = -1;

        for (var step = 0.5; step <= MAX_SCAN; step += 0.5) {
            var fx = startX + dx * step;
            var fy = startY + dy * step;
            if (fx < 0 || fy < 0 || fx >= natW - 1 || fy >= natH - 1) {
                return maxGradStep > 0 ? maxGradStep : null;
            }

            curVal = brightnessAt(fx, fy);
            var grad = Math.abs(curVal - prevVal);

            if (grad > maxGrad) {
                maxGrad = grad;
                maxGradStep = step;
            }

            // Threshold crossing: interpolate exact sub-pixel position
            var crossed = false;
            if (isDarkLine) {
                crossed = prevVal < threshold && curVal >= threshold;
            } else {
                crossed = prevVal > threshold && curVal <= threshold;
            }

            if (crossed) {
                var range = Math.abs(curVal - prevVal);
                if (range < 1) return step - 0.25;
                var frac = Math.abs(threshold - prevVal) / range;
                return (step - 0.5) + frac * 0.5;
            }

            prevVal = curVal;
        }

        // Fallback: use the point of maximum gradient if significant enough
        if (maxGrad > 10 && maxGradStep > 0) return maxGradStep;
        return null;
    }

    function getGridSection(canvasX, canvasY) {
        if (!gridSections) return null;
        var cw = w / gridSections;
        var ch = h / gridSections;
        var col = Math.min(gridSections - 1, Math.max(0, Math.floor(canvasX / cw)));
        var row = Math.min(gridSections - 1, Math.max(0, Math.floor(canvasY / ch)));
        return row + ',' + col;
    }

    function getSectionPanelStyle(canvasX, canvasY) {
        var key = getGridSection(canvasX, canvasY);
        if (!key) return { tint: null };
        var counts = getSectionCounts();
        var needed = samplesPerSection || 1;
        var n = counts[key] || 0;
        if (ignoredSections[key]) {
            return { tint: 'rgba(120, 120, 130, ' + LOUPE_TINT_ALPHA + ')' };
        }
        if (n >= needed) {
            return { tint: 'rgba(0, 220, 70, ' + LOUPE_TINT_ALPHA + ')' };
        }
        if (n > 0) {
            return { tint: 'rgba(255, 200, 0, ' + LOUPE_TINT_ALPHA + ')' };
        }
        return { tint: null };
    }

    function drawPreviewMeasurement(m) {
        if (!m) return;
        ctx.save();
        ctx.setLineDash([5, 4]);
        ctx.beginPath();
        ctx.moveTo(m.ax, m.ay);
        ctx.lineTo(m.bx, m.by);
        ctx.strokeStyle = 'rgba(0,0,0,0.55)';
        ctx.lineWidth = 3;
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(m.ax, m.ay);
        ctx.lineTo(m.bx, m.by);
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.9)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.setLineDash([]);
        drawAlignIndicator(m, true);
        ctx.font = 'bold 10px sans-serif';
        ctx.fillStyle = 'rgba(0,0,0,0.75)';
        ctx.fillText(m.width + 'px', m.cx + 10, m.cy - 10);
        ctx.fillStyle = '#00e5ff';
        ctx.fillText(m.width + 'px', m.cx + 9, m.cy - 11);
        ctx.restore();
    }

    function drawMeasurementMarks(m, color, markOpts) {
        markOpts = markOpts || {};
        color = color || '#ff3366';
        var dimmed = !!markOpts.dimmed;
        var highlighted = !!markOpts.highlighted;
        ctx.save();
        if (dimmed) ctx.globalAlpha = 0.28;
        var outerLw = highlighted ? 4 : 3;
        var innerLw = highlighted ? 2.5 : 1.5;
        ctx.beginPath();
        ctx.moveTo(m.ax, m.ay);
        ctx.lineTo(m.bx, m.by);
        ctx.strokeStyle = 'rgba(0,0,0,0.7)';
        ctx.lineWidth = outerLw;
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(m.ax, m.ay);
        ctx.lineTo(m.bx, m.by);
        ctx.strokeStyle = color;
        ctx.lineWidth = innerLw;
        ctx.stroke();
        ctx.restore();
    }

    function getAlignIndicatorStyle(contrastAlign) {
        if (contrastAlign === 'parallel') {
            return { fill: '#00e676', stroke: 'rgba(0,0,0,0.55)' };
        }
        if (contrastAlign === 'perpendicular') {
            return { fill: '#ff9100', stroke: 'rgba(0,0,0,0.55)' };
        }
        if (contrastAlign === 'unclear') {
            return { fill: '#ffd54f', stroke: 'rgba(0,0,0,0.55)' };
        }
        return { fill: '#b0bec5', stroke: 'rgba(0,0,0,0.55)' };
    }

    function drawAlignIndicator(m, highlighted, targetCtx) {
        var c = targetCtx || ctx;
        var circleR = highlighted ? 9 : 6;
        var style = getAlignIndicatorStyle(m.contrastAlign);
        if (highlighted) {
            c.beginPath();
            c.arc(m.cx, m.cy, circleR + 5, 0, 2 * Math.PI);
            c.strokeStyle = 'rgba(64, 147, 147, 0.95)';
            c.lineWidth = 2.5;
            c.stroke();
            c.beginPath();
            c.arc(m.cx, m.cy, circleR + 3, 0, 2 * Math.PI);
            c.strokeStyle = '#ffffff';
            c.lineWidth = 2;
            c.stroke();
        }
        c.beginPath();
        c.arc(m.cx, m.cy, circleR, 0, 2 * Math.PI);
        c.fillStyle = style.fill;
        c.fill();
        c.strokeStyle = style.stroke;
        c.lineWidth = highlighted ? 2 : 1.25;
        c.stroke();
    }

    function drawMeasurementLabel(m) {
        var circleR = 6;
        var circleX = m.cx;
        var circleY = m.cy;
        var text = m.width + 'px';
        ctx.font = 'bold 9px sans-serif';
        var tw = ctx.measureText(text).width;
        var pad = 3;

        var lx = circleX + circleR + 5;
        var ly = circleY;
        if (lx + tw + pad * 2 > w - 4) {
            lx = circleX - circleR - 5 - tw - pad * 2;
        }
        if (ly - 8 < 0) ly = circleY + circleR + 8;
        if (ly + 8 > h) ly = circleY - circleR - 8;

        var rx = lx - pad, ry = ly - 6 - pad, rw = tw + pad * 2, rh = 12 + pad * 2, rr = 3;
        ctx.fillStyle = 'rgba(0,0,0,0.85)';
        ctx.beginPath();
        ctx.moveTo(rx + rr, ry);
        ctx.lineTo(rx + rw - rr, ry);
        ctx.arcTo(rx + rw, ry, rx + rw, ry + rr, rr);
        ctx.lineTo(rx + rw, ry + rh - rr);
        ctx.arcTo(rx + rw, ry + rh, rx + rw - rr, ry + rh, rr);
        ctx.lineTo(rx + rr, ry + rh);
        ctx.arcTo(rx, ry + rh, rx, ry + rh - rr, rr);
        ctx.lineTo(rx, ry + rr);
        ctx.arcTo(rx, ry, rx + rr, ry, rr);
        ctx.closePath();
        ctx.fill();

        ctx.fillStyle = '#fff';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, lx, ly);
    }

    function drawCrosshair(mx, my) {
        ctx.save();
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = 'rgba(0,229,255,0.4)';
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(mx, 0); ctx.lineTo(mx, h);
        ctx.moveTo(0, my); ctx.lineTo(w, my);
        ctx.stroke();
        ctx.restore();
    }

    function getFitPreviewAt(mx, my) {
        if (activeTool !== 'fit' || !srcReady || mx === undefined || my === undefined) return null;
        if (previewMeasurement
            && Math.abs(previewMeasurement.cx - mx) < 0.02
            && Math.abs(previewMeasurement.cy - my) < 0.02
            && previewMeasurement.widthAng !== undefined) {
            return previewMeasurement;
        }
        return measureWidthInCircle(mx, my, fitCircleRadius);
    }

    function drawFitPreviewInLoupe(targetCtx, preview, mx, my, crossX, crossY, showRing) {
        if (!preview || preview.widthAng === undefined) return;

        var r = fitCircleRadius * LOUPE_ZOOM * LOUPE_FIT_RADIUS_SCALE;
        var wAng = preview.widthAng;
        var wdx = Math.cos(wAng);
        var wdy = Math.sin(wAng);
        var tdx = -wdy;
        var tdy = wdx;

        if (showRing !== false) {
            targetCtx.beginPath();
            targetCtx.arc(crossX, crossY, r, 0, 2 * Math.PI);
            targetCtx.fillStyle = 'rgba(64, 147, 147, ' + LOUPE_RING_ALPHA + ')';
            targetCtx.fill();
            targetCtx.strokeStyle = 'rgba(0,0,0,' + (LOUPE_RING_ALPHA * 0.75) + ')';
            targetCtx.lineWidth = 2;
            targetCtx.stroke();
            targetCtx.beginPath();
            targetCtx.arc(crossX, crossY, r, 0, 2 * Math.PI);
            targetCtx.strokeStyle = 'rgba(64, 147, 147, ' + LOUPE_RING_ALPHA + ')';
            targetCtx.lineWidth = 1;
            targetCtx.stroke();
        }

        targetCtx.setLineDash([4, 3]);
        targetCtx.lineWidth = 1;
        targetCtx.strokeStyle = 'rgba(64, 147, 147, ' + LOUPE_RING_ALPHA + ')';
        targetCtx.beginPath();
        targetCtx.moveTo(crossX - wdx * r * 0.98, crossY - wdy * r * 0.98);
        targetCtx.lineTo(crossX + wdx * r * 0.98, crossY + wdy * r * 0.98);
        targetCtx.stroke();
        targetCtx.setLineDash([]);

        targetCtx.setLineDash([3, 4]);
        targetCtx.strokeStyle = 'rgba(255, 255, 255, ' + LOUPE_RING_ALPHA + ')';
        targetCtx.lineWidth = 1;
        targetCtx.beginPath();
        targetCtx.moveTo(crossX - tdx * r * 0.85, crossY - tdy * r * 0.85);
        targetCtx.lineTo(crossX + tdx * r * 0.85, crossY + tdy * r * 0.85);
        targetCtx.stroke();
        targetCtx.setLineDash([]);

        var lax = crossX + (preview.ax - mx) * LOUPE_ZOOM;
        var lay = crossY + (preview.ay - my) * LOUPE_ZOOM;
        var lbx = crossX + (preview.bx - mx) * LOUPE_ZOOM;
        var lby = crossY + (preview.by - my) * LOUPE_ZOOM;
        targetCtx.beginPath();
        targetCtx.moveTo(lax, lay);
        targetCtx.lineTo(lbx, lby);
        targetCtx.strokeStyle = 'rgba(0,0,0,0.55)';
        targetCtx.lineWidth = 3;
        targetCtx.stroke();
        targetCtx.beginPath();
        targetCtx.moveTo(lax, lay);
        targetCtx.lineTo(lbx, lby);
        targetCtx.strokeStyle = 'rgba(0, 229, 255, 0.9)';
        targetCtx.lineWidth = 1.5;
        targetCtx.stroke();

        [{ x: lax, y: lay }, { x: lbx, y: lby }].forEach(function(pt) {
            targetCtx.beginPath();
            targetCtx.arc(pt.x, pt.y, 3, 0, 2 * Math.PI);
            targetCtx.fillStyle = 'rgba(0, 229, 255, 0.9)';
            targetCtx.fill();
            targetCtx.strokeStyle = 'rgba(0,0,0,0.6)';
            targetCtx.lineWidth = 1;
            targetCtx.stroke();
        });
    }

    function drawLoupeContent(targetCtx, lx, ly, mx, my, opts) {
        if (!srcReady) return;

        opts = opts || {};
        var loupeSize = opts.loupeSize || LOUPE_SIZE;
        var crossX = opts.crossX !== undefined ? opts.crossX : lx + loupeSize / 2;
        var crossY = opts.crossY !== undefined ? opts.crossY : ly + loupeSize / 2;
        var circular = !!opts.circular;
        var rr = 6;

        targetCtx.save();

        targetCtx.beginPath();
        if (circular) {
            targetCtx.arc(crossX, crossY, loupeSize / 2, 0, 2 * Math.PI);
        } else {
            targetCtx.moveTo(lx + rr, ly);
            targetCtx.lineTo(lx + loupeSize - rr, ly);
            targetCtx.arcTo(lx + loupeSize, ly, lx + loupeSize, ly + rr, rr);
            targetCtx.lineTo(lx + loupeSize, ly + loupeSize - rr);
            targetCtx.arcTo(lx + loupeSize, ly + loupeSize, lx + loupeSize - rr, ly + loupeSize, rr);
            targetCtx.lineTo(lx + rr, ly + loupeSize);
            targetCtx.arcTo(lx, ly + loupeSize, lx, ly + loupeSize - rr, rr);
            targetCtx.lineTo(lx, ly + rr);
            targetCtx.arcTo(lx, ly, lx + rr, ly, rr);
        }
        targetCtx.closePath();
        targetCtx.clip();

        var secStyle = getSectionPanelStyle(mx, my);

        var halfSrc = (loupeSize / 2 / LOUPE_ZOOM);
        var srcX = mx * scaleX - halfSrc * scaleX;
        var srcY = my * scaleY - halfSrc * scaleY;
        var srcW = (loupeSize / LOUPE_ZOOM) * scaleX;
        var srcH = (loupeSize / LOUPE_ZOOM) * scaleY;

        targetCtx.imageSmoothingEnabled = false;
        targetCtx.drawImage(srcCanvas, srcX, srcY, srcW, srcH, lx, ly, loupeSize, loupeSize);
        targetCtx.imageSmoothingEnabled = true;

        if (secStyle.tint) {
            targetCtx.fillStyle = secStyle.tint;
            targetCtx.fillRect(lx, ly, loupeSize, loupeSize);
        }

        var pxSize = LOUPE_ZOOM;
        targetCtx.strokeStyle = 'rgba(128,128,128,0.18)';
        targetCtx.lineWidth = 0.5;
        for (var gx = 0; gx <= loupeSize; gx += pxSize) {
            targetCtx.beginPath(); targetCtx.moveTo(lx + gx, ly); targetCtx.lineTo(lx + gx, ly + loupeSize); targetCtx.stroke();
        }
        for (var gy = 0; gy <= loupeSize; gy += pxSize) {
            targetCtx.beginPath(); targetCtx.moveTo(lx, ly + gy); targetCtx.lineTo(lx + loupeSize, ly + gy); targetCtx.stroke();
        }

        targetCtx.strokeStyle = '#ff3366';
        targetCtx.lineWidth = 2;
        targetCtx.strokeRect(crossX - pxSize / 2, crossY - pxSize / 2, pxSize, pxSize);

        targetCtx.strokeStyle = 'rgba(255,51,102,0.35)';
        targetCtx.lineWidth = 0.5;
        targetCtx.beginPath();
        targetCtx.moveTo(crossX, ly); targetCtx.lineTo(crossX, ly + loupeSize);
        targetCtx.moveTo(lx, crossY); targetCtx.lineTo(lx + loupeSize, crossY);
        targetCtx.stroke();

        for (var gi = 0; gi < measureGroups.length; gi++) {
            var gc = GROUP_COLORS[gi % GROUP_COLORS.length];
            for (var mi = 0; mi < measureGroups[gi].length; mi++) {
                var mm = measureGroups[gi][mi];
                var lax = crossX + (mm.ax - mx) * LOUPE_ZOOM;
                var lay = crossY + (mm.ay - my) * LOUPE_ZOOM;
                var lbx = crossX + (mm.bx - mx) * LOUPE_ZOOM;
                var lby = crossY + (mm.by - my) * LOUPE_ZOOM;

                targetCtx.beginPath();
                targetCtx.moveTo(lax, lay); targetCtx.lineTo(lbx, lby);
                targetCtx.strokeStyle = 'rgba(0,0,0,0.6)';
                targetCtx.lineWidth = 3;
                targetCtx.stroke();
                targetCtx.beginPath();
                targetCtx.moveTo(lax, lay); targetCtx.lineTo(lbx, lby);
                targetCtx.strokeStyle = gc;
                targetCtx.lineWidth = 1.5;
                targetCtx.stroke();

                [{ x: lax, y: lay }, { x: lbx, y: lby }].forEach(function(pt) {
                    targetCtx.beginPath();
                    targetCtx.arc(pt.x, pt.y, 3, 0, 2 * Math.PI);
                    targetCtx.fillStyle = gc;
                    targetCtx.fill();
                    targetCtx.strokeStyle = '#000';
                    targetCtx.lineWidth = 1;
                    targetCtx.stroke();
                });
            }
        }

        if (activeTool === 'fit') {
            drawFitPreviewInLoupe(targetCtx, getFitPreviewAt(mx, my), mx, my, crossX, crossY, opts.showFitRing);
        }

        targetCtx.restore();

        targetCtx.strokeStyle = circular ? 'rgba(0,0,0,' + LOUPE_RING_ALPHA + ')' : 'rgba(0,0,0,0.5)';
        targetCtx.lineWidth = circular ? 1.5 : 2;
        targetCtx.beginPath();
        if (circular) {
            targetCtx.arc(crossX, crossY, loupeSize / 2, 0, 2 * Math.PI);
        } else {
            targetCtx.moveTo(lx + rr, ly);
            targetCtx.lineTo(lx + loupeSize - rr, ly);
            targetCtx.arcTo(lx + loupeSize, ly, lx + loupeSize, ly + rr, rr);
            targetCtx.lineTo(lx + loupeSize, ly + loupeSize - rr);
            targetCtx.arcTo(lx + loupeSize, ly + loupeSize, lx + loupeSize - rr, ly + loupeSize, rr);
            targetCtx.lineTo(lx + rr, ly + loupeSize);
            targetCtx.arcTo(lx, ly + loupeSize, lx, ly + loupeSize - rr, rr);
            targetCtx.lineTo(lx, ly + rr);
            targetCtx.arcTo(lx, ly, lx + rr, ly, rr);
            targetCtx.closePath();
        }
        targetCtx.stroke();

        if (!opts.hideText) {
            var labelX = circular ? crossX + loupeSize / 2 - 4 : lx + loupeSize - 4;
            var labelY = circular ? crossY + loupeSize / 2 - 3 : ly + loupeSize - 3;
            targetCtx.font = 'bold 10px sans-serif';
            targetCtx.fillStyle = 'rgba(0,0,0,0.55)';
            targetCtx.textAlign = 'right';
            targetCtx.textBaseline = 'bottom';
            targetCtx.fillText(LOUPE_ZOOM + 'x', labelX, labelY);
        }
    }

    function drawFixedLoupe(mx, my) {
        if (!loupeCanvasEl || mx === undefined || my === undefined) return;
        var lctx = loupeCanvasEl.getContext('2d');
        lctx.clearRect(0, 0, LOUPE_SIZE, LOUPE_SIZE);
        if (!srcReady) {
            lctx.fillStyle = '#f8fafa';
            lctx.fillRect(0, 0, LOUPE_SIZE, LOUPE_SIZE);
            lctx.fillStyle = '#8a9a9a';
            lctx.font = '11px sans-serif';
            lctx.textAlign = 'center';
            lctx.textBaseline = 'middle';
            lctx.fillText('Loading…', LOUPE_SIZE / 2, LOUPE_SIZE / 2);
            return;
        }
        drawLoupeContent(lctx, 0, 0, mx, my, { showFitRing: false });
    }

    function drawLoupe(mx, my) {
        if (!srcReady) return;
        if (useFixedLoupe && !inlineLoupe) return;

        if (inlineLoupe) {
            var imageMx = mx - imgOx;
            var imageMy = my - imgOy;
            drawLoupeContent(ctx, mx - INLINE_LOUPE_SIZE / 2, my - INLINE_LOUPE_SIZE / 2, imageMx, imageMy, {
                circular: true,
                crossX: mx,
                crossY: my,
                loupeSize: INLINE_LOUPE_SIZE,
                showFitRing: false,
                hideText: true
            });
            return;
        }

        var lx, ly;
        if (mx < w / 2) {
            lx = w - LOUPE_SIZE - LOUPE_MARGIN;
        } else {
            lx = LOUPE_MARGIN;
        }
        if (my < h / 2) {
            ly = h - LOUPE_SIZE - LOUPE_MARGIN;
        } else {
            ly = LOUPE_MARGIN;
        }

        drawLoupeContent(ctx, lx, ly, mx, my);
    }

    function getCircleContrastStyle(canvasX, canvasY) {
        var fallback = {
            fill: 'rgba(0, 25, 255, 0.22)',
            stroke: '#ffffff',
            cross: 'rgba(255,255,255,0.85)'
        };
        if (!srcReady || !imgData) return fallback;

        var cx = Math.floor(canvasX * scaleX);
        var cy = Math.floor(canvasY * scaleY);
        if (cx < 0 || cy < 0 || cx >= natW || cy >= natH) return fallback;

        var centerBright = brightness(cx, cy);
        var natR = Math.max(3, Math.round(circleRadius * ((scaleX + scaleY) / 2)));

        var ringSamples = [];
        for (var i = 0; i < 20; i++) {
            var ang = i * Math.PI / 10;
            var spx = Math.round(cx + Math.cos(ang) * natR);
            var spy = Math.round(cy + Math.sin(ang) * natR);
            if (spx >= 0 && spy >= 0 && spx < natW && spy < natH) {
                ringSamples.push(brightness(spx, spy));
            }
        }
        if (!ringSamples.length) return fallback;

        ringSamples.sort(function(a, b) { return a - b; });
        var ringMedian = ringSamples[Math.floor(ringSamples.length / 2)];
        var contrast = Math.abs(centerBright - ringMedian);

        var stroke, fill, cross;
        if (contrast >= 15) {
            stroke = '#00e676';
            fill = 'rgba(0, 230, 118, 0.22)';
            cross = '#00e676';
        } else if (contrast >= 8) {
            stroke = '#ffc107';
            fill = 'rgba(255, 193, 7, 0.2)';
            cross = '#ffc107';
        } else {
            stroke = '#ff5252';
            fill = 'rgba(255, 82, 82, 0.2)';
            cross = '#ff5252';
        }

        if (centerBright < 50) {
            cross = contrast >= 15 ? '#b9f6ca' : cross;
        } else if (centerBright > 210) {
            stroke = contrast >= 15 ? '#00c853' : (contrast >= 8 ? '#f9a825' : '#d32f2f');
            cross = stroke;
        }

        return { fill: fill, stroke: stroke, cross: cross };
    }

    function drawCirclePreview(mx, my) {
        if (activeTool !== 'circle' || mx === undefined || my === undefined) return;
        var style = getCircleContrastStyle(mx, my);

        ctx.beginPath();
        ctx.arc(mx, my, circleRadius, 0, 2 * Math.PI);
        ctx.fillStyle = style.fill;
        ctx.fill();
        ctx.strokeStyle = 'rgba(0,0,0,0.4)';
        ctx.lineWidth = 3;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(mx, my, circleRadius, 0, 2 * Math.PI);
        ctx.strokeStyle = style.stroke;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(mx - 6, my); ctx.lineTo(mx + 6, my);
        ctx.moveTo(mx, my - 6); ctx.lineTo(mx, my + 6);
        ctx.strokeStyle = 'rgba(0,0,0,0.35)';
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(mx - 6, my); ctx.lineTo(mx + 6, my);
        ctx.moveTo(mx, my - 6); ctx.lineTo(mx, my + 6);
        ctx.strokeStyle = style.cross;
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    function getFitCircleStyle(mx, my, preview) {
        var fallback = {
            fill: 'rgba(255, 82, 82, 0.18)',
            stroke: '#ff5252',
            widthStroke: '#ff5252',
            tangentStroke: 'rgba(255,255,255,0.5)'
        };
        if (!preview) return fallback;
        if (preview.contrastAlign === 'parallel') {
            return {
                fill: 'rgba(0, 230, 118, 0.2)',
                stroke: '#00e676',
                widthStroke: '#00e676',
                tangentStroke: 'rgba(255,255,255,0.75)'
            };
        }
        if (preview.contrastAlign === 'unclear') {
            return {
                fill: 'rgba(255, 193, 7, 0.2)',
                stroke: '#ffc107',
                widthStroke: '#ffc107',
                tangentStroke: 'rgba(255,255,255,0.65)'
            };
        }
        return {
            fill: 'rgba(255, 145, 0, 0.2)',
            stroke: '#ff9100',
            widthStroke: '#ff9100',
            tangentStroke: 'rgba(255,255,255,0.65)'
        };
    }

    function drawFitCirclePreview(mx, my) {
        if (activeTool !== 'fit' || mx === undefined || my === undefined) return;
        var preview = (srcReady && previewMeasurement
            && Math.abs(previewMeasurement.cx - mx) < 0.01
            && Math.abs(previewMeasurement.cy - my) < 0.01)
            ? previewMeasurement
            : (srcReady ? measureWidthInCircle(mx, my, fitCircleRadius) : null);
        var style = getFitCircleStyle(mx, my, preview);

        ctx.beginPath();
        ctx.arc(mx, my, fitCircleRadius, 0, 2 * Math.PI);
        ctx.fillStyle = style.fill;
        ctx.fill();
        ctx.strokeStyle = 'rgba(0,0,0,0.45)';
        ctx.lineWidth = 3;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(mx, my, fitCircleRadius, 0, 2 * Math.PI);
        ctx.strokeStyle = style.stroke;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        if (preview && preview.widthAng !== undefined) {
            var r = fitCircleRadius * 0.98;
            var wAng = preview.widthAng;
            var wdx = Math.cos(wAng);
            var wdy = Math.sin(wAng);
            var tdx = -wdy;
            var tdy = wdx;
            var perpOk = preview.contrastAlign === 'parallel';

            // Full perpendicular diameter (detected width axis, edge to edge).
            ctx.save();
            ctx.setLineDash([5, 4]);
            ctx.lineWidth = 1.25;
            ctx.strokeStyle = perpOk ? 'rgba(0, 230, 118, 0.75)' : 'rgba(255, 145, 0, 0.85)';
            ctx.beginPath();
            ctx.moveTo(mx - wdx * r, my - wdy * r);
            ctx.lineTo(mx + wdx * r, my + wdy * r);
            ctx.stroke();
            ctx.setLineDash([]);

            // Tangent (along stroke), fainter.
            ctx.setLineDash([3, 5]);
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.45)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(mx - tdx * r * 0.85, my - tdy * r * 0.85);
            ctx.lineTo(mx + tdx * r * 0.85, my + tdy * r * 0.85);
            ctx.stroke();
            ctx.setLineDash([]);

            // Right-angle marker at center (⊥).
            var arm = 7;
            ctx.strokeStyle = perpOk ? '#00e676' : '#ff9100';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(mx, my);
            ctx.lineTo(mx + wdx * arm, my + wdy * arm);
            ctx.moveTo(mx, my);
            ctx.lineTo(mx + tdx * arm, my + tdy * arm);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(mx + wdx * arm * 0.55 + tdx * arm * 0.55,
                my + wdy * arm * 0.55 + tdy * arm * 0.55, 2, 0, 2 * Math.PI);
            ctx.fillStyle = perpOk ? '#00e676' : '#ff9100';
            ctx.fill();

            // Measured width segment.
            ctx.beginPath();
            ctx.moveTo(preview.ax, preview.ay);
            ctx.lineTo(preview.bx, preview.by);
            ctx.strokeStyle = 'rgba(0,0,0,0.55)';
            ctx.lineWidth = 4;
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(preview.ax, preview.ay);
            ctx.lineTo(preview.bx, preview.by);
            ctx.strokeStyle = style.widthStroke;
            ctx.lineWidth = 2.25;
            ctx.stroke();

            [{ x: preview.ax, y: preview.ay }, { x: preview.bx, y: preview.by }].forEach(function(pt) {
                ctx.beginPath();
                ctx.arc(pt.x, pt.y, 3.5, 0, 2 * Math.PI);
                ctx.fillStyle = style.widthStroke;
                ctx.fill();
                ctx.strokeStyle = 'rgba(0,0,0,0.6)';
                ctx.lineWidth = 1;
                ctx.stroke();
            });

            if (!inlineLoupe) {
                ctx.font = 'bold 9px sans-serif';
                ctx.fillStyle = 'rgba(0,0,0,0.65)';
                ctx.fillText('width', mx + wdx * (r + 6), my + wdy * (r + 6));
                ctx.fillStyle = perpOk ? '#00e676' : '#ff9100';
                ctx.fillText('width', mx + wdx * (r + 5), my + wdy * (r + 5));

                ctx.font = 'bold 10px sans-serif';
                ctx.fillStyle = 'rgba(0,0,0,0.7)';
                ctx.fillText(preview.width + 'px', mx + 8, my - fitCircleRadius - 4);
                ctx.fillStyle = style.widthStroke;
                ctx.fillText(preview.width + 'px', mx + 7, my - fitCircleRadius - 5);
            }

            ctx.restore();
        }
    }

    function getSectionCounts() {
        // Returns { 'row,col': count } over the canvas grid. Always defined for
        // every cell so callers don't need to defensively check.
        var counts = {};
        if (!gridSections) return counts;
        var cw = w / gridSections;
        var ch = h / gridSections;
        for (var r = 0; r < gridSections; r++)
            for (var c = 0; c < gridSections; c++)
                counts[r + ',' + c] = 0;
        for (var gi = 0; gi < measureGroups.length; gi++) {
            for (var mi = 0; mi < measureGroups[gi].length; mi++) {
                var mm = measureGroups[gi][mi];
                var sec = getGridSection(mm.cx, mm.cy);
                if (sec) counts[sec] += 1;
            }
        }
        return counts;
    }

    function drawSamplingGrid() {
        if (!gridSections) return;
        var cw = w / gridSections;
        var ch = h / gridSections;
        var counts = getSectionCounts();
        var needed = samplesPerSection || 1;

        for (var r = 0; r < gridSections; r++) {
            for (var c = 0; c < gridSections; c++) {
                var key = r + ',' + c;
                if (ignoredSections[key]) {
                    ctx.fillStyle = 'rgba(120, 120, 130, 0.28)';
                    ctx.fillRect(c * cw, r * ch, cw, ch);
                    continue;
                }
                var n = counts[key];
                if (n >= needed) {
                    ctx.fillStyle = 'rgba(0, 220, 70, 0.22)';
                    ctx.fillRect(c * cw, r * ch, cw, ch);
                } else if (n > 0) {
                    ctx.fillStyle = 'rgba(255, 200, 0, 0.18)';
                    ctx.fillRect(c * cw, r * ch, cw, ch);
                }
            }
        }

        // Grid lines on top of the fill.
        ctx.strokeStyle = 'rgba(255, 60, 60, 0.85)';
        ctx.lineWidth = 1;
        for (var i = 1; i < gridSections; i++) {
            ctx.beginPath();
            ctx.moveTo(i * cw, 0);
            ctx.lineTo(i * cw, h);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(0, i * ch);
            ctx.lineTo(w, i * ch);
            ctx.stroke();
        }
    }

    function fillLoupeMargins() {
        if (!imageMargin) return;
        ctx.fillStyle = '#ffffff';
        if (imgOy > 0) ctx.fillRect(0, 0, canvasW, imgOy);
        if (imgOy + h < canvasH) ctx.fillRect(0, imgOy + h, canvasW, canvasH - imgOy - h);
        if (imgOx > 0) ctx.fillRect(0, imgOy, imgOx, h);
        if (imgOx + w < canvasW) ctx.fillRect(imgOx + w, imgOy, canvasW - imgOx - w, h);
    }

    function syncOverlayGeometry() {
        if (!imageMargin) return;
        var newCanvasW = container.clientWidth;
        var newCanvasH = container.clientHeight;
        var containerRect = container.getBoundingClientRect();
        var imgRect = imgEl.getBoundingClientRect();
        imgOx = imgRect.left - containerRect.left;
        imgOy = imgRect.top - containerRect.top;
        var newW = imgEl.offsetWidth;
        var newH = imgEl.offsetHeight;
        if (newW > 0 && newH > 0) {
            w = newW;
            h = newH;
            scaleX = natW / w;
            scaleY = natH / h;
        }
        canvasW = newCanvasW;
        canvasH = newCanvasH;
        if (canvas.width !== canvasW || canvas.height !== canvasH) {
            canvas.width = canvasW;
            canvas.height = canvasH;
            canvas.style.width = canvasW + 'px';
            canvas.style.height = canvasH + 'px';
        }
        if (loadingBanner.parentNode) {
            loadingBanner.style.top = imgOy + 'px';
            loadingBanner.style.left = imgOx + 'px';
            loadingBanner.style.width = w + 'px';
        }
    }

    function redraw(mouseX, mouseY, canvasCx, canvasCy) {
        syncOverlayGeometry();
        ctx.clearRect(0, 0, canvasW, canvasH);
        fillLoupeMargins();

        ctx.save();
        if (imageMargin) ctx.translate(imgOx, imgOy);

        drawSamplingGrid();

        var cursorSection = (mouseX !== undefined && mouseY !== undefined)
            ? getGridSection(mouseX, mouseY)
            : null;

        for (var gi = 0; gi < measureGroups.length; gi++) {
            var gc = GROUP_COLORS[gi % GROUP_COLORS.length];
            for (var mi = 0; mi < measureGroups[gi].length; mi++) {
                drawMeasurementMarks(measureGroups[gi][mi], gc);
            }
        }

        for (var giInd = 0; giInd < measureGroups.length; giInd++) {
            for (var miInd = 0; miInd < measureGroups[giInd].length; miInd++) {
                drawAlignIndicator(measureGroups[giInd][miInd], false);
            }
        }

        if (mouseX !== undefined) {
            if (activeTool === 'click') drawCrosshair(mouseX, mouseY);
            if (activeTool === 'circle') drawCirclePreview(mouseX, mouseY);
            if (activeTool === 'fit' && !inlineLoupe) drawFitCirclePreview(mouseX, mouseY);
        }

        if (thresholdContainer && previewMeasurement && activeTool !== 'fit') {
            drawPreviewMeasurement(previewMeasurement);
        }

        if (!measureTableTarget) {
            for (var gi2 = 0; gi2 < measureGroups.length; gi2++) {
                for (var mi2 = 0; mi2 < measureGroups[gi2].length; mi2++) {
                    var meas = measureGroups[gi2][mi2];
                    if (cursorSection && getGridSection(meas.cx, meas.cy) === cursorSection) continue;
                    drawMeasurementLabel(meas);
                }
            }
        }

        ctx.restore();

        if (inlineLoupe) {
            var loupeCx = canvasCx;
            var loupeCy = canvasCy;
            if (loupeCx === undefined && mouseX !== undefined) {
                loupeCx = mouseX + imgOx;
                loupeCy = mouseY + imgOy;
            }
            if (loupeCx !== undefined) drawLoupe(loupeCx, loupeCy);
            if (mouseX !== undefined && activeTool === 'fit') {
                ctx.save();
                if (imageMargin) ctx.translate(imgOx, imgOy);
                drawFitCirclePreview(mouseX, mouseY);
                ctx.restore();
            }
        }

        if (useFixedLoupe) {
            var loupeCenter = getLoupeCenter(mouseX, mouseY);
            if (loupeCenter) drawFixedLoupe(loupeCenter.x, loupeCenter.y);
            else if (loupeCanvasEl) {
                var lctx = loupeCanvasEl.getContext('2d');
                lctx.clearRect(0, 0, LOUPE_SIZE, LOUPE_SIZE);
            }
        }
    }

    function pushMeasurement(p) {
        var m = activeTool === 'fit'
            ? measureWidthInCircle(p.x, p.y, fitCircleRadius)
            : measureWidthAt(p.x, p.y);
        if (m) {
            m.scaledWidth = imgEl.offsetWidth || w;
            m.scaledHeight = imgEl.offsetHeight || h;
            ensureMeasureId(m);
            measureGroups[currentGroup].push(m);
            latestMeasureId = m._id;
            hoveredMeasureId = null;
            updateStatsBar();
        }
        return m;
    }

    function coords(e) {
        var rect = canvas.getBoundingClientRect();
        var cx = e.clientX - rect.left;
        var cy = e.clientY - rect.top;
        var ix = cx - imgOx;
        var iy = cy - imgOy;
        var onImage = ix >= 0 && iy >= 0 && ix <= w && iy <= h;
        if (!onImage) {
            return { cx: cx, cy: cy, x: ix, y: iy, onImage: false };
        }
        var srcPxX = Math.floor(ix * scaleX);
        var srcPxY = Math.floor(iy * scaleY);
        return {
            cx: cx,
            cy: cy,
            x: (srcPxX + 0.5) / scaleX,
            y: (srcPxY + 0.5) / scaleY,
            onImage: true
        };
    }

    canvas.addEventListener('mousemove', function(e) {
        var p = coords(e);
        lastMouse = p;
        if (thresholdContainer && p.onImage) updateThresholdPreview();
        invokeRedraw(p);
    });

    canvas.addEventListener('mouseleave', function() {
        lastMouse = null;
        if (thresholdContainer && hoveredMeasureId === null) previewMeasurement = null;
        redraw();
    });

    canvas.addEventListener('click', function(e) {
        var p = coords(e);
        if (!p.onImage) return;
        pushMeasurement(p);
        invokeRedraw(p);
    });

    function onCanvasWheel(e) {
        if (activeTool !== 'circle' && activeTool !== 'fit') return;
        e.preventDefault();
        var step = e.shiftKey ? 5 : Math.max(1, Math.round(Math.abs(e.deltaY) / 40));
        if (activeTool === 'fit') {
            fitCircleRadius -= Math.sign(e.deltaY) * step;
            fitCircleRadius = Math.max(FIT_CIRCLE_MIN, Math.min(fitCircleRadius, getMaxFitCircleRadius()));
            updateFitCircleReadout();
        } else {
            circleRadius -= Math.sign(e.deltaY) * step;
            circleRadius = Math.max(4, Math.min(circleRadius, FIT_CIRCLE_MAX));
        }
        if (thresholdContainer) updateThresholdPreview();
        var p = lastMouse;
        if ((!p || !p.onImage) && e.currentTarget) {
            var wheelPt = coords(e);
            if (wheelPt.onImage) p = wheelPt;
        }
        if (p && p.onImage) invokeRedraw(p);
        else if (lastMouse) invokeRedraw(lastMouse);
        else redraw();
    }
    canvas.addEventListener('wheel', onCanvasWheel, { passive: false });
    container.addEventListener('wheel', onCanvasWheel, { passive: false });

    canvas.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        var grp = measureGroups[currentGroup];
        if (grp.length) {
            grp.pop();
        } else if (measureGroups.length > 1) {
            measureGroups.pop();
            currentGroup = measureGroups.length - 1;
        }
        updateStatsBar();
        var p = coords(e);
        invokeRedraw(p.onImage ? p : null);
    });

    if (imageMargin && typeof ResizeObserver !== 'undefined') {
        var overlayResizeObserver = new ResizeObserver(function() {
            if (lastMouse) invokeRedraw(lastMouse);
            else redraw();
        });
        overlayResizeObserver.observe(container);
    }

    window._mlwMeasureGroups = measureGroups;
    _measureState = {
        canvas: canvas,
        container: container,
        statsBar: statsBar,
        statsBarOwned: !externalStatsTarget,
        loadingBanner: loadingBanner,
        loupeCanvas: loupeCanvasEl,
        measureTableTarget: measureTableTarget,
        measureHistogramTarget: measureHistogramTarget,
        getSectionCounts: getSectionCounts,
        ignoredSections: ignoredSections,
        toggleSectionIgnored: toggleSectionIgnored,
        gridSections: gridSections,
        samplesPerSection: samplesPerSection,
        scaledWidth: w,
        scaledHeight: h,
        onCanvasWheel: onCanvasWheel
    };
    updateStatsBar();
    redraw();
}

function teardownMeasureOverlay() {
    if (!_measureState) return;
    if (_measureState.onCanvasWheel) {
        _measureState.canvas.removeEventListener('wheel', _measureState.onCanvasWheel);
        if (_measureState.container) {
            _measureState.container.removeEventListener('wheel', _measureState.onCanvasWheel);
        }
    }
    _measureState.canvas.remove();
    if (_measureState.loadingBanner && _measureState.loadingBanner.parentNode) {
        _measureState.loadingBanner.remove();
    }
    if (_measureState.loupeCanvas) {
        var lctx = _measureState.loupeCanvas.getContext('2d');
        lctx.clearRect(0, 0, _measureState.loupeCanvas.width, _measureState.loupeCanvas.height);
    }
    if (_measureState.statsBar) {
        if (_measureState.statsBarOwned) {
            _measureState.statsBar.remove();
        } else {
            _measureState.statsBar.innerHTML = '';
        }
    }
    if (_measureState.measureTableTarget) {
        _measureState.measureTableTarget.innerHTML = '';
    }
    if (_measureState.measureHistogramTarget) {
        _measureState.measureHistogramTarget.innerHTML = '';
    }
    _measureState = null;
    window._mlwMeasureGroups = null;
    var btn = document.querySelector('.measure-btn.active');
    if (btn) btn.classList.remove('active');
}

function toggleMeasureOverlay(btn) {
    if (_measureState) {
        teardownMeasureOverlay();
        btn.classList.remove('active');
        return;
    }
    var listing = btn.closest('.listing.light.container');
    var img = listing.querySelector('img.design');
    if (!img) return;
    btn.classList.add('active');
    if (!img.complete || !img.naturalWidth) {
        img.onload = function() { initMeasureOverlay(img); };
    } else {
        initMeasureOverlay(img);
    }
}

// Send session data on page unload
window.addEventListener('beforeunload', function() {
    var startedAt = sessionStorage.getItem('labeling_session_start');
    var count = parseInt(sessionStorage.getItem('labeling_session_count') || '0');
    if (!startedAt || count === 0) return;

    // Calculate active time: sum gaps between consecutive timestamps,
    // but cap each gap at 2 minutes to exclude breaks.
    var stamps = JSON.parse(sessionStorage.getItem('labeling_session_stamps') || '[]');
    stamps.push(Date.now());
    var MAX_GAP_MS = 2 * 60 * 1000;
    var activeMs = 0;
    for (var i = 1; i < stamps.length; i++) {
        var gap = stamps[i] - stamps[i - 1];
        activeMs += Math.min(gap, MAX_GAP_MS);
    }
    var activeSeconds = Math.round(activeMs / 1000);

    // Compute ended_at from start + active time (not wall clock)
    var startMs = new Date(startedAt).getTime();
    var endedAt = new Date(startMs + activeMs).toISOString();

    var collectionData = document.querySelector('.collection_data');
    var params = new URLSearchParams(window.location.search);

    var payload = {
        username: params.get('labeler_id') || (collectionData ? collectionData.getAttribute('labeler_id') : ''),
        task_type: params.get('task_type') || (collectionData ? collectionData.getAttribute('task_type') : ''),
        rule_index: params.get('rule_indexes') || params.get('rule_index') || '0',
        batch_id: params.get('batch_id') || '0',
        large_sub_batch: params.get('large_sub_batch') || '0',
        started_at: startedAt,
        ended_at: endedAt,
        labels_completed: count,
        active_seconds: activeSeconds
    };

    var blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
    navigator.sendBeacon(
        window.LABELING_API_BASE_URL + '/record_labeling_session/',
        blob
    );

    sessionStorage.removeItem('labeling_session_start');
    sessionStorage.removeItem('labeling_session_count');
    sessionStorage.removeItem('labeling_session_stamps');
});