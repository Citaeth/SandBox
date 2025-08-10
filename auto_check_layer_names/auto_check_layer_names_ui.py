from PySide2 import QtWidgets, QtCore, QtGui
import logging
import os
import re

import auto_check_layers_names_utils as utils

logger = logging.getLogger(__name__)

CheckLayerNameToolInstance = None

layer_data_dict = {}


class InfoPanel(QtWidgets.QWidget):
    """
    InfoPanel Widget, used to show details of the layers that are valid, incorrect, or with a simple number difference.
    """

    def __init__(self, parent=None):
        super(InfoPanel, self).__init__(parent=parent)
        self.hBoxLayout = QtWidgets.QHBoxLayout(self)
        self.hBoxLayout.setStretch(0, 1)

        self.tableView = QtWidgets.QTextEdit(self)
        self.tableView.setReadOnly(True)
        complex_text = """
                       <p>&#128308; following Layers have an issue:</p>
                       {}
                       <br>
                       <p>&#128994; following Layers are valid :</p>
                       {}
                       <br>
                       <p>&#128992; following Layers seems to have just a number issue:</p>
                       {}
                       <br>
                       <p>&#128993; following Layers looks like fx layers:</p>
                       {}
                       <br>
                       """.format("", "", "", "")

        self.tableView.setHtml(complex_text)
        self.hBoxLayout.addWidget(self.tableView)


