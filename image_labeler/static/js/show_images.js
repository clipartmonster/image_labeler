document.addEventListener('DOMContentLoaded', function () {
    // Initialize canvases
    const canvases = document.querySelectorAll('canvas.design');
    canvases.forEach(canvas => {
        const asset_id = canvas.id.split('_')[1];
        const image_element = document.getElementById(`image_${asset_id}`);
        const canvas_context = canvas.getContext('2d');

        image_element.onload = function () {
            canvas.width = image_element.width / 4;
            canvas.height = image_element.height / 4;
            canvas_context.drawImage(image_element, 0, 0, canvas.width, canvas.height);
            canvas_context.filter = "blur(1px)";
            canvas_context.drawImage(canvas, 0,0)
        };
    });
})

// document.addEventListener('DOMContentLoaded', function () {
//     // Initialize canvases
//     const canvases = document.querySelectorAll('canvas.design');
//     canvases.forEach(canvas => {
//         const asset_id = canvas.id.split('_')[1];
//         const image_element = document.getElementById(`image_${asset_id}`);
//         const canvas_context = canvas.getContext('2d');

//         image_element.onload = function () {
//             canvas.width = image_element.width / 4;
//             canvas.height = image_element.height / 4;
//             canvas_context.drawImage(image_element, 0, 0, canvas.width, canvas.height);
//             canvas_context.filter = "blur(1px)";
//             canvas_context.drawImage(canvas, 0,0)
//         };
//     });

//     // Initialize the color index
//     let colorIndex = 0;

//     const empty_swatches = Array.from(document.getElementsByClassName('color_swatch empty'));

//     empty_swatches.forEach(empty_swatch => {
//         addColorSelectionHandler(empty_swatch);
//         addRemovalHandler(empty_swatch);
//     });

//     function addColorSelectionHandler(swatch) {
//         const handleColorSelection = (event) => {
//             const listing_container = swatch.closest('.listing.light.container');
//             const canvas = Array.from(listing_container.querySelectorAll('[id^="canvas_"].design'))[0];
            
//             const handlePixelSelection = (event) => {
//                 selectPixelColor(event, canvas, swatch);
//             };

//             canvas.style.cursor = 'crosshair';
//             canvas.addEventListener('click', handlePixelSelection, { once: true });

//             // Remove the swatch click listener after selection
//             swatch.removeEventListener('click', handleColorSelection);
//         };

//         swatch.addEventListener('click', handleColorSelection);
//     }

//     function addRemovalHandler(swatch) {
//         const handleRemoval = (event) => {
//             if (swatch.classList.contains('filled')) {
//                 api_remove_color_label(swatch)
//                 swatch.remove();

//             }
//         };

//         swatch.addEventListener('click', handleRemoval);
//     }

//     function selectPixelColor(event, canvas, swatch) {
//         const canvas_context = canvas.getContext('2d');
//         const rect = canvas.getBoundingClientRect();
//         const x = event.clientX - rect.left;
//         const y = event.clientY - rect.top;

//         try {
//             const imageData = canvas_context.getImageData(x, y, 1, 1);
//             const pixel = imageData.data;
//             const rgb = `rgb(${pixel[0]},${pixel[1]},${pixel[2]})`;

//             swatch.style.backgroundColor = rgb;
//             swatch.querySelector('h1.field.add_color').textContent = '';
//             swatch.className = 'color_swatch filled active';

//             // Increment the color index
//             colorIndex++;

//             // Set the color_index attribute
//             swatch.setAttribute('color_index', colorIndex);
//             swatch.setAttribute('x_coord', x)
//             swatch.setAttribute('y_coord', y)

//             // Add new swatch
//             copy_empty_swatch(swatch);
//             canvas.style.cursor = 'auto';


//             // build the color palette to select color name. 
//             const reference_panels = 
//                 Array.from(document.getElementsByClassName('reference_panel selected panel_4'))

//             reference_panels.forEach(reference_panel =>{
//                 reference_panel.style.backgroundColor =  rgb
//             })

//             label_containers = 
//                 Array.from(document.getElementsByClassName('color_swatch palette container'))
            
//             label_containers.forEach(label_container =>{

//                 color = label_container.getAttribute('color')

//                 colors = selected_colors[color]

//                 count = 0
//                 colors.forEach(color =>{
//                     if ( count != 4) {
//                         panel = label_container.getElementsByClassName('reference_panel panel_' + count)[0]
//                         panel.style.backgroundColor = color
//                         }
//                     count++

//                 })
                
//             }) 

//             const palette_container = document.getElementById('color_palette')
//             const data_container = document.getElementById('color_data')
//             palette_container.style.display = 'grid'

//             const listing_container = swatch.closest('.listing.light.container').querySelector('.design')

//             listing_container.appendChild(palette_container)
//             listing_container.appendChild(data_container)

//         } catch (error) {
//             console.error('Unable to access pixel data:', error);
//         }
//     }

//     function copy_empty_swatch(original_swatch) {
//         // Clone the swatch and prepare the clone
//         const empty_swatch_copy = original_swatch.cloneNode(true);
//         empty_swatch_copy.className = 'color_swatch empty';
//         empty_swatch_copy.querySelector('.field.add_color').textContent = '+';
//         empty_swatch_copy.style.backgroundColor = '';

//         // Append the clone to the DOM
//         const add_color_container = original_swatch.closest('.add_color.container');
//         add_color_container.appendChild(empty_swatch_copy);

//         // Add click event listener to the new swatch
//         addColorSelectionHandler(empty_swatch_copy);
//         addRemovalHandler(empty_swatch_copy);
//     }
// });

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