
function handle_flood_fill_click(event, listing_container, layer, layer_index){

    //get highlight color
    const layer_control = listing_container.querySelector('#layer_control_' + String(layer_index))
    highlight_color_string = layer_control.querySelector('#highlight_color_indicator').style.backgroundColor
    highlight_color = convert_string_to_rgb(highlight_color_string)

    //get threshold 
    const threshold = listing_container.querySelector('#flood_fill_threshold').value
       
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
    const layer_data = layer_context.getImageData(0, 0, original_canvas.width, original_canvas.height, );
    const pixel_data = layer_context.getImageData(x, y, 1, 1).data;
    const target_color = [pixel_data[0], pixel_data[1], pixel_data[2]];

    //change color of layer control 
    const color_swatch = listing_container.querySelector('#rectangle_color_swatch')
    color_swatch.style.backgroundColor = canvas_color

    // const result = flood_fill(layer, [x,y], target_color, threshold, highlight_color)
    color_layer = flood_fill(layer, layer_data, x, y, target_color[0],target_color[1], target_color[2], highlight_color[0], highlight_color[1], highlight_color[2],threshold)

    mean_color = compute_mean_color(original_canvas, color_layer, highlight_color)
    layer_type = layer_control.querySelector('.listing_info.label.rectangle_swatch').textContent

    labels = {'color_type':'color',
              'color_rgb_values':mean_color.color_string,
              'mask_rgb_values':highlight_color_string,
              'layer_type':layer_type
       } 

    collect_color_layer_data(event,labels)
    
}


// Flood fill algorithm with color distance threshold, kernel size, and time limit
function flood_fill(canvas, colorLayer, startX, startY, startR, startG, startB, fillColorR, fillColorG, fillColorB, threshold, kernelSize = 1) {
    const pixelStack = [[startX, startY]];
    const context = canvas.getContext('2d', { willReadFrequently: true });
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;
    const drawingBoundTop = 0;
    


    const startTime = performance.now();  // Get the start time
    const maxDuration = 1000; // Maximum duration of 1 second (1000 ms)

    while (pixelStack.length) {
        // Check if the flood fill has exceeded the time limit
        if (performance.now() - startTime > maxDuration) {
            console.log("Flood fill exceeded time limit.");
            break;
        }

        let [x, y] = pixelStack.pop();
        let pixelPos = (y * canvasWidth + x) * 4;

        // Move upwards until hitting a boundary or different color
        while (y >= drawingBoundTop && kernelColorDistance(colorLayer, x, y, startR, startG, startB, kernelSize, canvasWidth, canvasHeight) < threshold) {
            pixelPos -= canvasWidth * 4;
            y--;
        }

        pixelPos += canvasWidth * 4;
        y++;

        let reachLeft = false;
        let reachRight = false;

        // Move downwards and fill pixels
        while (y < canvasHeight && kernelColorDistance(colorLayer, x, y, startR, startG, startB, kernelSize, canvasWidth, canvasHeight) < threshold) {
            colorPixel(colorLayer, pixelPos, fillColorR, fillColorG, fillColorB);

            if (x > 0) {
                if (kernelColorDistance(colorLayer, x - 1, y, startR, startG, startB, kernelSize, canvasWidth, canvasHeight) < threshold) {
                    if (!reachLeft) {
                        pixelStack.push([x - 1, y]);
                        reachLeft = true;
                    }
                } else {
                    reachLeft = false;
                }
            }

            if (x < canvasWidth - 1) {
                if (kernelColorDistance(colorLayer, x + 1, y, startR, startG, startB, kernelSize, canvasWidth, canvasHeight) < threshold) {
                    if (!reachRight) {
                        pixelStack.push([x + 1, y]);
                        reachRight = true;
                    }
                } else {
                    reachRight = false;
                }
            }

            pixelPos += canvasWidth * 4;
            y++;
        }
    }

    context.putImageData(colorLayer, 0, 0);
    return canvas
}

// Function to calculate the average color distance over a kernel
function kernelColorDistance(colorLayer, x, y, r, g, b, kernelSize, canvasWidth, canvasHeight) {
    let totalR = 0, totalG = 0, totalB = 0, count = 0;

    const halfKernel = Math.floor(kernelSize / 2);

    for (let dy = -halfKernel; dy <= halfKernel; dy++) {
        for (let dx = -halfKernel; dx <= halfKernel; dx++) {
            const newX = x + dx;
            const newY = y + dy;

            // Ensure the pixel is within the canvas boundaries
            if (newX >= 0 && newX < canvasWidth && newY >= 0 && newY < canvasHeight) {
                const pixelPos = (newY * canvasWidth + newX) * 4;
                totalR += colorLayer.data[pixelPos];
                totalG += colorLayer.data[pixelPos + 1];
                totalB += colorLayer.data[pixelPos + 2];
                count++;
            }
        }
    }

    // Calculate average color in the kernel
    const avgR = totalR / count;
    const avgG = totalG / count;
    const avgB = totalB / count;

    // Return the color distance between the average color and the target color
    return Math.sqrt((r - avgR) ** 2 + (g - avgG) ** 2 + (b - avgB) ** 2);
}

// Function to color a pixel with the fill color
function colorPixel(colorLayer, pixelPos, fillColorR, fillColorG, fillColorB) {
    colorLayer.data[pixelPos] = fillColorR;
    colorLayer.data[pixelPos + 1] = fillColorG;
    colorLayer.data[pixelPos + 2] = fillColorB;
    colorLayer.data[pixelPos + 3] = 255; // Set alpha to fully opaque
}

// Function to calculate the average color distance over a kernel
function kernelColorDistance(colorLayer, x, y, r, g, b, kernelSize, canvasWidth, canvasHeight) {
    let totalR = 0, totalG = 0, totalB = 0, count = 0;

    const halfKernel = Math.floor(kernelSize / 2);

    for (let dy = -halfKernel; dy <= halfKernel; dy++) {
        for (let dx = -halfKernel; dx <= halfKernel; dx++) {
            const newX = x + dx;
            const newY = y + dy;

            // Ensure the pixel is within the canvas boundaries
            if (newX >= 0 && newX < canvasWidth && newY >= 0 && newY < canvasHeight) {
                const pixelPos = (newY * canvasWidth + newX) * 4;
                totalR += colorLayer.data[pixelPos];
                totalG += colorLayer.data[pixelPos + 1];
                totalB += colorLayer.data[pixelPos + 2];
                count++;
            }
        }
    }

    // Calculate average color in the kernel
    const avgR = totalR / count;
    const avgG = totalG / count;
    const avgB = totalB / count;

    // Return the color distance between the average color and the target color
    return Math.sqrt((r - avgR) ** 2 + (g - avgG) ** 2 + (b - avgB) ** 2);
}

// Function to color a pixel with the fill color
function colorPixel(colorLayer, pixelPos, fillColorR, fillColorG, fillColorB) {
    colorLayer.data[pixelPos] = fillColorR;
    colorLayer.data[pixelPos + 1] = fillColorG;
    colorLayer.data[pixelPos + 2] = fillColorB;
    colorLayer.data[pixelPos + 3] = 255; // Set alpha to fully opaque
}




