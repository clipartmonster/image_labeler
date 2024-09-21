let highlight_colors = [
    { name: 'red', rgb_values: [255, 0, 0] },
    { name: 'blue', rgb_values: [0, 0, 255] },
    { name: 'green', rgb_values: [0, 255, 0] },
    { name: 'yellow', rgb_values: [255, 255, 0] },
    { name: 'purple', rgb_values: [128, 0, 128] }
];

var full_fill_threshold = 100
var flood_fill_threshold = 100

document.addEventListener('DOMContentLoaded', function () {
    // Initialize canvases
    
    const empty_swatches = Array.from(document.getElementsByClassName('color_swatch empty'));

    empty_swatches.forEach(swatch => {

        swatch.onclick = open_color_selector

    })


})




function remove_layer(event) {


    const listing_container = event.target.closest('.listing.light.container')
    const control_layer = event.target.closest('.layer_control.container')
    const layer_index = parseInt(control_layer.id.split('_')[2])
    const layer = listing_container.querySelector('#color_layer_' + String(layer_index))
    
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
    design_container.appendChild(pixel_selector_copy)
    
    add_layer(event)
   
}


function add_layer(event){
    
    const listing_container = event.target.closest('.listing.light.container')
    const pixel_selector = listing_container.querySelector('#pixel_selection_palette')
    
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
  

    activate_selection_tools(listing_container, layer, layer_index)

}

function activate_selection_tools(listing_container, layer, layer_index) {

    const flood_fill_button = listing_container.querySelector('.button.flood_fill')   
    const full_fill_button = listing_container.querySelector('.button.full_fill')
   
    flood_fill_button.removeEventListener('click',()=>{})
    full_fill_button.removeEventListener('click',()=>{})

    flood_fill_button.addEventListener('click', () => {
        layer.addEventListener('click', (event) => handle_flood_fill_click(event, listing_container, layer, layer_index));
    });

    full_fill_button.addEventListener('click', () => {
            layer.addEventListener('click', (event) => handle_full_fill_click(event, listing_container, layer, layer_index));
    });



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

    activate_selection_tools(listing_container, layer, layer_index)

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
    } else {
        flood_fill_threshold = new_threshold
    }

    threshold_container.querySelector('.pixel_selection.field').value = new_threshold

    

}

function convert_rgb_to_string(rbg_array) {
    rgb_string = `rgb(${highlight_colors[layer_index]['rgb_values'][0]}, 
                      ${highlight_colors[layer_index]['rgb_values'][1]}, 
                      ${highlight_colors[layer_index]['rgb_values'][2]})`

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

function collect_color_layer_data(event, labels){
    // this function fires off any time a color is selected on a canvas

    const layer = event.target
    const listing_container = layer.closest('.listing.light.container')
    const layer_index = parseInt(layer.id.split('_')[2])
    const asset_id = listing_container.getAttribute('asset_id')

    const file_name = asset_id + '_' + layer_index + '.png'

    labels = {'asset_id':asset_id,
              'color_type':labels.color_type,
              'layer_type':labels.layer_type,
              'color_index':layer_index,
              'color_rgb_values':labels.color_rgb_values,
              'mask_rgb_values':labels.mask_rgb_values,
              'layer_type':layer_type,
              'color_map_link':file_name,
       }


    api_update_color_labels(labels)
    save_color_layer_to_aws(layer, file_name)

}


function add_color_label(event){

    //get the color type label based on the color_swatch class
    color_type = event.target.closest('.color_swatch')
    color_type = color_type.getAttribute('class').split(' ')[1]

    //get asset id via listing container
    listing_container = event.target.closest('.listing.light.container')
    asset_id = listing_container.getAttribute('asset_id')

    labels = {'asset_id':asset_id,
              'color_type':color_type
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