

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
// Line-width auto-measure overlay
// Click ON a line to auto-detect its width. Right-click to undo.
// Scans outward in multiple angles to find the narrowest cross-section.
// ---------------------------------------------------------------------------
var _measureState = null;

function initMeasureOverlay(imgEl) {
    if (_measureState) teardownMeasureOverlay();

    var container = imgEl.parentElement;
    container.style.position = 'relative';

    var w = imgEl.offsetWidth;
    var h = imgEl.offsetHeight;
    var natW = imgEl.naturalWidth || w;
    var natH = imgEl.naturalHeight || h;
    var scaleX = natW / w;
    var scaleY = natH / h;

    var canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    canvas.style.cssText = 'position:absolute; top:' + imgEl.offsetTop + 'px; left:' + imgEl.offsetLeft + 'px; '
        + 'width:' + w + 'px; height:' + h + 'px; z-index:10; cursor:crosshair;';

    container.appendChild(canvas);
    var ctx = canvas.getContext('2d');

    var srcCanvas = document.createElement('canvas');
    srcCanvas.width = natW;
    srcCanvas.height = natH;
    var srcCtx = srcCanvas.getContext('2d');
    var srcReady = false;
    var imgData = null;

    function tryLoadImage(useCors) {
        var img2 = new Image();
        if (useCors) img2.crossOrigin = 'anonymous';
        img2.onload = function() {
            srcCtx.drawImage(img2, 0, 0, natW, natH);
            try {
                imgData = srcCtx.getImageData(0, 0, natW, natH);
                srcReady = true;
            } catch(e) {
                if (useCors) tryLoadImage(false);
            }
        };
        img2.onerror = function() {
            if (useCors) tryLoadImage(false);
        };
        img2.src = imgEl.src;
    }
    tryLoadImage(true);

    var measurements = [];

    var LOUPE_SIZE = 120;
    var LOUPE_ZOOM = 8;
    var LOUPE_MARGIN = 12;
    var MAX_SCAN = 80;

    function brightness(px, py) {
        if (px < 0 || py < 0 || px >= natW || py >= natH) return 255;
        var idx = (py * natW + px) * 4;
        var d = imgData.data;
        return 0.299 * d[idx] + 0.587 * d[idx+1] + 0.114 * d[idx+2];
    }

    function alpha(px, py) {
        if (px < 0 || py < 0 || px >= natW || py >= natH) return 0;
        return imgData.data[(py * natW + px) * 4 + 3];
    }

    function measureWidthAt(canvasX, canvasY) {
        if (!srcReady || !imgData) return null;

        var cx = Math.floor(canvasX * scaleX);
        var cy = Math.floor(canvasY * scaleY);

        var centerBright = brightness(cx, cy);
        var centerAlpha = alpha(cx, cy);

        // Sample the surrounding area to find the background brightness
        var bgSamples = [];
        for (var sd = 0; sd < 8; sd++) {
            var sa = sd * Math.PI / 4;
            for (var sr = 20; sr <= 60; sr += 10) {
                var spx = Math.round(cx + Math.cos(sa) * sr);
                var spy = Math.round(cy + Math.sin(sa) * sr);
                if (spx >= 0 && spy >= 0 && spx < natW && spy < natH) {
                    bgSamples.push(brightness(spx, spy));
                }
            }
        }
        bgSamples.sort(function(a, b) { return b - a; });
        var bgBright = bgSamples.length > 4 ? bgSamples[Math.floor(bgSamples.length * 0.25)] : 255;
        var contrast = Math.abs(bgBright - centerBright);
        var threshold = Math.max(25, contrast * 0.4);

        var angles = [];
        for (var deg = 0; deg < 180; deg += 5) {
            angles.push(deg * Math.PI / 180);
        }

        var bestWidth = Infinity;
        var bestA = null, bestB = null;

        for (var ai = 0; ai < angles.length; ai++) {
            var ang = angles[ai];
            var dx = Math.cos(ang);
            var dy = Math.sin(ang);

            var posD = findEdge(cx, cy, dx, dy, centerBright, centerAlpha, threshold);
            var negD = findEdge(cx, cy, -dx, -dy, centerBright, centerAlpha, threshold);

            if (posD !== null && negD !== null) {
                var total = posD + negD;
                if (total < bestWidth) {
                    bestWidth = total;
                    bestA = { x: (cx + dx * posD) / scaleX, y: (cy + dy * posD) / scaleY };
                    bestB = { x: (cx - dx * negD) / scaleX, y: (cy - dy * negD) / scaleY };
                }
            }
        }

        if (bestWidth === Infinity || bestWidth < 0.5) return null;

        return {
            width: Math.round(bestWidth * 2) / 2,
            ax: bestA.x, ay: bestA.y,
            bx: bestB.x, by: bestB.y,
            cx: canvasX, cy: canvasY
        };
    }

    function findEdge(startX, startY, dx, dy, refBright, refAlpha, threshold) {
        var useAlpha = refAlpha > 200;

        for (var step = 1; step <= MAX_SCAN; step++) {
            var px = Math.round(startX + dx * step);
            var py = Math.round(startY + dy * step);
            if (px < 0 || py < 0 || px >= natW || py >= natH) return step;

            if (useAlpha) {
                var a = alpha(px, py);
                if (a < 128) return step - 0.5;
            }

            var b = brightness(px, py);
            var diff = Math.abs(b - refBright);

            if (diff > threshold) {
                return step - 0.5;
            }
        }
        return null;
    }

    function drawMeasurement(m) {
        // Line through the measurement
        ctx.beginPath();
        ctx.moveTo(m.ax, m.ay);
        ctx.lineTo(m.bx, m.by);
        ctx.strokeStyle = 'rgba(0,0,0,0.7)';
        ctx.lineWidth = 3;
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(m.ax, m.ay);
        ctx.lineTo(m.bx, m.by);
        ctx.strokeStyle = '#ff3366';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Endpoints
        [{ x: m.ax, y: m.ay }, { x: m.bx, y: m.by }].forEach(function(pt) {
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, 3, 0, 2 * Math.PI);
            ctx.fillStyle = '#ff3366';
            ctx.fill();
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 1;
            ctx.stroke();
        });

        // Click point
        ctx.beginPath();
        ctx.arc(m.cx, m.cy, 2, 0, 2 * Math.PI);
        ctx.fillStyle = '#fff';
        ctx.fill();

        // Label offset from the midpoint
        var mx = (m.ax + m.bx) / 2;
        var my = (m.ay + m.by) / 2;
        var text = m.width + 'px';
        ctx.font = 'bold 13px sans-serif';
        var tw = ctx.measureText(text).width;
        var pad = 5;

        var lx = mx + 16;
        var ly = my - 16;
        if (lx + tw + pad * 2 > w) lx = mx - 16 - tw - pad * 2;
        if (ly - 14 < 0) ly = my + 20;

        var rx = lx - pad, ry = ly - 9 - pad, rw = tw + pad * 2, rh = 18 + pad * 2, rr = 4;
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

    function drawLoupe(mx, my) {
        if (!srcReady) return;

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

        var lcx = lx + LOUPE_SIZE / 2;
        var lcy = ly + LOUPE_SIZE / 2;

        ctx.save();

        var rr = 6;
        ctx.beginPath();
        ctx.moveTo(lx + rr, ly);
        ctx.lineTo(lx + LOUPE_SIZE - rr, ly);
        ctx.arcTo(lx + LOUPE_SIZE, ly, lx + LOUPE_SIZE, ly + rr, rr);
        ctx.lineTo(lx + LOUPE_SIZE, ly + LOUPE_SIZE - rr);
        ctx.arcTo(lx + LOUPE_SIZE, ly + LOUPE_SIZE, lx + LOUPE_SIZE - rr, ly + LOUPE_SIZE, rr);
        ctx.lineTo(lx + rr, ly + LOUPE_SIZE);
        ctx.arcTo(lx, ly + LOUPE_SIZE, lx, ly + LOUPE_SIZE - rr, rr);
        ctx.lineTo(lx, ly + rr);
        ctx.arcTo(lx, ly, lx + rr, ly, rr);
        ctx.closePath();
        ctx.clip();

        var halfSrc = (LOUPE_SIZE / 2 / LOUPE_ZOOM);
        var srcX = mx * scaleX - halfSrc * scaleX;
        var srcY = my * scaleY - halfSrc * scaleY;
        var srcW = (LOUPE_SIZE / LOUPE_ZOOM) * scaleX;
        var srcH = (LOUPE_SIZE / LOUPE_ZOOM) * scaleY;

        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(srcCanvas, srcX, srcY, srcW, srcH, lx, ly, LOUPE_SIZE, LOUPE_SIZE);
        ctx.imageSmoothingEnabled = true;

        var pxSize = LOUPE_ZOOM;
        ctx.strokeStyle = 'rgba(128,128,128,0.18)';
        ctx.lineWidth = 0.5;
        for (var gx = 0; gx <= LOUPE_SIZE; gx += pxSize) {
            ctx.beginPath(); ctx.moveTo(lx + gx, ly); ctx.lineTo(lx + gx, ly + LOUPE_SIZE); ctx.stroke();
        }
        for (var gy = 0; gy <= LOUPE_SIZE; gy += pxSize) {
            ctx.beginPath(); ctx.moveTo(lx, ly + gy); ctx.lineTo(lx + LOUPE_SIZE, ly + gy); ctx.stroke();
        }

        ctx.strokeStyle = '#ff3366';
        ctx.lineWidth = 2;
        ctx.strokeRect(lcx - pxSize / 2, lcy - pxSize / 2, pxSize, pxSize);

        ctx.strokeStyle = 'rgba(255,51,102,0.35)';
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(lcx, ly); ctx.lineTo(lcx, ly + LOUPE_SIZE);
        ctx.moveTo(lx, lcy); ctx.lineTo(lx + LOUPE_SIZE, lcy);
        ctx.stroke();

        // Draw measurement lines inside the loupe
        for (var mi = 0; mi < measurements.length; mi++) {
            var mm = measurements[mi];
            var lax = lcx + (mm.ax - mx) * LOUPE_ZOOM;
            var lay = lcy + (mm.ay - my) * LOUPE_ZOOM;
            var lbx = lcx + (mm.bx - mx) * LOUPE_ZOOM;
            var lby = lcy + (mm.by - my) * LOUPE_ZOOM;

            ctx.beginPath();
            ctx.moveTo(lax, lay); ctx.lineTo(lbx, lby);
            ctx.strokeStyle = 'rgba(0,0,0,0.6)';
            ctx.lineWidth = 3;
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(lax, lay); ctx.lineTo(lbx, lby);
            ctx.strokeStyle = '#ff3366';
            ctx.lineWidth = 1.5;
            ctx.stroke();

            [{ x: lax, y: lay }, { x: lbx, y: lby }].forEach(function(pt) {
                ctx.beginPath();
                ctx.arc(pt.x, pt.y, 3, 0, 2 * Math.PI);
                ctx.fillStyle = '#ff3366';
                ctx.fill();
                ctx.strokeStyle = '#000';
                ctx.lineWidth = 1;
                ctx.stroke();
            });
        }

        ctx.restore();

        ctx.strokeStyle = 'rgba(0,0,0,0.5)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(lx + rr, ly);
        ctx.lineTo(lx + LOUPE_SIZE - rr, ly);
        ctx.arcTo(lx + LOUPE_SIZE, ly, lx + LOUPE_SIZE, ly + rr, rr);
        ctx.lineTo(lx + LOUPE_SIZE, ly + LOUPE_SIZE - rr);
        ctx.arcTo(lx + LOUPE_SIZE, ly + LOUPE_SIZE, lx + LOUPE_SIZE - rr, ly + LOUPE_SIZE, rr);
        ctx.lineTo(lx + rr, ly + LOUPE_SIZE);
        ctx.arcTo(lx, ly + LOUPE_SIZE, lx, ly + LOUPE_SIZE - rr, rr);
        ctx.lineTo(lx, ly + rr);
        ctx.arcTo(lx, ly, lx + rr, ly, rr);
        ctx.closePath();
        ctx.stroke();

        ctx.font = 'bold 10px sans-serif';
        ctx.fillStyle = 'rgba(0,0,0,0.55)';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'bottom';
        ctx.fillText(LOUPE_ZOOM + 'x', lx + LOUPE_SIZE - 4, ly + LOUPE_SIZE - 3);
    }

    function redraw(mouseX, mouseY) {
        ctx.clearRect(0, 0, w, h);

        if (mouseX !== undefined) {
            drawCrosshair(mouseX, mouseY);
        }

        for (var i = 0; i < measurements.length; i++) {
            drawMeasurement(measurements[i]);
        }

        if (mouseX !== undefined) {
            drawLoupe(mouseX, mouseY);
        }
    }

    function coords(e) {
        var rect = canvas.getBoundingClientRect();
        var raw = { x: e.clientX - rect.left, y: e.clientY - rect.top };
        var srcPxX = Math.floor(raw.x * scaleX);
        var srcPxY = Math.floor(raw.y * scaleY);
        return { x: (srcPxX + 0.5) / scaleX, y: (srcPxY + 0.5) / scaleY };
    }

    canvas.addEventListener('mousemove', function(e) {
        var p = coords(e);
        redraw(p.x, p.y);
    });

    canvas.addEventListener('click', function(e) {
        var p = coords(e);
        var m = measureWidthAt(p.x, p.y);
        if (m) {
            measurements.push(m);
        }
        redraw(p.x, p.y);
    });

    canvas.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        if (measurements.length) measurements.pop();
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