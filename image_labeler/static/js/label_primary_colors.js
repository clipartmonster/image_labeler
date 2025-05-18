let highlight_colors = [
    { name: 'red', rgb_values: [255, 0, 0] },
    { name: 'blue', rgb_values: [0, 0, 255] },
    { name: 'green', rgb_values: [0, 255, 0] },
    { name: 'yellow', rgb_values: [255, 255, 0] },
    { name: 'purple', rgb_values: [128, 0, 128] }
];

var full_fill_threshold = 100
var flood_fill_threshold = 100
var brush_threshold = 25

if (window.location.pathname === '/label_images/select_primary_colors/') {
    document.addEventListener('DOMContentLoaded', function () {
        // Initialize canvases
    
        const empty_swatches = Array.from(document.getElementsByClassName('color_swatch empty'));

        empty_swatches.forEach(swatch => {

            swatch.onclick = open_color_selector

        })

    })
}

function remove_layer(event) {


    const listing_container = event.target.closest('.listing.light.container')
    const control_layer = event.target.closest('.layer_control.container')
    const layer_index = parseInt(control_layer.id.split('_')[2])
    const layer = listing_container.querySelector('#color_layer_' + String(layer_index))
    
    //remove tool indicator
    tool_indicator = listing_container.querySelector('.pixel_selection.tool.indicator.active')
    if (tool_indicator) {tool_indicator.className = 'pixel_selection tool indicator'}

    //remove canvas layer and control layer
    layer.remove()
    control_layer.remove()

    //remove from database
    asset_id = listing_container.getAttribute('asset_id')
    api_remove_color_label(asset_id, layer_index)

    //remove colormap from aws
    remove_color_layer_from_aws(event)

    const layer_controls = listing_container.querySelectorAll('.layer_control.container')
    
    if (layer_controls.length == 0) {
        listing_container.querySelector('#add_layer_button').click()
    } else {
        
        default_layer_control = layer_controls[0]
        
        // Trigger select_layer directly with a simulated event
        default_layer_control.click()
    }

    

}


function open_color_selector(event) {

    const listing_container = event.target.closest('.listing.light.container')
    const design_container = listing_container.querySelector('.design')
    const original_canvas = listing_container.querySelector('canvas.design')
    
    original_canvas.className = 'design'

    const pixel_selector = document.getElementById('pixel_selection_palette')  
    pixel_selector_copy = pixel_selector.cloneNode(true)

    pixel_selector_copy.querySelector('#flood_fill_threshold').value = flood_fill_threshold
    pixel_selector_copy.querySelector('#full_fill_threshold').value = full_fill_threshold
    pixel_selector_copy.querySelector('#brush_threshold').value = brush_threshold
    design_container.appendChild(pixel_selector_copy)
    
    add_layer(event)
   
}


function add_layer(event){
    
    const listing_container = event.target.closest('.listing.light.container')
    const pixel_selector = listing_container.querySelector('#pixel_selection_palette')
    

    //remove tool indicator
    tool_indicator = listing_container.querySelector('.pixel_selection.tool.indicator.active')
    if (tool_indicator) {tool_indicator.className = 'pixel_selection tool indicator'}

    ////////////////////
    //Get a list of all layer indexes
    layer_indices = []
    layers = Array.from(pixel_selector.querySelectorAll('div[id^="layer_control_"]'))
    layers.forEach(layer => {
 
        const id = layer.id; // Get the id, e.g., "layer_control_3"
        const index = id.split('_').pop(); // Extract the index part
        layer_indices.push(parseInt(index, 10)); // Convert to a number and push to the array
    
    })

    //get the new layers index -- either a missing index or a new one
    layer_index = get_layer_index(layer_indices)


    unassigned_layer_control = document.getElementById('layer_control_unassigned')
    assigned_layer_control = unassigned_layer_control.cloneNode(true)
    
    if (layer_index == 0){layer_type = 'background'}else{layer_type = 'color'}

    highlight_color = convert_rgb_to_string(highlight_colors[layer_index]['rgb_values'])
  
    assigned_layer_control.setAttribute('type', layer_type)
    assigned_layer_control.id = 'layer_control_' + String(layer_index)
    assigned_layer_control.className = 'layer_control container active'
    assigned_layer_control.querySelector('.listing_info.label.rectangle_swatch').textContent = layer_type
    assigned_layer_control.querySelector('.color_swatch.pixel_highlight').style.backgroundColor = highlight_color
   
    pixel_selector.querySelector('#pixel_selection_layer_panel')
    .appendChild(assigned_layer_control)

    create_layer_canvas(listing_container, layer_index)
 
    original_canvas = listing_container.querySelector('canvas.design').className = 'design'

    //click element to fire select layer fuction on the newly craeted control layer
    assigned_layer_control.click()

}

