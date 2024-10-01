function convert_string_to_rgb(rgb_string) {
    const matches = rgb_string.match(/\d+/g);
    return matches.map(Number);
}


function full_fill(event) {

    listing_container = event.target.closest('.listing.light.container');

    highlight_color_string = listing_container.querySelector('.layer_control.container.active') 
    .querySelector('#highlight_color_indicator')
    .style.backgroundColor

    highlight_color = convert_string_to_rgb(highlight_color_string)

    threshold = listing_container
    .querySelector('.pixel_selection.tool.indicator.active')
    .closest('.pixel_selection.panel')
    .querySelector('.pixel_selection.field')
    .value
   
    const active_layer_context = active_layer.getContext('2d')
    const image_data = active_layer_context.getImageData(0, 0, active_layer.width, active_layer.height);
    const pixel_data = image_data.data;

    //get target color
    const rect = active_layer.getBoundingClientRect();
    const x = event.clientX - rect.left; // Calculate mouse x position
    const y = event.clientY - rect.top; // Calculate mouse y position

    const single_pixel_data = active_layer_context.getImageData(x, y, 1, 1).data;
    const target_color = [single_pixel_data[0], single_pixel_data[1], single_pixel_data[2]];
   
    for (let i = 0; i < pixel_data.length; i += 4) {
        const pixel_color = [pixel_data[i], pixel_data[i + 1], pixel_data[i + 2]];
        
        const color_distance = compute_color_distance(target_color, pixel_color);

        if (color_distance < threshold) {

            // replace the pixel color
            pixel_data[i    ] = highlight_color[0];
            pixel_data[i + 1] = highlight_color[1];
            pixel_data[i + 2] = highlight_color[2];
        }
    }

    active_layer_context.putImageData(image_data, 0, 0);
    collect_color_layer_data(event)
}




function compute_color_distance(target_color, pixel_color) {
    const rDiff = target_color[0] - pixel_color[0];
    const gDiff = target_color[1] - pixel_color[1];
    const bDiff = target_color[2] - pixel_color[2];
    return Math.sqrt(rDiff * rDiff + gDiff * gDiff + bDiff * bDiff);
}


