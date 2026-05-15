

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

        response = hotkey === '1' ? 'yes' : 'no'

        if (priority_element.type === 'prompt') {

            if (priority_element.element.getAttribute('prompt_type') == 'mismatch') {
                collect_mismatch_prompt(priority_element.element, response)
                update_prompt(hotkey,priority_element.element, response)
            }else{
                collect_prompt(priority_element.element, response)
                update_prompt(hotkey,priority_element.element, response)
            }

        } else if (priority_element.type === 'button_container'){

            update_button(hotkey, priority_element.element)
            collect_label(priority_element.element, response)

        } else {

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
    if (hotkey === '1' || hotkey === '2') {
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

    listing_containers.forEach(listing_container =>{
        listing_container.style.display = 'grid'
    })

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
            rule_index:rule_validator.getAttribute('rule_index')
            }


    if (!window._trainingAnswers) {
        api_collect_label_issue(data)
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
    }
})


// Increment label count on each prompt submission
var _originalCollectPrompt = typeof api_collect_prompt === 'function' ? api_collect_prompt : null;
function _incrementSessionCount() {
    var count = parseInt(sessionStorage.getItem('labeling_session_count') || '0');
    sessionStorage.setItem('labeling_session_count', String(count + 1));
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
// Line-width measurement overlay — two-point ruler (visual only, no data saved)
// Click two points to measure pixel distance. Right-click to undo last.
// Dual-stroke rendering (dark outline + bright inner) for contrast on any bg.
// ---------------------------------------------------------------------------
var _measureState = null;

function initMeasureOverlay(imgEl) {
    if (_measureState) teardownMeasureOverlay();

    var container = imgEl.parentElement;
    container.style.position = 'relative';

    var w = imgEl.offsetWidth;
    var h = imgEl.offsetHeight;

    var canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    canvas.style.cssText = 'position:absolute; top:' + imgEl.offsetTop + 'px; left:' + imgEl.offsetLeft + 'px; '
        + 'width:' + w + 'px; height:' + h + 'px; z-index:10; cursor:crosshair;';

    container.appendChild(canvas);
    var ctx = canvas.getContext('2d');

    var measurements = [];
    var pendingPoint = null;

    function dist(ax, ay, bx, by) {
        return Math.sqrt((bx - ax) * (bx - ax) + (by - ay) * (by - ay));
    }

    function drawRulerLine(ax, ay, bx, by) {
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(bx, by);
        ctx.strokeStyle = 'rgba(0,0,0,0.8)';
        ctx.lineWidth = 3;
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(bx, by);
        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 1.5;
        ctx.stroke();
    }

    function drawEndpoint(x, y) {
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fillStyle = '#00e5ff';
        ctx.fill();
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 1.5;
        ctx.stroke();
    }

    function drawLabel(ax, ay, bx, by, d) {
        var mx = (ax + bx) / 2;
        var my = (ay + by) / 2;
        var text = Math.round(d) + 'px';

        ctx.font = 'bold 12px sans-serif';
        var tw = ctx.measureText(text).width;
        var pad = 4;

        ctx.fillStyle = 'rgba(0,0,0,0.75)';
        var rx = mx - tw / 2 - pad, ry = my - 8 - pad, rw = tw + pad * 2, rh = 16 + pad * 2, rr = 4;
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
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, mx, my);
    }

    function redraw(mouseX, mouseY) {
        ctx.clearRect(0, 0, w, h);

        for (var i = 0; i < measurements.length; i++) {
            var m = measurements[i];
            drawRulerLine(m.ax, m.ay, m.bx, m.by);
            drawEndpoint(m.ax, m.ay);
            drawEndpoint(m.bx, m.by);
            drawLabel(m.ax, m.ay, m.bx, m.by, m.d);
        }

        if (pendingPoint) {
            drawEndpoint(pendingPoint.x, pendingPoint.y);
            if (mouseX !== undefined) {
                drawRulerLine(pendingPoint.x, pendingPoint.y, mouseX, mouseY);
                drawEndpoint(mouseX, mouseY);
                var d = dist(pendingPoint.x, pendingPoint.y, mouseX, mouseY);
                drawLabel(pendingPoint.x, pendingPoint.y, mouseX, mouseY, d);
            }
        } else if (mouseX !== undefined) {
            drawEndpoint(mouseX, mouseY);
        }
    }

    function coords(e) {
        var rect = canvas.getBoundingClientRect();
        return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }

    canvas.addEventListener('mousemove', function(e) {
        var p = coords(e);
        redraw(p.x, p.y);
    });

    canvas.addEventListener('click', function(e) {
        var p = coords(e);
        if (!pendingPoint) {
            pendingPoint = { x: p.x, y: p.y };
        } else {
            var d = dist(pendingPoint.x, pendingPoint.y, p.x, p.y);
            measurements.push({ ax: pendingPoint.x, ay: pendingPoint.y, bx: p.x, by: p.y, d: d });
            pendingPoint = null;
        }
        redraw(p.x, p.y);
    });

    canvas.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        if (pendingPoint) {
            pendingPoint = null;
        } else if (measurements.length) {
            measurements.pop();
        }
        var p = coords(e);
        redraw(p.x, p.y);
    });

    canvas.addEventListener('mouseleave', function() { redraw(); });

    _measureState = { canvas: canvas, container: container };
    redraw();
}

function teardownMeasureOverlay() {
    if (!_measureState) return;
    _measureState.canvas.remove();
    _measureState = null;
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

    var endedAt = new Date().toISOString();

    // Gather batch context from the page
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
        labels_completed: count
    };

    var blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
    navigator.sendBeacon(
        window.LABELING_API_BASE_URL + '/record_labeling_session/',
        blob
    );

    sessionStorage.removeItem('labeling_session_start');
    sessionStorage.removeItem('labeling_session_count');
});