class AutoCheckLayerNamesUI(QtWidgets.QWidget):
    """
    Small UI that will check at the difference of naming between layout and bg layers names of a given shot.
    """

    def __init__(self, parent=None):
        """
        create the main window, define some class variables and call it.
        """
        super(AutoCheckLayerNamesUI, self).__init__(parent=parent)
        self.setWindowTitle('Auto Checker Layers Names')
        self.resize(750, 400)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)

        self._build_ui()

    def _build_ui(self):
        """
        Build UI of the tool and call the functions.
        """
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        locator_tool_widget = QtWidgets.QGroupBox()
        locator_tool_layout = QtWidgets.QVBoxLayout()
        locator_tool_widget.setLayout(locator_tool_layout)

        setup_box = QtWidgets.QGroupBox()
        locator_tool_layout.addWidget(setup_box)
        setup_layout = QtWidgets.QHBoxLayout()
        setup_layout.setContentsMargins(0, 0, 0, 0)
        setup_box.setLayout(setup_layout)

        self.set_name_line_edit = QtWidgets.QLineEdit("Gives BG Name")

        setup_layout.addWidget(self.set_name_line_edit, stretch=2)

        check_version_button = QtWidgets.QPushButton("Get versions info of given bg set")
        check_version_button.clicked.connect(self.get_bg_informations)
        setup_layout.addWidget(check_version_button)

        self.shot_menu = QtWidgets.QComboBox()
        setup_layout.addWidget(self.shot_menu, stretch=1)
        self.shot_menu.currentTextChanged.connect(self.fill_layers_menu)

        choose_layer_box = QtWidgets.QGroupBox()
        locator_tool_layout.addWidget(choose_layer_box)
        choose_layer_layout = QtWidgets.QHBoxLayout()
        choose_layer_layout.setContentsMargins(0, 0, 0, 0)
        choose_layer_box.setLayout(choose_layer_layout)

        self.first_layer_select_auto = QtWidgets.QCheckBox("Last Layout Pub")
        self.first_layer_select_auto.stateChanged.connect(self.toggle_combobox_auto_layer)
        choose_layer_layout.addWidget(self.first_layer_select_auto, stretch=0)

        self.layer_to_compare_menu_01 = QtWidgets.QComboBox()
        choose_layer_layout.addWidget(self.layer_to_compare_menu_01, stretch=1)

        self.arrow_text_widget = QtWidgets.QLabel("----------->")
        choose_layer_layout.addWidget(self.arrow_text_widget, stretch=0)

        self.layer_to_compare_menu_02 = QtWidgets.QComboBox()
        choose_layer_layout.addWidget(self.layer_to_compare_menu_02, stretch=1)

        check_name_button = QtWidgets.QPushButton("Check layers between selected version of the BG Set")
        check_name_button.clicked.connect(self.check_naming_differences)
        locator_tool_layout.addWidget(check_name_button)

        self.first_layer_select_auto.setChecked(True)

        lists_box = QtWidgets.QGroupBox()
        locator_tool_layout.addWidget(lists_box)
        lists_layout = QtWidgets.QVBoxLayout()
        lists_layout.setContentsMargins(0, 0, 0, 0)
        lists_box.setLayout(lists_layout)

        self.list_loc_widget = InfoPanel()
        lists_layout.addWidget(self.list_loc_widget)

        main_layout.addWidget(locator_tool_widget)

    def get_bg_informations(self):
        """
        get bg asset shots list, and the layers versions for each of them, to fill the menus.
        """
        self.shot_menu.blockSignals(True)
        self.reset_ui_content()

        layer_data_dict["bg_asset"] = self.set_name_line_edit.text()
        bg_asset = self.set_name_line_edit.text()

        shots = utils.get_bg_shots(bg_asset)
        for each_shot in shots:
            self.shot_menu.addItem(each_shot["code"])
            layer_data_dict[each_shot['code']] = {}
            shot_versions_infos = utils.get_bg_layers_version(each_shot["code"], bg_asset)
            layer_data_dict[each_shot['code']]['layers_versions'] = shot_versions_infos[0]
            layer_data_dict[each_shot['code']]['last_layer_version'] = shot_versions_infos[1]
        self.shot_menu.blockSignals(False)
        self.fill_layers_menu()

    def reset_ui_content(self):
        layer_data_dict = {}
        self.shot_menu.clear()
        self.layer_to_compare_menu_01.clear()
        self.layer_to_compare_menu_02.clear()

    def fill_layers_menu(self):
        """
        fill the layers menus with the informations getting from ShotGrid, depending on the shot name selected in the shot menu.
        """
        current_shot = self.shot_menu.currentText()
        layer_list = layer_data_dict[str(current_shot)]['layers_versions']
        self.layer_to_compare_menu_01.addItems(layer_list)
        self.layer_to_compare_menu_02.addItems(layer_list)

    def build_layers_list(self, layer):
        """
        get the list of the layers of a selected version/task combo, for the given asset.
        :param str layer: string with the format "task - v###" that'll be splited to recreated the layers folder path
        """
        task = layer.split(" -")[0]
        version = layer.split("- ")[1]
        version_path = 'T:/jobs/avoa/asset/Set/{}/bg/{}/layers/{}'.format(self.set_name_line_edit.text(), task, version)
        version_layers = []
        for each_file in os.listdir(version_path):
            if "png" in each_file:
                version_layers.append(each_file)
        return version_layers, task, version

    def check_naming_differences(self):
        """
        main function to check the differences between the folder
        """
        if self.first_layer_select_auto.isChecked():  # If auto checkbox is checked, look at the last publish layout scene and use the bg version in it.
            first_task_version = "lo - v{:03d}".format(
                layer_data_dict[str(self.shot_menu.currentText())]['last_layer_version'][1])
        else:  # else, take the version gives in the UI menu.
            first_task_version = self.layer_to_compare_menu_01.currentText()
        first_version_layers, first_task, first_version = self.build_layers_list(first_task_version)

        second_task_version = self.layer_to_compare_menu_02.currentText()
        second_version_layers, second_task, second_version = self.build_layers_list(second_task_version)

        valid_layers = []
        missing_layers = []
        fx_layers = []
        wrong_layers_id_list = []

        for each_first_layer in first_version_layers:
            if each_first_layer.replace(first_task, second_task).replace(first_version,
                                                                         second_version) in second_version_layers:
                valid_layers.append(each_first_layer)
            else:
                missing_layers.append(each_first_layer)

        for each_missing_layer in missing_layers:
            if 'fx' in each_missing_layer:  # Identify if the missing layer is an fx layer, so we don't need to mind it
                fx_layers.append(each_missing_layer)
                continue

            # Identify if a layer with the good name exist, but with the wrong layer number
            prefix = each_missing_layer.replace(first_task, second_task).split("L")[0]
            match = re.search(r'L\d+', each_missing_layer)
            suffix = each_missing_layer.replace(first_version, second_version)[match.end():]

            pattern = re.compile(r"^" + re.escape(prefix) + r"L\d{3}" + re.escape(suffix) + "$")
            for each_second_layer in second_version_layers:
                if pattern.match(each_second_layer):
                    wrong_layers_id_list.append(each_second_layer)
                    continue
        self.fill(valid_layers, missing_layers, wrong_layers_id_list, fx_layers)

    def fill(self, valid_layers, missing_layers, wrong_layers_id_list, fx_layers):
        """
        update the QTextEdit with the compare layers information.
        :param list valid_layers:
        :param list missing_layers:
        :param list wrong_layers_id_list:
        :param list fx_layers:
        """
        valid_string = ""
        missing_string = ""
        wrong_id_string = ""
        fx_string = ""
        if not missing_layers:
            complex_text = '<p style="text-indent: 45px; font-size:20px">&#127870; All Layers looks valids! Yahou! &#127870; </p>'
        else:
            for each_missing_layer in missing_layers:
                missing_string = missing_string + '<p style="text-indent: 30px;">{}</p>'.format(each_missing_layer)

            for each_valid_layer in valid_layers:
                valid_string = valid_string + '<p style="text-indent: 30px;">{}</p>'.format(each_valid_layer)

            for each_wrong_id_layer in wrong_layers_id_list:
                wrong_id_string = wrong_id_string + '<p style="text-indent: 30px;">{}</p>'.format(each_wrong_id_layer)

            for each_fx_layer in fx_layers:
                fx_string = fx_string + '<p style="text-indent: 30px;">{}</p>'.format(each_fx_layer)

            complex_text = """
                           Checked if layers from {} are in {} version.
                           <br>
                           <p>&#128308; following Layers have an issue:</p>
                           {}
                           <br>
                           <p>&#128994; following Layers are valid :</p>
                           {}
                           <br>
                           <p>&#128992; following Layers seems to have just a number issue:</p>
                           {}
                           <br>
                           <p>&#128993; following Layers looks like fx layers:</p>
                           {}
                           """.format(self.layer_to_compare_menu_01.currentText(),
                                      self.layer_to_compare_menu_02.currentText(),
                                      missing_string, valid_string, wrong_id_string, fx_string)
        self.list_loc_widget.tableView.setHtml(complex_text)

    def get_folders_version(self, base_path):
        """
        get the list of version in the selected bg folder.
        :param str base_path:
        """
        version_pattern = re.compile(r'^v(\d{3})$')
        try:
            subdirs = []
            for d in os.listdir(base_path):
                match = version_pattern.match(d)
                if match and os.path.isdir(os.path.join(base_path, d)):
                    subdirs.append(d)
            if not subdirs:
                return None
            return (subdirs)
        except OSError:
            return None

    def toggle_combobox_auto_layer(self):
        """
        toggle enable state of the combobox, if user check the auto checkbox.
        """
        first_layer_enabled = not bool(self.first_layer_select_auto.isChecked())
        self.layer_to_compare_menu_01.setEnabled(first_layer_enabled)


def load_autocheck_layer_name_tool():
    """
    Call the UI
    """
    global CheckLayerNameToolInstance
    if CheckLayerNameToolInstance and CheckLayerNameToolInstance.isVisible():
        CheckLayerNameToolInstance.close()

    CheckLayerNameToolInstance = AutoCheckLayerNamesUI()
    CheckLayerNameToolInstance.show()


load_autocheck_layer_name_tool()
