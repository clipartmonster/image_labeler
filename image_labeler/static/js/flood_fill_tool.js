let is_filling = false;  // Global variable to track flood fill status
let start_time;  // To store the start time of the flood fill
function flood_fill(event) {
    // Check if a flood fill is already in progress
    if (is_filling) {
        console.log("Flood fill already in progress. Ignoring new click.");
        return;  // Ignore the new click
    }

    console.log("Starting flood fill");
    is_filling = true;  // Set the flag to indicate flood fill has started
    start_time = Date.now();  // Record the start time

    // Timeout mechanism: Stop after 1 second (1000ms)
    const flood_fill_timeout = setTimeout(() => {
        console.log("Flood fill exceeded time limit. Terminating.");
        is_filling = false;  // Reset the filling flag
    }, 1000);

    const listing_container = event.target.closest('.listing.light.container');

    // Get the highlight color
    highlight_color_string = listing_container
        .querySelector('.layer_control.container.active')
        .querySelector('#highlight_color_indicator')
        .style.backgroundColor;

    highlight_color = convert_string_to_rgb(highlight_color_string);
    const threshold = parseInt(listing_container.querySelector('#flood_fill_threshold').value);
    const kernel_size = 1;

    // Selected pixel coordinates
    console.log(active_layer)
    const rect = active_layer.getBoundingClientRect();
    const x = Math.floor(event.clientX - rect.left);
    const y = Math.floor(event.clientY - rect.top);
    const pixel_stack = [[x, y]];

    // Get layer data once and work with it
    const layer_context = active_layer.getContext('2d', { willReadFrequently: true });
    const imageData = layer_context.getImageData(0, 0, active_layer.width, active_layer.height);
    const pixel_data = imageData.data;

    // Selected pixel color
    const selected_color = get_pixel_color(pixel_data, x, y, active_layer.width);

    // Perform flood fill using a stack-based approach
    while (pixel_stack.length) {
        // Check if the time limit has been reached
        if (Date.now() - start_time > 1000) {
            console.log("Flood fill exceeded time limit during operation. Terminating.");
            break;  // Terminate if the time limit is exceeded
        }

        // Pop coordinates from the stack
        let [x_coord, y_coord] = pixel_stack.pop();

        // Ensure coordinates are within bounds
        if (x_coord < 0 || x_coord >= active_layer.width || y_coord < 0 || y_coord >= active_layer.height) {
            continue; // Skip out-of-bounds pixels
        }

        // Calculate the pixel position
        let pixel_position = (y_coord * active_layer.width + x_coord) * 4;
        
        // Move upwards to find the first non-matching pixel
        while (y_coord >= 0 && get_color_distance(pixel_data, x_coord, y_coord, active_layer.width, selected_color, kernel_size) < threshold) {
            pixel_position -= active_layer.width * 4; // Move up in pixel data
            y_coord--;
        }

        // Move back down one step
        y_coord++;
        pixel_position += active_layer.width * 4;

        let reachLeft = false;
        let reachRight = false;

        // Move downwards and fill pixels
        while (y_coord < active_layer.height && get_color_distance(pixel_data, x_coord, y_coord, active_layer.width, selected_color, kernel_size) < threshold) {
            // Fill the pixel
            fill_pixel(pixel_data, pixel_position, highlight_color);

            // Check neighboring pixels to the left
            if (x_coord > 0 && get_color_distance(pixel_data, x_coord - 1, y_coord, active_layer.width, selected_color, kernel_size) < threshold) {
                if (!reachLeft) {
                    pixel_stack.push([x_coord - 1, y_coord]); // Push left neighbor
                    reachLeft = true; // Mark as reached
                }
            } else {
                reachLeft = false; // Reset reachLeft when not matched
            }

            // Check neighboring pixels to the right
            if (x_coord < active_layer.width - 1 && get_color_distance(pixel_data, x_coord + 1, y_coord, active_layer.width, selected_color, kernel_size) < threshold) {
                if (!reachRight) {
                    pixel_stack.push([x_coord + 1, y_coord]); // Push right neighbor
                    reachRight = true; // Mark as reached
                }
            } else {
                reachRight = false; // Reset reachRight when not matched
            }

            // Move to the next row
            pixel_position += active_layer.width * 4; // Move down in pixel data
            y_coord++;
        }
    }

    // Apply all the filled pixels in one step
    layer_context.putImageData(imageData, 0, 0);
    collect_color_layer_data(event)

    // Reset the filling flag and clear the timeout when the operation is complete
    clearTimeout(flood_fill_timeout);  // Clear timeout if operation finishes within the time limit
    console.log("Flood fill completed");
    is_filling = false;
}
function get_pixel_color(pixel_data, x, y, width) {
    const pixel_position = (y * width + x) * 4;
    return [pixel_data[pixel_position], pixel_data[pixel_position + 1], pixel_data[pixel_position + 2]];
}

function get_color_distance(pixel_data, x, y, width, selected_color, kernel_size) {
    let r_sum = 0, g_sum = 0, b_sum = 0, count = 0;
    const half_kernel = Math.floor(kernel_size / 2);
    const pixel_position = (y * width + x) * 4;

    // Loop over the kernel size and calculate the average color
    for (let dy = -half_kernel; dy <= half_kernel; dy++) {
        for (let dx = -half_kernel; dx <= half_kernel; dx++) {
            const nx = x + dx;
            const ny = y + dy;
            if (nx >= 0 && ny >= 0 && nx < width && ny < pixel_data.length / (4 * width)) {
                const pos = (ny * width + nx) * 4;
                r_sum += pixel_data[pos];
                g_sum += pixel_data[pos + 1];
                b_sum += pixel_data[pos + 2];
                count++;
            }
        }
    }

    // Calculate mean color in the kernel area
    const r_mean = r_sum / count;
    const g_mean = g_sum / count;
    const b_mean = b_sum / count;

    // Calculate Euclidean distance between the mean color and the selected color
    return Math.sqrt(
        (selected_color[0] - r_mean) ** 2 +
        (selected_color[1] - g_mean) ** 2 +
        (selected_color[2] - b_mean) ** 2
    );
}

function fill_pixel(pixel_data, pixel_position, highlight_color) {
    // pixel_position = pixel_position -2
    // if (pixel_position % 4 != 0) {pixel_position = pixel_position -2}

    pixel_data[pixel_position] = highlight_color[0];
    pixel_data[pixel_position + 1] = highlight_color[1];
    pixel_data[pixel_position + 2] = highlight_color[2];
    pixel_data[pixel_position + 3] = 255;

}
