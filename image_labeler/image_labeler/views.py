import os
from django.http import JsonResponse

#function creates an endpoint for js scripts to get the api_access_key kept on a private enviroment file
def get_config(request):

    config = {
        'API_ACCESS_KEY': os.getenv('API_ACCESS_KEY'),
        'AWS_ACCESS_KEY_ID':os.getenv('AWS_ACCESS_KEY_ID'),
        'AWS_SECRET_ACCESS_KEY':os.getenv('AWS_SECRET_ACCESS_KEY')
    }

    # print('----v-v-v-----')
    # print(config)

    return JsonResponse(config)