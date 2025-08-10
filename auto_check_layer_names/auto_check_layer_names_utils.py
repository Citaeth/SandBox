import re

import sg

env = sg.from_env()
project_record = env.project.as_shotgun_record()


def get_bg_shots(asset_name):
    """
    get the bg shots linked to the given asset in shotgrid.
    :param str asset_name:
    """
    filters = [
        ['project', 'is', project_record],
        ['assets.Asset.code', "is", asset_name],
    ]

    fields = ['code']
    bg_shots = env.sg.find("Shot", filters=filters, fields=fields)
    return bg_shots


def get_bg_layers_version(shot, asset_name):
    """
    get for the given shot the list of RoleDescription that contain the given asset.
    Read the json related to this roleDescription to get the informations of the layers.
    We want to get all the versions of the layers for layout and paint task, and the version used
    in the latest layout scene.
    :param str shot:
    :param str asset_name:
    :rtype list, list: layers_versions, last_layout_version
    """
    filters = [
        ['project', 'is', project_record],
        ['published_file_type.PublishedFileType.code', 'is', 'Image Layer'],
        ['entity.Asset.sg_asset_type', 'is', 'Set'],
        ['entity.Asset.code', "is", asset_name],
        # ['entity.CustomEntity29.custom_entity21_sg_roles_custom_entity21s.CustomEntity21.sg_context.Shot.code', 'in', shot],
    ]

    fields = ['version']
    published_files = env.sg.find("PublishedFile", filters=filters, fields=fields)
    layers_versions = set()
    last_layout_version = []

    for each_file in published_files:
        if not each_file['version']:
            continue
        json_path = each_file['version']['name']
        match = re.search(r'_v(\d{3})\.png$', json_path)
        if '_lo_' in json_path:
            if not last_layout_version or int(match.group(1)) > last_layout_version[1]:
                last_layout_version = [json_path, int(match.group(1))]
            layers_versions.add('lo - v{}'.format(match.group(1)))
        elif '_pnt_' in json_path:
            layers_versions.add('pnt - v{}'.format(match.group(1)))
    layers_versions_ordered = sorted(layers_versions, key=layers_versions_in_order)
    return layers_versions_ordered, last_layout_version


def layers_versions_in_order(layer_name):
    """
    function to order the layer list, filtering first the prefix, lo or pnt, and the version for each
    of them.
    """
    match = re.match(r"(\w+)\s*-\s*v(\d+)", layer_name, re.IGNORECASE)
    if match:
        prefix = match.group(1).lower()
        version = int(match.group(2))
        order_prefix = 0 if prefix == "lo" else 1
        return (order_prefix, version)
    return (2, 0)


