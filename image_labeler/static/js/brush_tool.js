function brush_fill(event){

    listing_container = event.target.closest('.listing.light.container');

    highlight_color_string = listing_container.querySelector('.layer_control.container.active') 
    .querySelector('#highlight_color_indicator')
    .style.backgroundColor

    highlight_color = convert_string_to_rgb(highlight_color_string)

    brush_radius = listing_container
    .querySelector('.pixel_selection.tool.indicator.active')
    .closest('.pixel_selection.panel')
    .querySelector('.pixel_selection.field')
    .value

    brush_radius = parseInt(brush_radius/4)

    const rect = active_layer.getBoundingClientRect();
    const x = event.clientX - rect.left; // Calculate mouse x position
    const y = event.clientY - rect.top; // Calculate mouse y position

    // Allow continuous painting as the mouse moves
    function on_mouse_move(event) {
        const xMove = event.clientX - rect.left;
        const yMove = event.clientY - rect.top;
        paint(xMove, yMove,active_layer, brush_radius, highlight_color);
    }

    function on_mouse_down(){
        paint(x, y,active_layer, brush_radius, highlight_color);
        active_layer.addEventListener('mousemove', on_mouse_move)
        window.addEventListener('mouseup', on_mouse_up);
     }
 
    function on_mouse_up(){
        collect_color_layer_data(event)
        active_layer.removeEventListener('mousedown', on_mouse_down)
        active_layer.removeEventListener('mousemove', on_mouse_move)
        window.removeEventListener('mouseup', on_mouse_up)
    }

    active_layer.addEventListener('mousedown', on_mouse_down)
    

}

function paint(x, y, active_layer, brush_radius, highlight_color) {

    const active_layer_context = active_layer.getContext('2d')
    const image_data = active_layer_context.getImageData(0, 0, active_layer.width, active_layer.height);
    const pixel_data = image_data.data;

    for (let i = -brush_radius; i <= brush_radius; i++) {
        for (let j = -brush_radius; j <= brush_radius; j++) {
            const dx = x + i;
            const dy = y + j;

            // Ensure brush stays within canvas bounds
            if (dx >= 0 && dx < active_layer.width && dy >= 0 && dy < active_layer.height) {
                const index = (dy * active_layer.width + dx) * 4;

                // Use the circle equation for round brush
                if (i * i + j * j <= brush_radius * brush_radius) {
                    pixel_data[index] = highlight_color[0];
                    pixel_data[index + 1] = highlight_color[1];
                    pixel_data[index + 2] = highlight_color[2];
                }
            }
        }
    }

    active_layer_context.putImageData(image_data, 0, 0);
}

