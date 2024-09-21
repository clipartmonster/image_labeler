function convert_string_to_rgb(rgb_string) {
    const matches = rgb_string.match(/\d+/g);
    return matches.map(Number);
}


function handle_full_fill_click(event, listing_container, layer, layer_index){

    //get highlight color
    const layer_control = listing_container.querySelector('#layer_control_' + String(layer_index))
    highlight_color_string = layer_control.querySelector('#highlight_color_indicator').style.backgroundColor
    highlight_color = convert_string_to_rgb(highlight_color_string)

    //get threshold 
    const threshold = listing_container.querySelector('#full_fill_threshold').value
       
    //Get coordinates of canvas click
    const rect = layer.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top    

    //get original canvas data
    const original_canvas = listing_container.querySelector('canvas.design')
    const canvas_context = original_canvas.getContext('2d')
    const canvas_pixel_data = canvas_context.getImageData(x,y,1,1).data
    const canvas_color = [canvas_pixel_data[0], canvas_pixel_data[1], canvas_pixel_data[2]]

    //get layer data
    const layer_context = layer.getContext('2d',{ willReadFrequently: true }  );
    const pixel_data = layer_context.getImageData(x, y, 1, 1).data;
    const target_color = [pixel_data[0], pixel_data[1], pixel_data[2]];

    const color_layer = full_fill(layer, layer_context, target_color, threshold, highlight_color)

    //change color of layer control 
    const color_swatch = listing_container.querySelector('#rectangle_color_swatch')
    color_swatch.style.backgroundColor = canvas_color
    
    mean_color = compute_mean_color(original_canvas, color_layer, highlight_color)
    layer_type = layer_control.querySelector('.listing_info.label.rectangle_swatch').textContent
    

    labels = {'color_type':'color',
              'color_rgb_values':mean_color.color_string,
              'mask_rgb_values':highlight_color_string,
              'layer_type':layer_type
             }

    collect_color_layer_data(event, labels)
    
}


function full_fill(layer, context, target_color, threshold,  highlight_color) {
    
    const image_data = context.getImageData(0, 0, layer.width, layer.height);
    const pixel_data = image_data.data;
    

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

    context.putImageData(image_data, 0, 0);
    return layer

}


function compute_color_distance(target_color, pixel_color) {
    const rDiff = target_color[0] - pixel_color[0];
    const gDiff = target_color[1] - pixel_color[1];
    const bDiff = target_color[2] - pixel_color[2];
    return Math.sqrt(rDiff * rDiff + gDiff * gDiff + bDiff * bDiff);
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