function create_layer_canvas(listing_container, layer_index){

    original_canvas = listing_container.querySelector('canvas.design')

    //remove active status from active canvas layer
    layers = Array.from(listing_container.querySelectorAll('.layer_canvas'))
    layers.forEach(layer => {layer.className = 'layer_canvas'})

    //create a layer
    const layer_container = listing_container.querySelector('.layer_container')

    const layer = original_canvas.cloneNode(true)
    layer.getContext('2d').drawImage(original_canvas,0,0)
    layer.id = 'color_layer_' + String(layer_index)
    layer.className = 'layer_canvas active'

    layer_container.appendChild(layer)
  

}


function select_tool(event) {

    const listing_container = event.target.closest('.listing.light.container');
    const active_layer = listing_container.querySelector('.layer_canvas.active');
    const selected_tool = event.target.closest('.button').id;

    //activate selected tool and turn on indicator

    active_indicator = listing_container
    .querySelector('.pixel_selection.tool.indicator.active')

    if (active_indicator) {active_indicator.className = 'pixel_selection tool indicator'}
   
    event.target.closest('.pixel_selection.button')
    .querySelector('.pixel_selection.tool.indicator')
    .className = 'pixel_selection tool indicator active'

    //activate tool
    if (selected_tool == 'button_brush'){

        active_layer.removeEventListener('click',flood_fill)
        active_layer.removeEventListener('click',full_fill)

        active_layer.addEventListener('click', brush_fill)

    }else if (selected_tool == 'button_full_fill') {
      
        active_layer.removeEventListener('click',brush_fill)
        active_layer.removeEventListener('click',flood_fill)

        active_layer.addEventListener('click',full_fill)

    } else if (selected_tool == 'button_flood_fill') {

        active_layer.removeEventListener('click',brush_fill)
        active_layer.removeEventListener('click',full_fill)

        active_layer.addEventListener('click',flood_fill)

    }

   
}

function handle_canvas_click(event){

    const listing_container = event.target.closest('.listing.light.container')
    const active_layer = listing_container.querySelector('.layer_canvas.active')
    const layer_index = parseInt(active_layer.id.split('_')[2])   
    const selected_tool = listing_container
    .querySelector('.pixel_selection.tool.indicator.active')
    .closest('.pixel_selection.button')
    .id

    console.log(selected_tool)

    //get highlight color
    const layer_control = listing_container.querySelector('#layer_control_' + String(layer_index))
    highlight_color_string = layer_control.querySelector('#highlight_color_indicator').style.backgroundColor
    highlight_color = convert_string_to_rgb(highlight_color_string)

    //get threshold 
    const threshold = listing_container.querySelector('#full_fill_threshold').value
       
    //activate tool
    if (selected_tool == 'button_brush'){
        active_layer.removeEventListener('click',full_fill)
        active_layer.addEventListener('click',brush_fill)

    }else if (selected_tool == 'button_full_fill') {
        active_layer.removeEventListener('click',brush_fill)
        active_layer.addEventListener('click',full_fill)
        
        
        // color_layer = full_fill(active_layer, layer_context, target_color, threshold, highlight_color)
    }

}

