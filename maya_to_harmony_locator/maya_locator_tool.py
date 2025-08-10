import maya.cmds as cmds
from PySide6 import QtWidgets, QtCore, QtGui
import logging
import os
import re

logger = logging.getLogger(__name__)

LocatorToolInstance=None

class LocatorToolUI(QtWidgets.QWidget):
    """
    Maya UI that allow you to create locator snapped on object in your scene.
    Allow you to export the locators in a .ma scene, with an offset animation starting at frame 1, to be used in
    Harmony.
    """

    def __init__(self, parent=None):
        """
        create the main window, define some class variables and call it.
        :param parent:
        """
        super(LocatorToolUI, self).__init__(parent=parent)
        self.setWindowTitle('ShotBuilder - Locator Tool')
        self.resize(500, 400)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.start_frame = cmds.playbackOptions(query=True, minTime=True)
        self.end_frame = cmds.playbackOptions(query=True, maxTime=True)

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
        setup_box.setLayout(setup_layout)

        lists_box = QtWidgets.QGroupBox()
        locator_tool_layout.addWidget(lists_box)
        lists_layout = QtWidgets.QVBoxLayout()
        lists_layout.setContentsMargins(0, 0, 0, 0)
        lists_box.setLayout(lists_layout)

        create_locator_button = QtWidgets.QPushButton("Create a locator on selected item")
        create_locator_button.clicked.connect(self.create_locator)
        setup_layout.addWidget(create_locator_button)

        self.shot_menu = QtWidgets.QComboBox()
        self.fill_shot_combobox()
        setup_layout.addWidget(self.shot_menu)

        self.list_loc_widget = QtWidgets.QListWidget()
        self.list_loc_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_loc_widget.setFont(QtGui.QFont("Arial", 14))
        lists_layout.addWidget(self.list_loc_widget)

        offset_box = QtWidgets.QGroupBox()
        locator_tool_layout.addWidget(offset_box)
        offset_layout = QtWidgets.QHBoxLayout()
        offset_box.setLayout(offset_layout)

        self.offset_value_x = QtWidgets.QLineEdit('0.00')
        self.offset_value_y = QtWidgets.QLineEdit('0.00')
        self.offset_value_z = QtWidgets.QLineEdit('0.00')
        offset_layout.addWidget(self.offset_value_x)
        offset_layout.addWidget(self.offset_value_y)
        offset_layout.addWidget(self.offset_value_z)

        self.apply_offset_button = QtWidgets.QPushButton("Apply translate offset on selected locator")
        self.apply_offset_button.clicked.connect(self.apply_offset)
        offset_layout.addWidget(self.apply_offset_button)

        export_selected_locator_button = QtWidgets.QPushButton("Export selected locator(s)")
        export_selected_locator_button.clicked.connect(self.export_selected_locator)
        locator_tool_layout.addWidget(export_selected_locator_button)

        main_layout.addWidget(locator_tool_widget)

    def fill_shot_combobox(self):
        """
        fill the ComboBox in the UI to add the list of the shot currently in the scene, and an option "Use time Slider
        Range", in case None shot are in the scene, or if the user prefer to use a custom time range.
        :return:
        """
        shot_list = cmds.ls(type="shot")
        if shot_list:
            for each_shot in shot_list:
                shot_name = cmds.getAttr(f"{each_shot}.shotName")
                shot_start_frame = cmds.getAttr(f"{each_shot}.startFrame")
                shot_end_frame = cmds.getAttr(f"{each_shot}.endFrame")
                self.shot_menu.addItem(f"{shot_name} [{shot_start_frame} - {shot_end_frame}]")
        self.shot_menu.addItem("Use Time Slider Range")

    def create_locator(self):
        """
        Ask the user for a locator name, created it, parent it to the selected item and add it to the QList in the
        UI, with the item it's linked.
        """
        selected_item = cmds.ls(selection=True)
        locator_name=""
        if not selected_item:
            logger.warning("Please select something to connect the locator!")
            return

        dialog = GivesLocatorName()
        if dialog.exec_():
            locator_name = dialog.input_name.text()
        if not locator_name:
            logger.warning("Enter a locator name please!")
            return

        locator = cmds.spaceLocator(name=locator_name)
        parent = cmds.parentConstraint(selected_item[0], locator, maintainOffset=True)[0]
        cmds.scaleConstraint(selected_item[0], locator, maintainOffset=False)
        parameters = ["targetOffsetTranslateX", "targetOffsetTranslateY", "targetOffsetTranslateZ",
                      "targetOffsetRotateX", "targetOffsetRotateY", "targetOffsetRotateZ"]

        for each_offset_param in parameters:
            cmds.setAttr(f"{parent}.target[0].{each_offset_param}", 0)

        self.list_loc_widget.addItem(f"{locator_name} -> {selected_item[0]}")

    def get_selected_locator_in_ui(self):
        """
        function to export selected locators in the UI.
        :return:
        """
        selected_items = self.list_loc_widget.selectedItems()
        selected_locators = [item.text().split(" -> ")[0] for item in selected_items]
        return selected_locators

    def get_time_range(self):
        """
        get the time range depending on the selected shot, or the time slider.
        """
        if self.shot_menu.currentText() == "Use Time Slider Range":
            self.start_frame = cmds.playbackOptions(query=True, minTime=True)
            self.end_frame = cmds.playbackOptions(query=True, maxTime=True)
        else:
            shot_info = self.shot_menu.currentText()
            match = re.search(r"\[(\d+)\s*-\s*(\d+)]", shot_info)
            if match:
                self.start_frame = int(match.group(1))
                self.end_frame = int(match.group(2))

    def apply_offset(self):
        locators = self.get_selected_locator_in_ui()
        print(locators)
        if not locators:
            logger.warning("Please select a locator to apply offset!")
            return
        for each_locator in locators:
            constraint = cmds.listRelatives(each_locator, type="constraint", allDescendents=True)[0]
            cmds.setAttr(f"{constraint}.target[0].targetOffsetTranslateX", float(self.offset_value_x.text()))
            cmds.setAttr(f"{constraint}.target[0].targetOffsetTranslateY", float(self.offset_value_y.text()))
            cmds.setAttr(f"{constraint}.target[0].targetOffsetTranslateZ", float(self.offset_value_z.text()))
            logger.info(f"Offset applied well for {each_locator}!")

    def bake_selected_locator(self, locator, layer=True):
        """
        function to bake selected locators in the UI.
        """
        self.get_time_range()
        cmds.bakeResults(locator, simulation=True, time=(self.start_frame, self.end_frame),
                         sampleBy=1, preserveOutsideKeys=True,
                         sparseAnimCurveBake=False, removeBakedAttributeFromLayer=layer,
                         minimizeRotation=True, controlPoints=False, shape=True)
        anim_curves = cmds.keyframe(locator, query=True, name=True)
        if anim_curves:
            constraint = cmds.listRelatives(locator, type="constraint", allDescendents=True)
            if constraint:
                cmds.delete(constraint)
        cmds.select(locator)

    def scale_selected_locator(self, locator):
        """
        function to offset to frame one the given locator.
        """
        scale_locator = cmds.spaceLocator(name=f"scale_{locator}")[0]
        export_locator = cmds.spaceLocator(name=f"export_{locator}")[0]

        self.bake_selected_locator(locator, layer=False)

        cmds.parent(locator, scale_locator)
        cmds.setAttr(f"{scale_locator}.scaleX", 0.01)
        cmds.setAttr(f"{scale_locator}.scaleY", 0.01)
        cmds.setAttr(f"{scale_locator}.scaleZ", 0.01)

        cmds.parentConstraint(locator, export_locator)
        cmds.connectAttr(f"{locator}.scale", f"{export_locator}.scale")

        self.bake_selected_locator(export_locator, layer=False)
        cmds.delete(scale_locator)
        return export_locator

    def offset_selected_locator(self, locator):
        """
        bake the animation of the locator, removing the constraint to the objet. Offset the animation to the frame 1.
        :param locator:
        :return:
        """
        anim_curves = cmds.keyframe(locator, query=True, name=True)
        if anim_curves:
            min_frame = None
            for curve in anim_curves:
                keyframes = cmds.keyframe(curve, query=True)
                if keyframes:
                    first_key = min(keyframes)
                    if min_frame is None or first_key < min_frame:
                        min_frame = first_key
            if min_frame != 1:
                self.get_time_range()
                offset_frame = 1 - self.start_frame
            else:
                offset_frame = 0

            cmds.keyframe(anim_curves, edit=True, timeChange=offset_frame, relative=True)
        logger.info("Success! locator animation bake and offset well!")

    def export_selected_locator(self):
        """
        Save the .ma scene for each locator given.
        :return:
        """
        locator = self.get_selected_locator_in_ui()
        temp_folder_path = r"X:\avoa\10. Users"
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(None,
                                                                 "Select a folder to save the locator(s)",
                                                                 temp_folder_path)
        os.makedirs(os.path.dirname(folder_path), exist_ok=True)
        for each_locator in locator:
            export_locator = self.scale_selected_locator(each_locator)
            self.offset_selected_locator(export_locator)
            file_path = f"{folder_path}\\{export_locator}.ma"
            cmds.file(file_path, exportSelected=True, type="mayaAscii", force=True, preserveReferences=False,
                      constructionHistory=True, channels=True)

def load_maya_locator_tool():
    """
    Call the UI
    """
    global LocatorToolInstance
    if LocatorToolInstance and LocatorToolInstance.isVisible():
        LocatorToolInstance.close()

    LocatorToolInstance = LocatorToolUI()
    LocatorToolInstance.show()


class GivesLocatorName(QtWidgets.QDialog):
    """
    Small QDialog UI used to define the name of the locator you want to create.
    """
    def __init__(self):
        super(GivesLocatorName, self).__init__()
        self.setWindowTitle("Locator name?")
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        self.resize(100,50)

        self.label = QtWidgets.QLabel("Enter the new lcoator name :", self)
        self.input_name = QtWidgets.QLineEdit(self)
        self.button = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self
        )

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.input_name)
        layout.addWidget(self.button)
        self.setLayout(layout)

        self.button.accepted.connect(self.accept)
        self.button.rejected.connect(self.reject)

load_maya_locator_tool()
