import nuke
from PySide2 import QtWidgets, QtCore
import logging
import os
import re
import math

logger = logging.getLogger(__name__)

import sg

env = sg.from_env()
project_record = env.project.as_shotgun_record()


class SequenceContactSheetUtils:
    """
    Utils class to build the Sequence ContactSheet in Nuke, generating from scratch of using a template if we want.
    """
    tasks = ['cmp_slp', 'cmp_pcmp', 'anm_taLayerExport', 'anm_rr']
    warnings = set()

    def build_contactsheet_template(self, sequence_name, task, status):
        """
        main function to build the contact sheet templace. will get the list of the shot
        for the given sequence, and get the last comp version for each shot, depending on selected filter:
            task (cmp_cmp or cmp_del) and status (last approved or last published).
        Will create a backdrop, all the Read nodes fills with the middle frame of the version, and connect them to
        a contactsheet node.
        Run a quick pop-up window to let the user know about potential warnings encounters during the process.
        :param str sequence_name:
        :param str task:
        :param str status:
        """
        # Get the shots list in alphabetic order
        sequence_code = sequence_name.split('_')[0]
        shots = self.get_sg_shots_for_sequence(sequence_code)
        self.tasks.insert(0, task)
        if task == 'cmp_del':
            self.tasks.insert(1, 'cmp_cmp')

        read_nodes = []
        shot_index = 0
        # For each shot, get the version of the comp depending on given filter by the user
        nuke.Undo.disable()
        for shot in shots:
            if shot['code'].startswith(f"{sequence_code}99_"):
                continue
            shot_code = shot['code']
            shot_id = shot['id']

            # Look for the last approved or published versions for the tasks in the following order:
            # Task_from_user (cmp_cmp or cmp_del) -> cmp_slp -> cmp_pcmp -> anm_taLayerExport
            for each_task in self.tasks:
                shot_task = each_task
                versions = self.get_shot_version_for_task_and_status(shot_code, shot_id, each_task, status)
                if versions:
                    break

            if not versions:
                print(f'no version for shot:{shot["code"]}')
                self.create_gray_constant_for_shot(shot['code'], shot_index)
                input_shot = self.create_template_for_shot(shot_code, version=None, task=None, status=None)
                read_nodes.append(input_shot)
                shot_index += 1
                continue
            # Create a read for the last version from the filters ones
            latest_version = versions[0]

            version, status = self.create_frame_for_shot_version(shot_code, latest_version, shot_index)
            input_shot = self.create_template_for_shot(shot_code, version, shot_task, status)
            read_nodes.append(input_shot)
            shot_index += 1

        self.create_contact_sheet_node(sequence_name, read_nodes)
        nuke.Undo.enable()

        # Run the warnings dialog if there is some, to let the user know if some shot missings and why.
        # if self.warnings:
        #    dlg = WarningDialog(self.warnings)
        #    dlg.exec_()

    def get_sg_shots_for_sequence(self, sequence_code):
        """
        get the SG shot info from given sequence.
        :param str sequence_code:
        """
        filters = [
            ['project', 'is', project_record],
            ['sg_sequence.Sequence.code', 'is', sequence_code],
            ["sg_status_list", "is_not", "omt"],
        ]
        fields = ['code', 'id', 'sg_cut_order']
        shots = env.sg.find('Shot', filters=filters, fields=fields)

        def sort_key(shot):
            cut_order = shot.get('sg_cut_order')
            if cut_order is None:
                match = re.search(r'\d+', shot['code'])
                return int(match.group()) if match else 0
            return cut_order

        shots.sort(key=sort_key)
        return shots

    def get_shot_version_for_task_and_status(self, shot_code, shot_id, task, status):
        """

        :param str shot_code:
        :param int shot_id:
        :param str task:
        :param str status:
        :return:
        """
        version_filters = [
            ['entity', 'is', {'type': 'Shot', 'id': shot_id}],
            ['code', 'contains', task]
        ]
        if status == 'latest approved':
            version_filters.append(["sg_status_list", "in", ['clapr', 'capr', 'sapr']])

        version_fields = ['code', 'version', 'sg_path_to_movie', 'sg_path_to_frames', 'frame_range', 'sg_status_list']
        versions = env.sg.find('Version', filters=version_filters, fields=version_fields,
                              order=[{'field_name': 'created_at', 'direction': 'desc'}])

        if not versions and status == 'latest approved' and 'cmp' in task:
            self.warnings.add(f"No Approved comp version found for shot {shot_code}")
        elif not versions and status == 'latest published' and 'cmp' in task:
            self.warnings.add(f"No published Comp version found for shot {shot_code}")
        return versions

    def create_gray_constant_for_shot(self, shot_code, shot_index):
        """
        If there is any issue with the shot we wanted to load, in a non-template context, we want to create a grey
        constant for this shot instead.
        :param str shot_code:
        :param int shot_index:
        :return:
        :rtype node:
        """
        grey_constant = nuke.createNode('Constant')
        grey_constant['name'].setValue(f'constant_{shot_code}')
        grey_constant['color'].setValue(0.5)

        xpos = shot_index * 100
        ypos = 50
        grey_constant.setXpos(xpos)
        grey_constant.setYpos(ypos)
        return grey_constant

    def create_frame_for_shot_version(self, shot_code, latest_version, shot_index):
        """
        create the Read node and get the frame to load for the given shot version.
        :param str shot_code:
        :param str latest_version:
        :param int shot_index:
        :return:
        :rtype:
        """
        if latest_version['sg_path_to_frames']:
            path = latest_version['sg_path_to_frames'].replace('\\', '/')
            version = latest_version['sg_path_to_frames'].split('\\')[-2]
            status = latest_version['sg_status_list']
        elif latest_version['sg_path_to_movie']:
            path = latest_version['sg_path_to_movie'].replace('\\', '/')
            version = latest_version['sg_path_to_movie'].split('\\')[-2]
            status = latest_version['sg_status_list']
        else:
            self.warnings.add(f"No frame/movie path for version {latest_version['code']}")
            self.create_gray_constant_for_shot(shot_code, shot_index)
            return 'no version', 'no status'

        # Get middle frame of the current version image sequence
        frame_range = latest_version.get('frame_range')
        if not frame_range or frame_range == 'None-None':
            self.warnings.add(f"No frame range for version {latest_version['code']}")
            frame_range = '1-1'

        try:
            start, end = map(int, frame_range.split('-'))
            frame_to_read = (start + end) // 2
            path_frame = path.replace(r'%04d', str(frame_to_read))

            read = nuke.createNode('Read')
            read['file'].setValue(path_frame)
            read['first'].setValue(start)
            read['last'].setValue(end)
            if '.mov' in path:
                read['colorspace'].setValue('color_picking')

            xpos = shot_index * 100
            ypos = 50
            read.setXpos(xpos)
            read.setYpos(ypos)
            return version, status
        except Exception as e:
            self.warnings.add(f"Error processing shot {shot_code}: {e}")
            self.create_gray_constant_for_shot(shot_code, shot_index)
            return version, status

    def set_radial_status(self, radial_node, status, task):
        """
        set the data on the radial status nuke node, that will gives color indicator about the shot version status.
        :param node radial_node:
        :param str status:
        :param str task:
        :return:
        """
        if status not in ['omt', 'nr'] and task == 'cmp_del':
            radial_node['status'].setValue('CNT')
        elif status == 'clapr':
            radial_node['status'].setValue('APP')
        elif status == 'ip':
            radial_node['status'].setValue('WIP')
        elif status in ['crtk', 'rtk', 'srtk']:
            radial_node['status'].setValue('RTK')
        else:
            radial_node['status'].setValue('RTS')

    def create_template_for_shot(self, shot_code, version, task, status):
        """
        Create the template per shot, with the Read to load the frame, reformat, texts to writes the shot info and a
        radial node to create a dot who will give info about the version status.
        :param str shot_code:
        :param str version:
        :param str task:
        :param str status:
        :return:
        """
        # frame_hold = nuke.createNode('FrameHold')
        # frame_hold['name'].setValue(f'FrameHold_{shot_code}')
        # frame_hold['firstFrame'].setValue(int(f"{frame_to_read:04d}"))

        crop = nuke.createNode('Crop')
        crop['name'].setValue(f'Crop_{shot_code}')
        crop['box'].setValue([0, -50, 2048, 938])  # crop resolution hardcoded here, maybe better TODO
        crop['reformat'].setValue('enable')
        crop['intersect'].setValue('enable')
        crop['crop'].setValue('enable')
        crop.setYpos(crop.ypos() + 25)

        shot_version_text = nuke.createNode('Text2')
        shot_version_text['name'].setValue(f'Text_{shot_code}')
        # Get the value as an argument, don't work to getting it from previous node as the name
        if version:
            shot_version_text['message'].setValue(
                f'[string range [file tail [value [topnode].file]] 6 14] -- {version}')
        else:
            shot_version_text['message'].setValue(f'{shot_code} -- v000')

        shot_version_text.setYpos(shot_version_text.ypos() + 20)

        shot_status_radial = nuke.createNode('Radial')
        shot_status_radial['name'].setValue(f'Radial_{shot_code}')
        shot_status_radial['softness'].setValue(0)
        shot_status_radial.setYpos(shot_status_radial.ypos() + 20)

        RADIUS = 26
        shot_status_radial.addKnob(nuke.XY_Knob('pos', 'pos'))
        shot_status_radial['pos'].setValue([1997, 948])  # same as crop rez, maybe better TODO
        shot_status_radial.addKnob(nuke.Double_Knob('RADIUS', 'RADIUS'))
        shot_status_radial['RADIUS'].setValue(RADIUS)
        shot_status_radial.addKnob(nuke.Enumeration_Knob('status', 'status', ['APP', 'WIP', 'RTK', 'RTS', 'CNT']))
        shot_status_radial['status'].setValue('CNT')

        self.set_radial_status(shot_status_radial, status, task)

        shot_status_radial['area'].setExpression('pos.x - RADIUS', 0)
        shot_status_radial['area'].setExpression('pos.y - RADIUS', 1)
        shot_status_radial['area'].setExpression('pos.x + RADIUS', 2)
        shot_status_radial['area'].setExpression('pos.y + RADIUS', 3)

        shot_status_radial['color'].setSingleValue(False)
        shot_status_radial['color'].setExpression(
            '[if {[value status]== "CNT"} {return 1} {return [if {[value status]== "RTK"} {return 1} {return [if {[value status]== "WIP"} {return 0.5} {return 0}]}]}]',
            0
        )

        shot_status_radial['color'].setExpression(
            '[if {[value status]== "CNT"} {return 1} {return [if {[value status]== "APP"} {return 1} {return [if {[value status]== "WIP"} {return 0.5} {return 0}]}]}]',
            1
        )

        shot_status_radial['color'].setExpression(
            '[if {[value status]== "RTS"} {return 1} {return 0[if {[value status]== "CNT"} {return 1} {return }]}]', 2
        )

        shot_status_radial['color'].setExpression('1', 3)

        return shot_status_radial

    def create_contact_sheet_node(self, sequence_name, read_nodes=None):
        """
        Build the contact sheet part of the template
        :param str sequence_name: name of the sequence
        :param list read_nodes: list of read nodes
        """
        if read_nodes:
            best_height = None
            best_width = None
            min_diff = math.inf

            num_reads = len(read_nodes)
            for width in range(1, num_reads + 1):
                height = math.ceil(num_reads / width)
                if width * height >= num_reads:
                    diff = abs(width - height)
                    if diff < min_diff:
                        best_width, best_height = width, height
                        min_diff = diff

            contact = nuke.createNode('ContactSheet')
            contact['name'].setValue('Sequence_ContactSheet')
            contact.setInput(0, read_nodes[0])
            for node_index, node in enumerate(read_nodes[1:], 1):
                contact.setInput(node_index, node)

            scale_knob = (nuke.Double_Knob('scale', 'scale'))
            contact.addKnob(scale_knob)
            scale_knob.setValue(1)
            scale_knob.setRange(0, 2)

            if contact['width'].isAnimated:
                contact['width'].clearAnimated()
            if contact['height'].isAnimated:
                contact['height'].clearAnimated()
            contact['width'].setExpression("4096*scale")
            contact['height'].setExpression("2160*scale")

            contact['columns'].setValue(best_height)
            contact['rows'].setValue(best_width)
            contact['center'].setValue('enable')
            contact['gap'].setValue(50)

            contact['roworder'].setValue('TopBottom')

            contact['tile_color'].setValue(0x9fffff)

            contact.setXpos(int((read_nodes[0].xpos() + read_nodes[-1].xpos()) / 2))
            contact.setYpos(read_nodes[0].ypos() + 400)

            crop = nuke.createNode('Crop')
            crop['name'].setValue('Crop_ContactSheet')
            crop['box'].setValue(-100, 0)
            crop['box'].setValue(-100, 1)
            crop['box'].setExpression('[value Sequence_ContactSheet.width] + 100', 2)
            crop['box'].setExpression('[value Sequence_ContactSheet.height] + [value Sequence_ContactSheet.height]/10',
                                      3)
            crop['reformat'].setValue('enable')
            crop['intersect'].setValue('enable')
            crop['crop'].setValue('enable')

            continuity_sequence_text = nuke.createNode('Text2')
            continuity_sequence_text['name'].setValue('Continuity_Contact_Text')
            continuity_sequence_text['box'].setExpression('[value Crop_ContactSheet.box.t] + 100', 1)
            continuity_sequence_text['box'].setExpression('[value Crop_ContactSheet.box.r]', 2)
            continuity_sequence_text['box'].setExpression('[value Crop_ContactSheet.box.t] + 50', 3)

            continuity_sequence_text['message'].setValue(f'CONTINUITY CONTACT - {sequence_name}')
            continuity_sequence_text['global_font_scale'].setExpression('[value Sequence_ContactSheet.scale]*1.5')

            data_contact_text = nuke.createNode('Text2')
            data_contact_text['name'].setValue('Data_Contact_Text')
            data_contact_text['box'].setExpression('[value Crop_ContactSheet.box.r]', 2)
            data_contact_text['box'].setExpression('[value Crop_ContactSheet.box.t] + 50', 3)
            data_contact_text['xjustify'].setValue('right')
            data_contact_text['yjustify'].setValue('bottom')

            user_name = os.getenv("USERNAME", None).replace('.', ' ')
            data_contact_text['message'].setValue(f'{user_name} -- [date %x]')
            data_contact_text['global_font_scale'].setExpression('[value Sequence_ContactSheet.scale]')

            read_nodes.append(data_contact_text)
            self.create_backdrop_around(read_nodes)
        else:
            self.warnings.add("No Read nodes created, skipping ContactSheet")

    def create_backdrop_around(self, nodes, label="Sequence ContactSheet"):
        """
        creation of the backdrop in nuke (because it's pretty, isn't?)
        :param list nodes: list of the Read and ContactSheet node to put in the backdrop
        :param str label:
        """
        if not nodes:
            return

        padding = 200
        min_x = min(n.xpos() for n in nodes) - padding
        max_x = max(n.xpos() + n.screenWidth() for n in nodes) + padding
        min_y = min(n.ypos() for n in nodes) - padding - 50
        max_y = max(n.ypos() + n.screenHeight() for n in nodes) + padding / 2

        backdrop = nuke.createNode("BackdropNode")
        backdrop['bdwidth'].setValue(max_x - min_x)
        backdrop['bdheight'].setValue(max_y - min_y)
        backdrop['xpos'].setValue(min_x)
        backdrop['ypos'].setValue(min_y)
        backdrop['name'].setValue('BackDrop_ContactSheet')
        backdrop['label'].setValue(label)
        backdrop['note_font_size'].setValue(28)
        backdrop['tile_color'].setValue(0x242b49ff)

        return backdrop

    def get_template_path(self):
        """
        get the template path if we choose the option to use it in the UI.
        :return:
        """
        current_dir = os.path.dirname(__file__)
        template_path = os.path.join(current_dir, 'template.nk')
        return template_path

    def fill_contact_sheet_template(self, sequence, task, status):
        """
        if the template option is selected, load it and fill the infos needed for the sg shots.
        :param str sequence:
        :param str task:
        :param str status:
        """
        contact_sheet_nodes = ['Sequence_ContactSheet', 'Crop_ContactSheet', 'Continuity_Contact_Text',
                               'Data_Contact_Text']

        template = self.get_template_path()

        nuke.nodePaste(template)
        # Get the shots list in alphabetic order
        sequence_code = sequence.split('_')[0]
        shots = self.get_sg_shots_for_sequence(sequence_code)
        self.tasks.insert(0, task)
        if task == 'cmp_del':
            self.tasks.insert(1, 'cmp_cmp')

        read_shots = []
        for node in nuke.allNodes():
            node_name = node['name'].getValue()
            match = re.search(r'(\D+)(\d+)$', node_name)
            if match:
                number_str = match.groups()[1]
                if int(number_str) > len(shots):
                    nuke.delete(node)
                elif 'Read' in node_name:
                    read_shots.append(node)
        new_contact_nodes_xpos = int((read_shots[0].xpos() + read_shots[-1].xpos()) / 2)

        for each_contact in contact_sheet_nodes:
            contact_node = nuke.toNode(each_contact)
            contact_node['xpos'].setValue(new_contact_nodes_xpos)

        contact_sheet_node = nuke.toNode('Sequence_ContactSheet')

        min_diff = math.inf
        num_reads = len(read_shots)
        for width in range(1, num_reads + 1):
            height = math.ceil(num_reads / width)
            if width * height >= num_reads:
                diff = abs(width - height)
                if diff < min_diff:
                    best_width, best_height = width, height
                    min_diff = diff
        contact_sheet_node['columns'].setValue(best_height)
        contact_sheet_node['rows'].setValue(best_width)

        continuity_sequence_text = nuke.toNode('Continuity_Contact_Text')
        continuity_sequence_text['message'].setValue(f'CONTINUITY CONTACT - {sequence}')

        user_name = os.getenv("USERNAME", None).replace('.', ' ')
        data_contact_text = nuke.toNode('Data_Contact_Text')
        data_contact_text['message'].setValue(f'{user_name} -- [date %x]')

        backdrop = nuke.toNode('BackDrop_ContactSheet')
        print(backdrop['xpos'].getValue())
        width = (new_contact_nodes_xpos - backdrop['xpos'].getValue()) * 2 + 200
        backdrop['bdwidth'].setValue(width)

        # Fill the read nodes and followings nodes with the shots infos
        for shot_index in range(1, len(read_shots) + 1):
            print(shot_index)

            read_node = nuke.toNode(f'Read{shot_index}')
            constant_node = nuke.toNode(f'Constant{shot_index}')
            switch_node = nuke.toNode(f'Switch{shot_index}')
            crop_node = nuke.toNode(f'Crop{shot_index}')
            text_node = nuke.toNode(f'Text{shot_index}')
            radial_node = nuke.toNode(f'Radial{shot_index}')
            version_task = ''

            shot_code = shots[shot_index - 1]['code']
            shot_id = shots[shot_index - 1]['id']

            read_node['name'].setValue(f'Read_{shot_code}')
            switch_node['name'].setValue(f'Switch_{shot_code}')
            crop_node['name'].setValue(f'Crop_{shot_code}')
            text_node['name'].setValue(f'Text_{shot_code}')
            radial_node['name'].setValue(f'Radial_{shot_code}')

            for each_task in self.tasks:
                version_task = each_task
                versions = self.get_shot_version_for_task_and_status(shot_code, shot_id, each_task, status)
                if versions:
                    break
            if not versions:
                print('use the constant')
                continue

            latest_version = versions[0]

            if latest_version['sg_path_to_frames']:
                path = latest_version['sg_path_to_frames'].replace('\\', '/')
                version = latest_version['sg_path_to_frames'].split('\\')[-2]
                status = latest_version['sg_status_list']
            elif latest_version['sg_path_to_movie']:
                path = latest_version['sg_path_to_movie'].replace('\\', '/')
                version = latest_version['sg_path_to_movie'].split('\\')[-2]
                status = latest_version['sg_status_list']
            else:  # If no frames or movie for selected version, turn the switch on the constant
                switch_node['which'].setValue(1)
                continue

            frame_range = latest_version.get('frame_range')
            if not frame_range or frame_range == 'None-None':
                self.warnings.add(f"No frame range for version {latest_version['code']}")
                frame_range = '1-1'

            start, end = map(int, frame_range.split('-'))
            frame_to_read = (start + end) // 2
            path_frame = path.replace(r'%04d', str(frame_to_read))

            read_node['file'].setValue(path_frame)
            read_node['first'].setValue(start)
            read_node['last'].setValue(end)
            if '.mov' in path:
                read_node['colorspace'].setValue('color_picking')

            switch_node['which'].setValue(0)

            text_node['message'].setValue(f'[string range [file tail [value [topnode].file]] 6 14] -- {version}')

            self.set_radial_status(radial_node, status, version_task)


class WarningDialog(QtWidgets.QDialog):
    """
    Small dialog UI to display to the users all warning we had during the process, to
    track missings shots or bigger issues.
    """

    def __init__(self, warnings, parent=None):
        super(WarningDialog, self).__init__(parent)
        self.setWindowTitle("Warnings during ContactSheet Build")
        self.resize(600, 400)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        info_label = QtWidgets.QLabel("The following issues were encountered:")
        layout.addWidget(info_label)

        self.text_area = QtWidgets.QPlainTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setPlainText("\n".join(warnings))
        layout.addWidget(self.text_area)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