function select_layer(event) {

    const listing_container = event.target.closest('.listing.light.container')
    const control_layer = event.target.closest('.layer_control.container')
    const layer_index = parseInt(control_layer.id.split('_')[2])
    const layer = listing_container.querySelector('#color_layer_' + String(layer_index))

    //remove active from active layer if there is one
    active_layer = listing_container.querySelector('.layer_canvas.active') || null
    if (active_layer){active_layer.className = 'layer_canvas'}

    //remove active from active layer control if there is one
    active_layer_control = listing_container.querySelector('.layer_control.container.active') || null
    if (active_layer_control) {active_layer_control.className = 'layer_control container'}

    //set selected layer control as active
    listing_container.querySelector('#layer_control_' + String(layer_index)).className = 'layer_control container active'

    //set control layer as active
    layer.classname = 'layer_control container active'

    //set selected layer as active
    layer.className = 'layer_canvas active'

    layer.addEventListener('keydown', handleKeyPress(event))

    // activate_selection_tools(listing_container, layer, layer_index)

}

function change_threshold(event,operation){
 
    threshold_container = event.target.closest('.pixel_selection.threshold.container')
    current_threshold = parseInt(threshold_container.querySelector('.pixel_selection.field').value)
    
    if (operation == 'subtraction'){
        new_threshold = current_threshold - 25
    }else{
        new_threshold = current_threshold + 25
    }
    
    if ( new_threshold <= 0){
        new_threshold = 0
    }

    if ( new_threshold >= 255){
        new_threshold = 255
    }

    if (threshold_container.id == 'full_fill_threshold_container') {
        full_fill_threshold = new_threshold
    } else if(threshold_container.id == 'brush_threshold_container')  {
        brush_threshold = new_threshold
    } else {
        flood_fill_threshold = new_threshold
    }

    threshold_container.querySelector('.pixel_selection.field').value = new_threshold

    

}

function convert_rgb_to_string(rbg_array) {
    rgb_string = `rgb(${highlight_colors[layer_index]['rgb_values'][0]}, ${highlight_colors[layer_index]['rgb_values'][1]}, ${highlight_colors[layer_index]['rgb_values'][2]})`

    return rgb_string
}


function rgb_array_to_string(color_array) {

    rgb_string = `rgb(${color_array[0]}, ${color_array[1]}, ${color_array[2]})`
    return rgb_string
}

function get_layer_index(arr) {
    // If the array is empty, return 0
    if (arr.length === 0) {
        return 0;
    }

    // Sort the array to ensure it's in ascending order
    arr.sort((a, b) => a - b);

    // Check if 0 is missing (important for sequences starting at 0)
    if (arr[0] !== 0) {
        return 0;
    }

    // Iterate through the array to find the missing number
    for (let i = 0; i < arr.length - 1; i++) {
        if (arr[i + 1] !== arr[i] + 1) {
            return arr[i] + 1; // Return the missing number
        }
    }

    // If no missing number, return one greater than the max
    return arr[arr.length - 1] + 1;
}

function collect_color_layer_data(event){
    // this function fires off any time a color is selected on a canvas

    //get labeler id
    labeler_id = document.getElementById('labeler_id').getAttribute('labeler_id')

    ////////////////////////////
    //generate the file name for saving to aws
    const layer = event.target
    const listing_container = layer.closest('.listing.light.container')
    const layer_index = parseInt(layer.id.split('_')[2])
    const asset_id = listing_container.getAttribute('asset_id')

    const file_name = asset_id + '_' + layer_index + '.png'

    ////////////////////////////
    //compute mean color of selected pixels
    const original_canvas = listing_container.querySelector('canvas.design')

    highlight_color_string = listing_container
    .querySelector('.layer_control.container.active') 
    .querySelector('#highlight_color_indicator')
    .style.backgroundColor

    highlight_color = convert_string_to_rgb(highlight_color_string)

    mean_color = compute_mean_color(original_canvas,layer,highlight_color)

    layer_control_color_swatch = listing_container
    .querySelector('.layer_control.container.active')
    .querySelector('#rectangle_color_swatch')
    .style.backgroundColor = mean_color.color_string

    ////////////////////////////
    //gather rest of data

    layer_type = listing_container
    .querySelector('.layer_control.container.active') 
    .querySelector('.listing_info.label.rectangle_swatch')
    .textContent

    ///////////////////////////
    //compute color spread
    if (layer_type == 'color') {
        total_pixel_count = layer.width * layer.height
        color_pixel_count = count_matching_pixels(layer, highlight_color)      
        
        background_layer = listing_container.querySelector('#color_layer_0')  
        background_pixel_count = count_matching_pixels(background_layer, [255,0,0])

        content_pixels = total_pixel_count - background_pixel_count
        let percent_spread = ((color_pixel_count / content_pixels) * 100).toFixed(0);

        layer_control_color_swatch = listing_container
        .querySelector('.layer_control.container.active')
        .querySelector('#color_spread')
        .textContent = percent_spread
    }

    color_type = 'color'

    labels = {'asset_id':asset_id,
              'color_type':color_type,
              'layer_type':layer_type,
              'color_index':layer_index,
              'color_rgb_values':mean_color.color_string,
              'mask_rgb_values':highlight_color_string,
              'layer_type':layer_type,
              'color_map_link':file_name,
              'labeler_id':labeler_id
       }


    api_update_color_labels(labels)
    save_color_layer_to_aws(layer, file_name)

}


