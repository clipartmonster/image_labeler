
// set global parameters
let API_ACCESS_KEY = '';

fetch('/get_config/')
    .then(response => response.json())
    .then(config => {
        API_ACCESS_KEY = config.API_ACCESS_KEY;
       
})

function api_remove_color_label(swatch){
  
    console.log('here')
    console.log(swatch)

    asset_id = swatch
    .closest('.listing.light.container')
    .getAttribute('asset_id')
  
    color_index = swatch.getAttribute('color_index')

    console.log(asset_id)
    console.log(color_index)

    api_url = 'https://backend-python-nupj.onrender.com/remove_color_label/'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': API_ACCESS_KEY,
    }

    data = {
        asset_id:asset_id,
        color_index:color_index       
        
    }

    return fetch(api_url, {
    method:'POST',
    headers : headers,
    mode:'cors',
    body: JSON.stringify(data)})
    .then(response => { return response.json() })
    .then(data => { return console.log(data) })


}

function api_update_color_labels(labels) {

    let color_type = labels.color_type ?? null
    let color_index = labels.color_index ?? null
    let color_broad_color_labels = labels.broad_color_labels ?? null
    let rgb_values = labels.rgb_values ?? null
    let spread_value = labels.spread_value ?? null
    let x_coord = labels.spread_value ?? null
    let y_coord = labels.spread_value ?? null

    api_url = 'https://backend-python-nupj.onrender.com/update_color_labels/'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': API_ACCESS_KEY,
    }

    data = {
        asset_id:labels.asset_id,
        color_labels:[{
            'asset_id' : labels.asset_id,
            'color_type':labels.color_type,
            'color_index': labels.color_index,
            'color_label':labels.color_label,
            'rgb_values':labels.rgb_values,
            'spread':labels.spread_value,
            'x_coord':labels.x_coord,
            'y_coord':labels.y_coord
        }]
    }

    return fetch(api_url, {
    method:'POST',
    headers : headers,
    mode:'cors',
    body: JSON.stringify(data)})
    .then(response => { return response.json() })
    .then(data => { return console.log(data) })

}