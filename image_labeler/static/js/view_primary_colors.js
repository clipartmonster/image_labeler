document.addEventListener("DOMContentLoaded", function () {
    const min_slider_distance = document.getElementById("min_slider_color_distance");
    const max_slider_distance = document.getElementById("max_slider_color_distance");
    const min_slider_score = document.getElementById("min_slider_score");
    const max_slider_score = document.getElementById("max_slider_score");
    
    const min_val_distance = document.getElementById("min_distance");
    const max_val_distance = document.getElementById("max_distance");
    const min_val_score = document.getElementById("min_score");
    const max_val_score = document.getElementById("max_score");
  
    function updateValues() {
      let min_distance = parseInt(min_slider_distance.value);
      let max_distance = parseInt(max_slider_distance.value);

      let min_score = parseFloat(min_slider_score.value);
      let max_score = parseFloat(max_slider_score.value);


      let selected_color = document.getElementById('color_picker').value
      let color_swatches = document.getElementsByClassName('color_swatch')

      if (min_distance > max_distance) {
        [min_distance, max_distance] = [max_distance, min_distance];
      }

      Array.from(color_swatches).forEach(swatch => {

        const style = window.getComputedStyle(swatch);
        const bgColor = style.backgroundColor; // e.g., "rgb(123, 45, 67)"
        const rgbMatch = bgColor.match(/(\d+),\s*(\d+),\s*(\d+)/);


        if (rgbMatch) {
          const swatchColor = {
            r: parseInt(rgbMatch[1]),
            g: parseInt(rgbMatch[2]),
            b: parseInt(rgbMatch[3])
          };
  
          const distance = computeDistance(hexToRgb(selected_color), swatchColor);
          const score = swatch
          .parentNode
          .querySelector('.primary_color_data')
          .getAttribute('score')


          // Example: highlight if within range
          if (distance >= min_distance && distance <= max_distance &&
              score >= min_score && score <= max_score)
         {
            swatch.classList.remove('inactive')
            swatch.classList.add('active')
          } else {
            swatch.classList.remove('active')
            swatch.classList.add('inactive')
          }
        }
      });

      assets = document.querySelectorAll('.image_box')

      assets.forEach(asset => {

        active_swatches = asset.querySelectorAll('.color_swatch.active')

        if (active_swatches.length === 0) {
          asset.style.display = 'none'
        } else {
          asset.style.display = 'grid'
        }

      })

      min_val_distance.textContent = min_distance;
      max_val_distance.textContent = max_distance;
      min_val_score.textContent = min_score;
      max_val_score.textContent = max_score;
    }
  
    min_slider_distance.addEventListener("input", updateValues);
    max_slider_distance.addEventListener("input", updateValues);
    min_slider_score.addEventListener("input", updateValues);
    max_slider_score.addEventListener("input", updateValues);

  });



  function hexToRgb(hex) {
    const parsedHex = hex.replace(/^#/, '');
    const bigint = parseInt(parsedHex, 16);
    return {
      r: (bigint >> 16) & 255,
      g: (bigint >> 8) & 255,
      b: bigint & 255
    };
  }

  function computeDistance(c1, c2) {
    const rDiff = c1.r - c2.r;
    const gDiff = c1.g - c2.g;
    const bDiff = c1.b - c2.b;

    distance = Math.sqrt(rDiff * rDiff + gDiff * gDiff + bDiff * bDiff);
    distance = distance/255 * 100

    return distance;
  }