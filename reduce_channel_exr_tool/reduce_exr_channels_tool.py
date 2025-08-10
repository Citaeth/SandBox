import sys
import os
import re
import shutil
import stat
import concurrent.futures
import numpy as np
import OpenImageIO as oiio

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import sg
env = sg.from_env()
project_record = env.project.as_shotgun_record()

from tk_multi_publish2_nodes import MultiPublish2


def create_harmony_version_folders(version):
    """
    Get the user X:\\ personal location, to create a folder that will contain the new harmony folder.
    copy to this location the previous published harmony folder, the previous clip and create a Layers folder.

    :param sg_version version:
    :return:
    :rtype: Path local_harmony_folder
    :rtype: str layers_folder
    :rtype: str source_layers_folder
    :rtype: str version
    """
    current_username = os.getenv("USERNAME", None)
    logger.info(f"user found: {current_username}")

    users_personal_space = f"X:\\avoa\\10. Users\\{current_username.replace('.', '_')}"
    if not os.path.isdir(users_personal_space):
        logger.warning('No User folder found in X:\ Users location for the current user.')
        return

    destination_path = f'{users_personal_space}\\reduce_channel_tool_folders'
    os.makedirs(destination_path, exist_ok=True)

    source_clip_version = version['sg_path_to_movie']

    target = 'taLayerExport'
    #Regex to find the /taLayerExport folder in the path, and the version number.
    match = re.match(fr"^(.*?{re.escape(target)})\\.*?\\(v\d+)\b", source_clip_version)
    if not match:
        logger.warning("unable to found the taLayerExport main folder for this version")
        return
    talayer_folder = match.group(1)
    version = match.group(2)

    source_layers_folder = f"{talayer_folder}\layers"
    source_harmony_folder_version = f"{talayer_folder}\source\{version}"
    if not os.path.isdir(source_harmony_folder_version):
        logger.warning("No source version to generate the needed harmony project")
        return
    source_harmony_project_name = os.listdir(source_harmony_folder_version)[0]

    shutil.copytree(source_harmony_folder_version, destination_path, dirs_exist_ok=True)

    local_harmony_folder = os.path.join(destination_path, source_harmony_project_name)

    #Create layers and clips folders
    layers_folder = f"{local_harmony_folder}\\layers"
    os.makedirs(layers_folder, exist_ok=True)
    clips_folder = f"{local_harmony_folder}\\clips"
    os.makedirs(clips_folder, exist_ok=True)

    #Move the .mov last clip into the clips folder
    shutil.copy2(source_clip_version, clips_folder) #copyfile return a permission error, so used copy2 here

    remove_readonly_recursive(local_harmony_folder)

    return local_harmony_folder, layers_folder, source_layers_folder, version

def get_latest_version_path(path):
    """
    Get the last version folder path of the current layer folder.
    :param str path:
    :return:
    :rtype: Path
    """
    versions = [d for d in os.listdir(path) if re.match(r'v\d+', d)]
    versions.sort(key=lambda v: int(v[1:]))
    return os.path.join(path, versions[-1]) if versions else None


def remove_readonly_recursive(root_path):
    """
    Browse all the folder and files to remove the `readonly` tag, that creates issues during the publishing.
    :param str root_path:
    """
    for dirpath, dirnames, filenames in os.walk(root_path):
        for dirname in dirnames:
            dir_full_path = os.path.join(dirpath, dirname)
            try:
                os.chmod(dir_full_path, stat.S_IWRITE)
            except Exception as e:
                logger.warning(f"Error removing readonly on: {dir_full_path}: {e}")

        for filename in filenames:
            file_full_path = os.path.join(dirpath, filename)
            try:
                os.chmod(file_full_path, stat.S_IWRITE)
            except Exception as e:
                logger.warning(f"Error removing readonly on: {file_full_path}: {e}")


def create_new_version_path(latest_version_path, new_folders_location):
    """
    create the version for the current layer folder to save the edited EXRs in the new layers location.
    :param str latest_version_path:
    :param str new_folders_location:
    return:
    :rtype: str new_path, str layer_version
    """
    layer_name = latest_version_path.split('\\')[-2]
    layer_version = latest_version_path.split('\\')[-1]
    new_path = os.path.join(new_folders_location, layer_name)
    os.makedirs(new_path, exist_ok=True)
    return new_path, layer_version

