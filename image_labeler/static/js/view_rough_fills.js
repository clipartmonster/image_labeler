document.addEventListener("DOMContentLoaded", function () {
  
  sliders = this.documentElement.querySelectorAll('.slider-input')
  console.log(sliders)


  sliders.forEach(slider => {
    slider.addEventListener('input',update_slider_value)
  })

  // roughness_slider = document.getElementById('slider roughness')
  // roughness_slider.addEventListener("input", update_slider_values);

  // roughness_slider = document.getElementById('slider roughness')
  // roughness_slider.addEventListener("input", update_slider_values);




  });

function update_slider_value(){

  value = this.value
  console.log(this)

  attribute = this.id.split(' ')[1]

  slider_container = this.closest('.slider-container')

  min_slider = slider_container.querySelector('[class*="min"]')
  max_slider = slider_container.querySelector('[class*="max"]')

  const image_boxes = Array.from(document.querySelectorAll('.image_box'));

  // Sort image_boxes by numeric attribute ascending
  image_boxes.sort((a, b) => {
    return parseFloat(a.getAttribute(attribute)) - parseFloat(b.getAttribute(attribute));
  });

  // Get the parent container of the image boxes (assumed same parent)
  const parent = image_boxes.length > 0 ? image_boxes[0].parentNode : null;

  if (parent) {
    // Append sorted boxes back to parent (this moves them in DOM order)
    image_boxes.forEach(box => parent.appendChild(box));
  }

  image_boxes.forEach(image_box =>{

    if (image_box.getAttribute(attribute) > min_slider.value & 
        image_box.getAttribute(attribute) < max_slider.value) {
      image_box.style.display = 'grid'
    } else {
      image_box.style.display = 'none'
    }

  })


}


function handleImageError(assetId) {
    const container = document.getElementById('container_' + assetId);
    if (container) {
        container.remove();
        console.warn('Removed container for missing image:', assetId);
    }
}
