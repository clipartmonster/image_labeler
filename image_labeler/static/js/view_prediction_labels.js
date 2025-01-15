if (window.location.pathname === '/label_images/view_prediction_labels/')
    document.addEventListener('DOMContentLoaded', function(){
       
        flag_issue_buttons = document.querySelectorAll('.flag_issue')

        flag_issue_buttons.forEach(button =>{
            button.addEventListener('click', ()=> collect_label_issue(button))
        })

})


function collect_label_issue(button){

    image_box_container = button.closest('.image_box')
    console.log(image_box_container)

    button.style.opacity = .25

    data = {asset_id:image_box_container.getAttribute('asset_id'), 
            task_type:image_box_container.getAttribute('task_type'),
            rule_index:image_box_container.getAttribute('rule_index')
            }


    api_collect_label_issue(data)

}

    