def analyze_exrs_in_version(version_path):
    """
    Analyse the EXRs files in the given version path folder, and store the datas into dict to editing them.
    :param str version_path:
    :return:
    :rtype: set, set, list[str]
    """
    images_files = [f for f in os.listdir(version_path) if f.lower().endswith('.exr')]

    channel_stats = {}
    empty_channels = set()
    matte_channels = set()
    color_override_channels = set()

    if not images_files:
        images_files = [f for f in os.listdir(version_path)] #If no EXRs, we just want to copy everything
        return empty_channels, matte_channels, color_override_channels, images_files

    for fname in images_files:
        image_path = os.path.join(version_path, fname)
        input_image = oiio.ImageInput.open(image_path)
        if not input_image:
            logger.warning(f"Warning: Cannot open {image_path}")
            continue

        spec = input_image.spec()
        pixels = input_image.read_image()
        input_image.close()

        np_pixels = np.array(pixels).reshape((spec.height, spec.width, spec.nchannels))
        for channel_index, channel_name in enumerate(spec.channelnames):
            values = np_pixels[:, :, channel_index]
            max_value = np.max(values)

            if channel_name not in channel_stats:
                channel_stats[channel_name] = {"max": max_value, "count": 1}
            else:
                channel_stats[channel_name]["max"] = max(channel_stats[channel_name]["max"], max_value)
                channel_stats[channel_name]["count"] += 1

            # Track "coloroverride" / "colour_override" / "matte"
            if 'coloroverride' in channel_name.lower() or 'colour-override' in channel_name.lower():
                base_channel = channel_name.split('.')[0]
                color_override_channels.add(base_channel)

            if 'matte' in channel_name.lower():
                base_channel = channel_name.split('.')[0]
                matte_channels.add(base_channel)

    # Determine empty channels
    for channel, stat in channel_stats.items():
        #Track for tonal channel here if we don't want to be removes from empty_channel group
        if 'tonal' in channel.lower() and not 'matte' in channel.lower():
            empty_channels.add(channel.split('.')[0])

        elif stat["max"] == 0:
            empty_channels.add(channel.split('.')[0])
        elif channel.split('.')[0] in empty_channels:
            empty_channels.remove(channel.split('.')[0])

    return empty_channels, matte_channels, color_override_channels, images_files

def modify_and_copy_exrs(src_version, dst_version, new_version_label, exr_files,
                         empty_channels, matte_channels, coloroverride_channels):
    """
    Modify the given EXRs and save it to its new version folder, using empty_channel, matte_channels and
    coloroverride_channels dicts to find which channel we need to remove, or update before copying.
    :param str src_version:
    :param str dst_version:
    :param list[str] exr_files:
    :param dict empty_channels:
    :param dict matte_channels:
    :param dict coloroverride_channels:
    """
    for fname in exr_files:
        src_path = os.path.join(src_version, fname)
        basename, extension = os.path.splitext(fname)
        new_fname = re.sub(r"v\d+", new_version_label, basename) + extension
        dst_path = os.path.join(dst_version, new_fname)

        if not empty_channels and not matte_channels and not coloroverride_channels:
            shutil.copy2(src_path, dst_path)
            continue

        inp = oiio.ImageInput.open(src_path)
        spec = inp.spec()
        pixels = inp.read_image()
        inp.close()

        np_pixels = np.array(pixels).reshape((spec.height, spec.width, spec.nchannels))

        new_channels = []
        new_data = []
        override_alpha_layers = {}

        for i, channel_name in enumerate(spec.channelnames):
            base_channel = channel_name.split('.')[0]

            if base_channel in empty_channels:
                continue # Skip completely

            if base_channel in coloroverride_channels:
                if channel_name.endswith(".R"):
                    override_alpha_layers[base_channel] = np_pixels[:, :, i]
                continue

            if base_channel in matte_channels:
                if channel_name.endswith(".A"):
                    override_alpha_layers[base_channel] = np_pixels[:, :, i]
                continue

            new_channels.append(channel_name)
            new_data.append(np_pixels[:, :, i])

        # Inject override alphas
        for base, alpha in override_alpha_layers.items():
            new_channels.append(f"{base}.mask")
            new_data.append(alpha)

        try:
            final_data = np.stack(new_data, axis=-1)
        except ValueError: #If channel is empty, create an empty EXR
            final_data = np.empty((0, 0, 0))

        out_spec = oiio.ImageSpec()
        out_spec.width = spec.width
        out_spec.height = spec.height
        out_spec.nchannels = len(new_channels)
        out_spec.channelnames = new_channels
        out_spec.format = spec.format #We want to be sure we use the format of the input EXR

        out = oiio.ImageOutput.create(dst_path)
        out.open(dst_path, out_spec)
        out.write_image(final_data)
        out.close()

def publish_version_on_sg(harmony_folder, task_id):
    """
    Local process to publish a SG version of the created Harmony Folder with updated layers, under TA Layer Export Task.
    :param str harmony_folder:
    :param int task_id:
    """
    multiPublishNode = MultiPublish2()
    multiPublishNode.plug("source_path").set_value(harmony_folder)
    multiPublishNode.name = ("Publish Harmony")
    multiPublishNode.plug("task_id").set_value(task_id)
    description = (
        "Publish Harmony folder after Reduced channels layers process"
    )
    multiPublishNode.plug("description").set_value(description)

    multiPublishNode.run()


