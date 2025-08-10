from PySide2 import QtWidgets, QtCore

import sg
env = sg.from_env()
project_record = env.project.as_shotgun_record()

from . import sequence_sheet_utils as utils

SequenceSheetInstance=None

class SequenceSheetUI(QtWidgets.QWidget):
    """
    Nuke UI to let the user select a sequence and build a template to have a contactSheet of the
    whole sequence shots, using the last version of selected Task/Status for each shot.
    """
    def __init__(self, parent=None):
        """
        create the main window, define some class variables and call it.
        :param parent:
        """
        super(SequenceSheetUI, self).__init__(parent=parent)
        self.setWindowTitle('Sequence Sheet Tool')
        self.resize(500, 75)
        self.setWindowFlags(QtCore.Qt.Window)

        self._build_ui()

    def _build_ui(self):
        """
        Build UI of the tool, adding the widgets and call the functions.
        """
        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        select_sequence_box = QtWidgets.QGroupBox()
        select_sequence_layout = QtWidgets.QHBoxLayout()
        select_sequence_box.setLayout(select_sequence_layout)
        main_layout.addWidget(select_sequence_box)

        sequence_label = QtWidgets.QLabel('choose the sequence:')

        self.sequence_menu = QtWidgets.QComboBox()
        sequences_list_for_show = self.get_sg_sequences_info()
        if not sequences_list_for_show:
            return 'No sequences for current show context'
        for each_sequence in sequences_list_for_show:
            self.sequence_menu.addItem(each_sequence)

        self.task_menu = QtWidgets.QComboBox()
        self.task_menu.addItems(['cmp_del', 'cmp_cmp'])

        self.status_menu = QtWidgets.QComboBox()
        self.status_menu.addItems(['latest published', 'latest approved'])

        select_sequence_layout.addWidget(sequence_label)
        select_sequence_layout.addWidget(self.sequence_menu)
        select_sequence_layout.addWidget(self.task_menu)
        select_sequence_layout.addWidget(self.status_menu)

        build_contactsheet_box = QtWidgets.QGroupBox()
        build_contactsheet_layout = QtWidgets.QHBoxLayout()
        build_contactsheet_box.setLayout(build_contactsheet_layout)
        main_layout.addWidget(build_contactsheet_box)

        self.use_template_checkbox = QtWidgets.QCheckBox('Use Template file')
        self.use_template_checkbox.setChecked(True)
        build_contactsheet_layout.addWidget(self.use_template_checkbox)

        run_template_button = QtWidgets.QPushButton('Build contactSheet template for selected sequence')
        run_template_button.clicked.connect(self.on_run_template)
        build_contactsheet_layout.addWidget(run_template_button)


    def get_sg_sequences_info(self):
        """
        get the list of sequences for the show defined in the current nuke context.
        """
        sequences_code_list = []
        filters = [['project', 'is', project_record],
                   ["sg_status_list", "is_not", "omt"],
                   ]
        fields = ['code', 'id', 'sg_script_order']
        sg_sequences = env.sg.find("Sequence", filters=filters, fields=fields)
        for each_sequence in sg_sequences:
            if each_sequence['sg_script_order']:
                sequences_code_list.append(f"{each_sequence['code']}_{each_sequence['sg_script_order']}")
        sequences_code_list.sort()
        return sequences_code_list

    def on_run_template(self):
        """
        function to run the creation of the contactsheet template, fills with the selected sequence name,
        the task and status filter for the versions.
        """
        selected_sequence = self.sequence_menu.currentText()
        if selected_sequence:
            task = self.task_menu.currentText()
            status = self.status_menu.currentText()
        if self.use_template_checkbox.isChecked():
            utils.SequenceContactSheetUtils().fill_contact_sheet_template(selected_sequence, task, status)
        else:
            utils.SequenceContactSheetUtils().build_contactsheet_template(selected_sequence, task, status)


def load_sequence_sheet():
    """
    Call the UI
    """
    global SequenceSheetInstance
    if SequenceSheetInstance and SequenceSheetInstance.isVisible():
        SequenceSheetInstance.close()

    SequenceSheetInstance = SequenceSheetUI()
    SequenceSheetInstance.show()
