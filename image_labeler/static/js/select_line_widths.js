if (window.location.pathname === '/label_images/select_line_widths/') {
    document.addEventListener('DOMContentLoaded', function () {

    console.log('here')

    add_line_width_buttons = document.querySelectorAll('.color_swatch.line_width.empty')

    add_line_width_buttons.forEach(button => {
        button.addEventListener('click', function(event) {
            activate_line_width_palette(button) 
        })
    })

    })


    
}

function activate_line_width_palette(event) {
    console.log("here")
    console.log(event)

    palette_template =  document.querySelector('#line_width_palette_template')

    palette = palette_template.cloneNode(true)
    palette.id = ''

    asset_container = event.closest('.listing.light.container')

    //add palette to asset container
    asset_container
    .querySelector('.listing_info.header')
    .appendChild(palette)

    canvas =  asset_container
    .querySelector('canvas')

    draw3x3GridOnCanvas(canvas);


}

function draw3x3GridOnCanvas(canvas) {
    const ctx = canvas.getContext('2d');
    const rows = 3;
    const cols = 3;
    const squareWidth = canvas.width / cols;
    const squareHeight = canvas.height / rows;
    let circleIndex = 0;
    let currentRadius = 10;

    const clickedCircles = []; // store all circle positions
    const greenSquares = new Set(); // store row,col strings like "1,2" that were clicked

    const cells = Array.from(document.querySelectorAll('.sample.panel'));

    const originalImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

    function drawCanvas(hoverX = null, hoverY = null) {
        ctx.putImageData(originalImageData, 0, 0);
        ctx.lineWidth = 2;

        for (let row = 0; row < rows; row++) {
            for (let col = 0; col < cols; col++) {
                const x = col * squareWidth;
                const y = row * squareHeight;
                const key = `${row},${col}`;

                if (greenSquares.has(key)) {
                    ctx.fillStyle = 'rgba(0, 255, 0, 0.3)';
                    ctx.fillRect(x, y, squareWidth, squareHeight);
                }

                ctx.strokeStyle = 'red';
                ctx.strokeRect(x, y, squareWidth, squareHeight);
            }
        }

        if (hoverX !== null && hoverY !== null) {
            drawCircle(hoverX, hoverY, 'rgba(0, 25, 255, 0.3)', '#FFF', currentRadius); // 👈 updated
        }

        for (const { x, y, radius } of clickedCircles) {
            drawCircle(x, y, 'rgba(0, 25, 255, 0.5)', '#FFF', radius); // 👈 updated
        }
    }

    // 🔧 Modified to accept radius
    function drawCircle(x, y, fillColor, strokeColor, radius) {
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, 2 * Math.PI);
        ctx.fillStyle = fillColor;
        ctx.fill();
        ctx.strokeStyle = strokeColor;
        ctx.stroke();
    }

    canvas.addEventListener('mousemove', (event) => {
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        drawCanvas(x, y);
    });

    canvas.addEventListener('mouseleave', () => {
        drawCanvas();
    });

    canvas.addEventListener('click', (event) => {
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        clickedCircles.push({ x, y, radius: currentRadius, index: circleIndex++ });

        const col = Math.floor(x / squareWidth);
        const row = Math.floor(y / squareHeight);
        const key = `${row},${col}`;
        greenSquares.add(key);

        const index = row * cols + col;
        if (cells[index]) {
            cells[index].style.backgroundColor = 'rgba(0, 255, 0, 0.3)';
        }

        drawCanvas(x, y);

        collect_line_width_sample(canvas, circleIndex, x, y, currentRadius, canvas.width, canvas.height);
    });

    canvas.addEventListener('contextmenu', (event) => {
        event.preventDefault();

        if (clickedCircles.length === 0) return;

        remove_line_width_sample(canvas, circleIndex);
        const removedCircle = clickedCircles.pop();
        circleIndex--;

        const col = Math.floor(removedCircle.x / squareWidth);
        const row = Math.floor(removedCircle.y / squareHeight);
        const key = `${row},${col}`;

        const stillHasCircle = clickedCircles.some(circle => {
            return Math.floor(circle.x / squareWidth) === col &&
                   Math.floor(circle.y / squareHeight) === row;
        });

        if (!stillHasCircle) {
            greenSquares.delete(key);
            const index = row * cols + col;
            if (cells[index]) {
                cells[index].style.backgroundColor = '';
            }
        }

        drawCanvas();
    });

    // 🧭 NEW: Mouse wheel controls radius
    canvas.addEventListener('wheel', (event) => {
        event.preventDefault(); // prevent page scroll
        const delta = Math.sign(event.deltaY);
        currentRadius -= delta; // scroll up to increase
        currentRadius = Math.max(2, Math.min(currentRadius, 100)); // clamp between 2 and 100
        drawCanvas(); // update preview with new radius
    });

    drawCanvas();
}



function collect_line_width_sample(canvas, sample_index, x_coord, y_coord, radius, image_width, image_height){

    data = {
        asset_id:canvas.getAttribute('asset_id'), 
        sample_index:sample_index,
        x_coord:x_coord,
        y_coord:y_coord,
        radius:radius,
        image_width:image_width,
        image_height:image_height,
        labeler_id:document.getElementById('labeler_id').getAttribute('labeler_id')
        }

    console.log(data)

    api_collect_line_width_sample(data)

}

function remove_line_width_sample(canvas, sample_index){

    data = {
        asset_id:canvas.getAttribute('asset_id'), 
        sample_index:sample_index}

    console.log(data)

    api_remove_line_width_sample(data)

}