def get_sg_version_info(shot_name):
    """
    get the sg version info for given shot name.
    :param str shot_name:
    :return:
    :rtype: sg_versions list
    :rtype: sg_task_id int
    """

    #Get the SG shot info
    sg_shot =  env.sg.find_one("Shot", [["project", "is", project_record], ["code", "is", shot_name]])
    if not sg_shot:
        return None
    sg_shot_id = sg_shot['id']
    #Get the task for TA Layer Export for specified shot
    task = 'TA Layer Export'
    sg_task_id = get_sg_task_id(sg_shot_id, task)
    if not sg_task_id:
        return None

    #Get the list of versions not in omit.
    version_filters = [
            ['entity', 'is', {'type': 'Shot', 'id': sg_shot_id}],
            ['sg_task', 'name_is', task],
            ["sg_status_list", "is_not", "omt"]
        ]
    version_fields = ['code', 'version', 'sg_path_to_movie']
    versions = env.sg.find('Version', filters=version_filters, fields=version_fields, order=[{'field_name': 'created_at',
                                                                                             'direction': 'desc'}])
    if not versions:
        return None
    return versions, sg_task_id

def get_sg_task_id(shot_id, task_name):
    """
    Get SG task ID for given Task name and shot ID.
    :param int shot_id:
    :param str task_name:
    :return:
    :rtype: int task id
    """
    filters= [["project", "is", project_record], ["content", "is", task_name],
              ["entity", "is", {"type": "Shot", "id": shot_id}]]
    query_fields = ["id"]
    target_task_record = env.sg.find_one("Task", filters, query_fields)
    return target_task_record['id']

def layer_treatment(layer_name, layers_source_path, layers_dest_path, sg_versions, version):
    """
    function to copy the EXRs for given layer, removing empty channels and make the channels
    with 'matte' or 'coloroverride' in the name as Alpha-Only channels.
    :param str layer_name:
    :param str layers_source_path:
    :param str layers_dest_path:
    :param list sg_versions:
    :param str version:
    """
    layer_path = os.path.join(layers_source_path, layer_name)
    if not os.path.isdir(layer_path):
        return
    logger.info(f"Analyzing layer: {layer_name}")
    layer_version = f"{layer_path}\{version}"
    if not os.path.isdir(layer_version):
        layer_version = None
        logger.warning(f"No version {version} found in {layer_name}")
        for each_sg_version in sg_versions:
            for each_layer_version in os.listdir(layer_path):
                if each_layer_version in each_sg_version['code']:
                    layer_version = f"{layer_path}\{each_layer_version}"
                    logger.warning(f'will use the {each_layer_version} instead')
                    break
            if layer_version:
                break

    if not layer_version:
        logger.warning(f'no version not in omit found for {layer_name}, skipped it')
        return

    empty_channels, matte_channels, coloroverride_channels, exrs = analyze_exrs_in_version(layer_version)
    logger.info(f"Empty channels: {sorted(empty_channels)}")
    logger.info(f"Matte overrides: {sorted(matte_channels)}")
    logger.info(f"ColorOverride overrides: {sorted(coloroverride_channels)}")

    new_ver_path, new_ver_label = create_new_version_path(layer_version, layers_dest_path)
    logger.info(f"Creating new EXRs right now")
    modify_and_copy_exrs(layer_version, new_ver_path, new_ver_label, exrs,
                         empty_channels, matte_channels, coloroverride_channels)
    logger.info(f"New version created at: {new_ver_path}")

    exr_generic_label = exrs[0].replace(exrs[0].rsplit('.')[1], '@@@@')
    layer_path = f'{new_ver_path}\{exr_generic_label}'


def main():
    """
    main function to get argument layers path from bat script, and run the function to
    create the Harmony folder. will run the concurrent function to treat al layers individualy,
    and them publish the new Harmony folder with reduced layers.
    """
    shot_name = sys.argv[1]
    sg_versions, sg_task_id = get_sg_version_info(shot_name)

    if not sg_versions or not sg_task_id:
        logger.warning("Invalid given shot")
        sys.exit(1)

    latest_sg_version = sg_versions[0]
    local_harmony_folder, layers_dest_path, layers_source_path, version = create_harmony_version_folders(latest_sg_version)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(
                    layer_treatment,
              layer_name, layers_source_path, layers_dest_path, sg_versions, version) for layer_name in os.listdir(layers_source_path)]
        for future in concurrent.futures.as_completed(futures):
            try:
                result_layer = future.result()
            except Exception as e:
                logger.info(f'issue with: {e}')

    publish_version_on_sg(local_harmony_folder, sg_task_id)

if __name__ == "__main__":
    main()
