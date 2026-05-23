

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
            rule_index:rule_validator.getAttribute('rule_index'),
            labeler_id:collection_data.getAttribute('labeler_id') || new URLSearchParams(window.location.search).get('labeler_id') || ''
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
    var hasTransparency = false;

    var loadingBanner = document.createElement('div');
    loadingBanner.style.cssText = 'position:absolute; top:' + imgEl.offsetTop + 'px; left:' + imgEl.offsetLeft + 'px; '
        + 'width:' + w + 'px; text-align:center; padding:8px 0; z-index:15; '
        + 'background:rgba(0,0,0,0.7); color:#fff; font:600 13px sans-serif; '
        + 'border-radius:0 0 6px 6px; pointer-events:none;';
    loadingBanner.textContent = 'Loading pixel data…';
    container.appendChild(loadingBanner);

    function onPixelDataReady() {
        if (loadingBanner.parentNode) loadingBanner.remove();
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
        statsBar.style.cssText = 'position:absolute; top:' + imgEl.offsetTop + 'px; left:' + imgEl.offsetLeft + 'px; '
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

        // Overall measurement stats.
        var allWidths = [];
        for (var gi = 0; gi < measureGroups.length; gi++)
            for (var mi = 0; mi < measureGroups[gi].length; mi++)
                allWidths.push(measureGroups[gi][mi].width);
        html += '<div class="mlw-panel-section">'
            + '<div class="mlw-panel-title">Measurements</div>';
        if (allWidths.length === 0) {
            html += '<div class="mlw-panel-empty">Click on a line to start measuring.</div>';
        } else {
            var mn = Math.min.apply(null, allWidths);
            var mx = Math.max.apply(null, allWidths);
            var avg = Math.round(allWidths.reduce(function(a, b) { return a + b; }, 0) / allWidths.length * 2) / 2;
            html += '<div class="mlw-panel-row"><span>Count</span><strong>' + allWidths.length + '</strong></div>'
                +  '<div class="mlw-panel-row"><span>Min</span><strong>' + mn + ' px</strong></div>'
                +  '<div class="mlw-panel-row"><span>Avg</span><strong>' + avg + ' px</strong></div>'
                +  '<div class="mlw-panel-row"><span>Max</span><strong>' + mx + ' px</strong></div>';
        }
        html += '</div>';

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

    function updateStatsBar() {
        // Rich per-section panel (rule-2 measurement page).
        if (externalStatsTarget && gridSections && samplesPerSection) {
            renderSectionPanel();
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

    var LOUPE_SIZE = 160;
    var LOUPE_ZOOM = 6;
    var LOUPE_MARGIN = 12;
    var MAX_SCAN = Math.floor(LOUPE_SIZE / 2 / LOUPE_ZOOM);

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

    function measureWidthAt(canvasX, canvasY) {
        if (!srcReady || !imgData) return null;

        var cx = Math.floor(canvasX * scaleX);
        var cy = Math.floor(canvasY * scaleY);
        if (cx < 0 || cy < 0 || cx >= natW || cy >= natH) return null;

        var centerBright = brightness(cx, cy);
        var centerAlpha = alpha(cx, cy);

        // Decide detection mode: alpha-based for transparent images, brightness for opaque
        var useAlphaMode = hasTransparency && centerAlpha > 128;

        // Estimate background from within the loupe's visible radius
        var bgSamples = [];
        var bgMinR = Math.max(2, Math.ceil(MAX_SCAN * 0.4));
        var bgMaxR = MAX_SCAN;
        for (var sd = 0; sd < 16; sd++) {
            var sa = sd * Math.PI / 8;
            for (var sr = bgMinR; sr <= bgMaxR; sr += 1) {
                var spx = Math.round(cx + Math.cos(sa) * sr);
                var spy = Math.round(cy + Math.sin(sa) * sr);
                if (spx >= 0 && spy >= 0 && spx < natW && spy < natH) {
                    bgSamples.push(brightness(spx, spy));
                }
            }
        }
        bgSamples.sort(function(a, b) { return b - a; });

        var bgBrightHigh = bgSamples.length > 8 ? bgSamples[Math.floor(bgSamples.length * 0.15)] : 255;
        var bgBrightLow = bgSamples.length > 8 ? bgSamples[Math.floor(bgSamples.length * 0.85)] : 0;

        // Determine if we have a dark line on light background or vice versa
        var isDarkLine = centerBright < (bgBrightHigh + bgBrightLow) / 2;
        var bgBright = isDarkLine ? bgBrightHigh : bgBrightLow;
        var contrast = Math.abs(centerBright - bgBright);

        // Threshold at half the contrast
        var threshold = (centerBright + bgBright) / 2;

        // Bail if there's almost no contrast (clicked on background, not a line)
        if (!useAlphaMode && contrast < 15) return null;

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

        return {
            width: Math.round(bestWidth * 2) / 2,
            ax: bestA.x, ay: bestA.y,
            bx: bestB.x, by: bestB.y,
            cx: canvasX, cy: canvasY
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

    function drawMeasurement(m, color) {
        color = color || '#ff3366';
        ctx.beginPath();
        ctx.moveTo(m.ax, m.ay);
        ctx.lineTo(m.bx, m.by);
        ctx.strokeStyle = 'rgba(0,0,0,0.7)';
        ctx.lineWidth = 3;
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(m.ax, m.ay);
        ctx.lineTo(m.bx, m.by);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        [{ x: m.ax, y: m.ay }, { x: m.bx, y: m.by }].forEach(function(pt) {
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, 3, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 1;
            ctx.stroke();
        });

        ctx.beginPath();
        ctx.arc(m.cx, m.cy, 2, 0, 2 * Math.PI);
        ctx.fillStyle = '#fff';
        ctx.fill();

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

        for (var gi = 0; gi < measureGroups.length; gi++) {
            var gc = GROUP_COLORS[gi % GROUP_COLORS.length];
            for (var mi = 0; mi < measureGroups[gi].length; mi++) {
                var mm = measureGroups[gi][mi];
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
                ctx.strokeStyle = gc;
                ctx.lineWidth = 1.5;
                ctx.stroke();

                [{ x: lax, y: lay }, { x: lbx, y: lby }].forEach(function(pt) {
                    ctx.beginPath();
                    ctx.arc(pt.x, pt.y, 3, 0, 2 * Math.PI);
                    ctx.fillStyle = gc;
                    ctx.fill();
                    ctx.strokeStyle = '#000';
                    ctx.lineWidth = 1;
                    ctx.stroke();
                });
            }
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
                var col = Math.min(gridSections - 1, Math.max(0, Math.floor(mm.cx / cw)));
                var row = Math.min(gridSections - 1, Math.max(0, Math.floor(mm.cy / ch)));
                counts[row + ',' + col] += 1;
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

    function redraw(mouseX, mouseY) {
        ctx.clearRect(0, 0, w, h);

        drawSamplingGrid();

        if (mouseX !== undefined) {
            drawCrosshair(mouseX, mouseY);
        }

        for (var gi = 0; gi < measureGroups.length; gi++) {
            var gc = GROUP_COLORS[gi % GROUP_COLORS.length];
            for (var mi = 0; mi < measureGroups[gi].length; mi++) {
                drawMeasurement(measureGroups[gi][mi], gc);
            }
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
            measureGroups[currentGroup].push(m);
            updateStatsBar();
        }
        redraw(p.x, p.y);
    });

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
        redraw(p.x, p.y);
    });

    canvas.addEventListener('mouseleave', function() { redraw(); });

    window._mlwMeasureGroups = measureGroups;
    _measureState = {
        canvas: canvas,
        container: container,
        statsBar: statsBar,
        statsBarOwned: !externalStatsTarget,
        loadingBanner: loadingBanner,
        getSectionCounts: getSectionCounts,
        ignoredSections: ignoredSections,
        toggleSectionIgnored: toggleSectionIgnored,
        gridSections: gridSections,
        samplesPerSection: samplesPerSection
    };
    updateStatsBar();
    redraw();
}

function teardownMeasureOverlay() {
    if (!_measureState) return;
    _measureState.canvas.remove();
    if (_measureState.loadingBanner && _measureState.loadingBanner.parentNode) {
        _measureState.loadingBanner.remove();
    }
    if (_measureState.statsBar) {
        if (_measureState.statsBarOwned) {
            _measureState.statsBar.remove();
        } else {
            _measureState.statsBar.innerHTML = '';
        }
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