function count_matching_pixels(layer, highlight_color) {
    const layer_context = layer.getContext('2d');
    const layer_data = layer_context.getImageData(0, 0, layer.width, layer.height);
    const pixels = layer_data.data;
    let matching_pixel_count = 0;

    console.log(highlight_color[0])

    for (let i = 0; i < pixels.length; i += 4) {
        const r = pixels[i];
        const g = pixels[i + 1];
        const b = pixels[i + 2];

        // Check if the pixel matches the highlight color
        if (r === highlight_color[0] && g === highlight_color[1] && b === highlight_color[2]) {
            matching_pixel_count++;
        }
    }

    return matching_pixel_count;
}

function add_color_label(event){

    //get labeler id
    labeler_id = document.getElementById('labeler_id').getAttribute('labeler_id')


    //get the color type label based on the color_swatch class
    color_type = event.target.closest('.color_swatch')
    color_type.style.border = '4px solid #5a8383'
    color_type = color_type.getAttribute('class').split(' ')[1]
    

    //get asset id via listing container
    listing_container = event.target.closest('.listing.light.container')
    asset_id = listing_container.getAttribute('asset_id')

    labels = {'asset_id':asset_id,
              'color_type':color_type,
              'labeler_id':labeler_id,
            }

    api_update_color_labels(labels)
    remove_color_layer_from_aws(event)

    //remove color layers as any image not labelled color (outline, solid, invlaid) shouldn't have them
    layers = listing_container.querySelectorAll('.layer_canvas')
    Array.from(layers).forEach(layer =>{
        layer.remove()
    })

    //remove pixel selector and activate the original canvas so image persists
    listing_container.querySelector('#pixel_selection_palette').remove()
    listing_container.querySelector('canvas.design').className = 'design active'


}



function compute_mean_color(originalCanvas, maskCanvas, targetColor) {
    const originalContext = originalCanvas.getContext('2d');
    const maskContext = maskCanvas.getContext('2d');


    // Get image data from both canvases
    const originalImageData = originalContext.getImageData(0, 0, originalCanvas.width, originalCanvas.height);
    const maskImageData = maskContext.getImageData(0, 0, maskCanvas.width, maskCanvas.height);

    let totalR = 0, totalG = 0, totalB = 0, count = 0;
    const originalData = originalImageData.data;
    const maskData = maskImageData.data;
    const width = originalCanvas.width;

    for (let y = 0; y < originalCanvas.height; y++) {
        for (let x = 0; x < width; x++) {
            const index = (y * width + x) * 4;
            const maskR = maskData[index];
            const maskG = maskData[index + 1];
            const maskB = maskData[index + 2];

            // Check for exact color match and non-transparent pixel
            if (maskR === targetColor[0] && maskG === targetColor[1] && maskB === targetColor[2]) {
                const originalR = originalData[index];
                const originalG = originalData[index + 1];
                const originalB = originalData[index + 2];

                totalR += originalR;
                totalG += originalG;
                totalB += originalB;
                count++;
            }
        }
    }


    if (count === 0) return { r: 0, g: 0, b: 0 }; // Handle case with no matching pixels

    const meanColor = {
        r: Math.round(totalR / count),
        g: Math.round(totalG / count),
        b: Math.round(totalB / count)
    };

    return {
        color_array: meanColor,
        color_string: `rgb(${meanColor.r}, ${meanColor.g}, ${meanColor.b})`
    };
}
