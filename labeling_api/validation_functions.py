from .models import *


def check_for_asset_in_simulated_color_table(asset_id):
    return simulated_assets_color_table.objects.all().filter(asset_id=asset_id).exists()
