
// set global parameters
let API_ACCESS_KEY = '';

fetch('/get_config/')
    .then(response => response.json())
    .then(config => {
        API_ACCESS_KEY = config.API_ACCESS_KEY;
        AWS_ACCESS_KEY_ID = config.AWS_ACCESS_KEY_ID;
        AWS_SECRET_ACCESS_KEY = config.AWS_SECRET_ACCESS_KEY
       
})


function api_get_labelling_rules(art_type, label){

    api_url = 'https://backend-python-nupj.onrender.com/get_labelling_rules/'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': API_ACCESS_KEY,
    }

    data = {
        task_type:art_type,
        label:label              
    }

    return fetch(api_url, {
    method:'POST',
    headers : headers,
    mode:'cors',
    body: JSON.stringify(data)})
    .then(response => { return response.json() })
    .then(data => { return console.log(data) })

}


function api_remove_color_label(asset_id, layer_index){

    api_url = 'https://backend-python-nupj.onrender.com/remove_color_label/'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': API_ACCESS_KEY,
    }

    data = {
        asset_id:asset_id,
        color_index:layer_index               
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

    api_url = 'https://backend-python-nupj.onrender.com/update_color_labels/'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': API_ACCESS_KEY,
    }

    data = {
        asset_id:labels.asset_id,
        color_labels:[{
            'asset_id':labels.asset_id,
            'color_type':labels.color_type,
            'layer_type':labels.layer_type,
            'color_index':labels.color_index,
            'color_rgb_values':labels.color_rgb_values,
            'mask_rgb_values':labels.mask_rgb_values,
            'layer_type':labels.layer_type,
            'color_map_link':labels.color_map_link,
            'labeler_id':labels.labeler_id,
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
    


function save_color_layer_to_aws(layer, file_name) {
    // Convert canvas to a Blob
    layer.toBlob(function(blob) {
        // AWS S3 configuration
        AWS.config.update({
            accessKeyId: AWS_ACCESS_KEY_ID,
            secretAccessKey: AWS_SECRET_ACCESS_KEY,
            region: 'us-east-2'
        });

        const s3 = new AWS.S3({maxRetries: 0,});

        const params = {
            Bucket: 'label-color-maps',
            Key: file_name, // Your desired file path in the bucket
            Body: blob,
            ContentType: 'image/png'              
        };

        // Upload the Blob to S3
        s3.putObject(params, (err, data) => {
            if (err) {
                console.error('Error uploading image:', err);
            } else {
                console.log('Image uploaded successfully:', data);
            }
        });
    }, 'image/png');

    console.log('here')
    // download_image_from_s3(file_name)

}


function remove_color_layer_from_aws(event) {

    //becasue remove color layer can either mean remove one signle layer or all
    //layers we have to check for which one to do

    const listing_container = event.target.closest('.listing.light.container')
    const control_layer = event.target.closest('.layer_control.container') || null


    //if control layer is not null we have a request to delete one single layer
    if (control_layer) {
        control_layers = [control_layer]
    } else {
        control_layers = listing_container.querySelectorAll('.layer_control.container')
    }

    Array.from(control_layers).forEach(control_layer => {

        const layer_index = parseInt(control_layer.id.split('_')[2])
        const file_name =  asset_id + '_' + String(layer_index) + '.png' 

         // AWS S3 configuration
        AWS.config.update({
            accessKeyId: AWS_ACCESS_KEY_ID,
            secretAccessKey: AWS_SECRET_ACCESS_KEY
        });

        const s3 = new AWS.S3({region: 'us-east-2'});

        let params = {
            Bucket: 'label-color-maps',
            Key: file_name // The file to delete from the bucket
        };

        // Create the request object
        const request = s3.deleteObject(params);
        
        // Add a listener to the request to log the HTTP request details
        request.on('build', function() {
        console.log("Request:", request.httpRequest);
        });

        // Send the request and handle the promise
        request.promise()
        .then((data) => {
            console.log("Delete Object Success", data);
        })
        .catch((err) => {
            console.log("Error", err);
        });


    })

  

}


function download_image_from_s3(file_name) {
    // AWS S3 configuration
    AWS.config.update({
        accessKeyId: AWS_ACCESS_KEY_ID,
        secretAccessKey: AWS_SECRET_ACCESS_KEY,
        region: 'us-east-2'
    });

    const s3 = new AWS.S3({maxRetries: 0,});

    const params = {
        Bucket: 'label-color-maps',
        Key: file_name // The file path in the bucket
    };

    // Retrieve the object from S3
    s3.getObject(params, function(err, data) {
        if (err) {
            console.error('Error downloading image:', err);
        } else {
            // Convert binary data to Blob
            const blob = new Blob([data.Body], { type: 'image/png' });

            // Create a URL for the Blob and display the image
            const url = URL.createObjectURL(blob);
            
            // Example: Set the image src to the blob URL in an img element
            const img = document.createElement('img');
            img.src = url;
            document.body.appendChild(img); // Add the image to the page
        }
    });
}




function api_collect_label(data) {

    api_url = 'https://backend-python-nupj.onrender.com/collect_label/'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': API_ACCESS_KEY,
    }

    return fetch(api_url, {
    method:'POST',
    headers : headers,
    mode:'cors',
    body: JSON.stringify(data)})
    .then(response => { return response.json() })
    .then(data => { return console.log(data) })

}1


function api_collect_prompt(data) {

    api_url = 'https://backend-python-nupj.onrender.com/collect_prompt/'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': API_ACCESS_KEY,
    }

    return fetch(api_url, {
    method:'POST',
    headers : headers,
    mode:'cors',
    body: JSON.stringify(data)})
    .then(response => { return response.json() })
    .then(data => { return console.log(data) })

}


function api_remove_prompt_responses(asset_id, labeler_id) {

    api_url = 'https://backend-python-nupj.onrender.com/remove_prompt_responses/'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': API_ACCESS_KEY,
    }

    data = {
        asset_id:asset_id,
        labeler_id:labeler_id
    }

    return fetch(api_url, {
    method:'POST',
    headers : headers,
    mode:'cors',
    body: JSON.stringify(data)})
    .then(response => { return response.json() })
    .then(data => { return console.log(data) })

}



function api_collect_validation_response(assignment_id, response, feedback) {

    api_url = 'https://backend-python-nupj.onrender.com/collect_validation_response/'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': API_ACCESS_KEY,
    }

    data = {
        assignment_id:assignment_id,
        response:response,
        feedback:feedback
    }

    return fetch(api_url, {
    method:'POST',
    headers : headers,
    mode:'cors',
    body: JSON.stringify(data)})
    .then(response => { return response.json() })
    .then(data => { return console.log(data) })

}
