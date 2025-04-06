document.addEventListener('DOMContentLoaded', function () {
    // Initialize canvases
    const canvases = document.querySelectorAll('canvas.design');
    canvases.forEach(canvas => {
        const asset_id = canvas.id.split('_')[1];
        const image_element = document.getElementById(`image_${asset_id}`);
        const canvas_context = canvas.getContext('2d');

        canvas_context.globalAlpha = 1

        image_element.onload = function () {
            const originalWidth = image_element.width;
            const originalHeight = image_element.height; // Use full height or crop if needed
        
            // Set the desired canvas height
            const targetWidth = 500;
        
            // Calculate the aspect ratio and corresponding width
            const aspectRatio = originalHeight / originalWidth ;
            const targetHeight = targetWidth * aspectRatio;
        
            // Set the canvas size
            canvas.width = targetWidth;
            canvas.height = targetHeight;
        
            // Draw the image scaled to new dimensions
            canvas_context.drawImage(
                image_element,
                0, 0, originalWidth, originalHeight,   // Source image
                0, 0, targetWidth, targetHeight        // Destination on canvas
            );
        
            // Optionally apply blur and redraw (though this might not visibly do anything)
            // canvas_context.filter = "blur(1px)";
            // canvas_context.drawImage(canvas, 0, 0);
        };
    });
});
const color_labels = [
    'red', 'orange', 'yellow', 'green', 'blue', 
    'purple', 'brown','tan','pink', 'gray', 'black', 'white'
];

const shadesCount = 9; // Number of shades per color
const defaultShade = '#dddddd';

const selected_colors = {};

// Initialize colorsWithShades with default shades
color_labels.forEach(color => {
    selected_colors[color] = Array(shadesCount).fill(defaultShade);
});


function select_color_label(element){

    color_palette = document.getElementById('color_palette')
    color_palette.style.display = 'none'

    selected_color = document.getElementsByClassName('reference_panel panel_4')[0].style.backgroundColor
    selected_label = element.querySelector('.listing_info.label').textContent

    //add selected color remove last one in the list (we only get the 8 most recently selected colors)
    colors =  selected_colors[selected_label]
    colors.unshift(selected_color)
    colors.pop()

    //get active swatch
    listing_container = element.closest('.listing.light.container')
    swatch  = Array.from(listing_container.getElementsByClassName('color_swatch filled active'))[0]
    swatch.setAttribute('color_name', selected_label)

    spread_container = document.getElementById('color_data')
    spread_container.style.display = 'block'

}



function select_spread_value(element){
    //spread value
    spread_value = element.getAttribute('spread_value')
    spread_value = parseFloat(spread_value.replace('%', '')) / 100

    //get listing container as it holds the asset id
    listing_container = element.closest('.listing.light.container')
    asset_id = listing_container.getAttribute('asset_id')

    //get active swatch to get color, color label and rgb 
    active_swatch = listing_container.getElementsByClassName('color_swatch filled active')[0]
    
    color_index = active_swatch.getAttribute('color_index')
    rgb_values = active_swatch.style.backgroundColor
    color_label = active_swatch.getAttribute('color_name')
    x_coord = active_swatch.getAttribute('x_coord')
    y_coord = active_swatch.getAttribute('y_coord')




    labels = {'asset_id': asset_id,
              'color_type':'color',
              'color_index': color_index,
              'color_label':color_label,
              'rgb_values':rgb_values,
              'spread_value':spread_value,
              'x_coord':x_coord,
              'y_coord':y_coord
             }



    //update manual table
    // api_update_color_labels(labels)   


    //deactivate active swatch
    active_swatch.className = 'color_swatch filled'

    //hide the sprea value menu box
    document.getElementById('color_data').style.display = 'none'

}