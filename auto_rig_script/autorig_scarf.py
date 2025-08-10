import colorsys
import maya.cmds as cmds

def create_follicle_joint(name, joint_id, surface, u_value, v_value, follicles_group, temp=False):
    """
    Function to create a follicle joint setup on the given position of the given surface.
    We can choose to have the follicle temporary or not, depending of the joint should be constraint
    on the surface, or if we want it to be only on the desired position. It's usualy used to have the
    joint that will constraint the surface.
    :param str name: name of the joint/follicle, it will contain the horizontal position (low, mid, up)
    :param int joint_id: id of the joint, for the vertical order
    :param str surface: the nurbs surface where we want to snap the follicle/joint
    :param int u_value:
    :param int v_value:
    :param str follicles_group: name of the group that we want to parent the created follicle/joint setup
    :param bool temp: choose if the joint should stay constrained to the surface or not.
    """
    follicle_shape = cmds.createNode("follicle")
    follicle_transform = cmds.listRelatives(follicle_shape, parent=True)[0]
    if not temp:
        follicle_transform = cmds.rename(follicle_transform, "M_{}Follicle{:02d}_utl".format(name, joint_id))
        follicle_shape = cmds.listRelatives(follicle_transform, shapes=True)[0]

    cmds.connectAttr(surface + ".local", follicle_shape + ".inputSurface")
    cmds.connectAttr(surface + ".worldMatrix[0]", follicle_shape + ".inputWorldMatrix")

    cmds.setAttr(follicle_shape + ".parameterU", u_value)
    cmds.setAttr(follicle_shape + ".parameterV", v_value)

    cmds.connectAttr(follicle_shape + ".outTranslate", follicle_transform + ".translate")
    cmds.connectAttr(follicle_shape + ".outRotate", follicle_transform + ".rotate")
    if not temp:
        cmds.parent(follicle_transform, follicles_group)

    joint_name = "M_{}{:02d}_jnt".format(name, joint_id)
    cmds.select(clear=True)
    joint = cmds.joint(name=joint_name, radius=10)
    cmds.parent(joint, follicle_transform)
    cmds.setAttr(joint + ".translate", 0, 0, 0)
    cmds.setAttr(joint + ".rotate", 0, 0, 0)
    if temp:
        position = cmds.xform(follicle_transform, q=True, ws=True, t=True)
        rotation = cmds.xform(follicle_transform, q=True, ws=True, ro=True)
        cmds.parent(joint, world=True)
        cmds.xform(joint, ws=True, t=position)
        cmds.xform(joint, ws=True, ro=rotation)
        cmds.delete(follicle_transform)
    return joint

def color_controller(ctrl_name, rgb=(1, 0, 0)):
    """
    function to change to the given color the given controller's color.
    :param str ctrl_name: controller that we want to change the color
    :param tupple rgb: rgb code of the color we want to gives at our controller
    """
    print(ctrl_name)
    shape = cmds.listRelatives(ctrl_name, shapes=True)[0]
    cmds.setAttr(shape + ".overrideEnabled", 1)
    cmds.setAttr(shape + ".overrideRGBColors", 1)
    cmds.setAttr(shape + ".overrideColorRGB", rgb[0], rgb[1], rgb[2])

def add_control_attribute(control_name):
    cmds.addAttr(control_name, longName = "Control", at = "bool", keyable = False, defaultValue = 1)
    cmds.setAttr("{}.Control".format(control_name), lock = True)

def create_ribbon_rig(geometry, mbase_offset, number_of_joints, number_of_fine_controllers):
    """
    Main function to create the Scarf rig on the given geometry. It will create a two Nurbs curve setup.
    The controllers that we'll manipulate will constraint the low Res Nurbs.
    The High res NURBS will be a rebuild of the low res, and will follow it. All the joints that will skin
    the scarf geo are on this high res nurbs.
    Idealy, we would like to have one joint per vertical edge of the model, to avoid any automatic skin issue.
    Change the number_of_joints attribut to adapt at the res of the model.
    The geometry and the high nurbs will be hidden, to make the rig workable by animator, with an Option control to
    unhide the geometry at the end to publish it.
    :param str geometry: name of the Scarf geometry
    :param str mbase_offset: name of base controller from BattleRig that will constraint our whole rig setup
    :param int number_of_joints: number of bind joints we want on the setup, make it equal to the number of vertical edge of
                                 the skinned model
    :param int number_of_fine_controllers: number of fine controllers we want for the details
    """
    if not cmds.ls(geometry):
        return

    #Unlock offset control scale
    for attr in ('X','Y', 'Z'):
        cmds.setAttr('{}.scale{}'.format(mbase_offset, attr), keyable=True, lock=False)

    surface_name="scarf_surface"
    bounding_box = cmds.exactWorldBoundingBox(geometry)
    min_x, min_y, min_z, max_x, max_y, max_z = bounding_box

    length_x = max_x - min_x
    length_y = max_y - min_y
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    center_z = (min_z + max_z) / 2.0

    ribbon_surface = cmds.nurbsPlane(name=surface_name,
                                     width=length_x,
                                     lengthRatio=length_y / length_x if length_x != 0 else 0.1,
                                     patchesU= number_of_fine_controllers-1,
                                     patchesV=1,
                                     axis=[0, 0, -1],
                                     degree=2,
                                     )[0]

    cmds.move(center_y, ribbon_surface, relative=True, objectSpace=True, worldSpaceDistance=True, moveY=True)
    rebuild = cmds.rebuildSurface(ribbon_surface,
                                  constructionHistory=True,
                                  replaceOriginal=False,
                                  endKnots=1, keepRange=0,
                                  keepCorners=1,
                                  spansU=number_of_joints,
                                  degreeU=3,
                                  spansV=2,
                                  degreeV=3
                                  )[0]
    cmds.setAttr("{}.visibility".format(rebuild), False)

    system_group = "System"

    cmds.parent(ribbon_surface, system_group)
    cmds.parent(rebuild, system_group)

    options_ctrl = cmds.circle(name='M_ScarfOptions_ctl', normal=(0, 1, 0), radius=250)[0]
    add_control_attribute(options_ctrl)
    cmds.sets(options_ctrl, include="animControls")
    color_controller(options_ctrl, rgb=(1, 1, 0))
    for each_param in ["translateX","translateY","translateZ","rotateX", "rotateY", "rotateZ",
                       "scaleX", "scaleY", "scaleZ", "visibility"]:
        cmds.setAttr("{}.{}".format(options_ctrl, each_param), keyable = False, channelBox=False)
    cmds.parent(options_ctrl, system_group)
    cmds.parentConstraint(mbase_offset, options_ctrl)
    cmds.addAttr(options_ctrl, longName="ShowGeometry", attributeType='bool', keyable=True)
    cmds.connectAttr("{}.ShowGeometry".format(options_ctrl), "{}.visibility".format(geometry))

    cmds.addAttr(options_ctrl, longName="FK_Parent_Controllers", attributeType='bool', keyable=True)

    created_joints = []

    for v_value in [0, 0.5, 1]:
        line = "Down" if v_value == 0 else "Mid" if v_value == 0.5 else "Up"
        follicles_group = cmds.group(empty=True, name="RibbonsFollicles{}_grp".format(line))
        cmds.setAttr("{}.visibility".format(follicles_group), False)
        cmds.parent(follicles_group, system_group)
        for joint_id in range(number_of_joints):
            u_value = float(joint_id) / (number_of_joints - 1)
            name = "Scarf{}".format(line)
            joint = create_follicle_joint(name, joint_id, rebuild, u_value, v_value, follicles_group, False)
            created_joints.append(joint)
            for attr in ('X','Y', 'Z'):
                cmds.connectAttr('{}.scale{}'.format(mbase_offset, attr) ,'{}.scale{}'.format(joint, attr))

    cmds.select(created_joints)
    cmds.select(geometry, add=True)
    cmds.skinCluster()

    fine_joint_list = []
    fine_controller_dict = {"Down": [], "Mid": [], "Up": []}

    for v_value in [0.5, 0, 1]:
        line = "Down" if v_value == 0 else "Mid" if v_value == 0.5 else "Up"
        for controller_id in range(number_of_fine_controllers):
            u_value = float(controller_id) / (number_of_fine_controllers - 1)
            joint = create_follicle_joint("Fine{}".format(line), controller_id, rebuild, u_value, v_value, None, True)
            cmds.setAttr("{}.visibility".format(joint), False)
            fine_joint_list.append(joint)

            fine_controller = cmds.circle(name="M_{}Fine{:02d}_ctl".format(line, controller_id), normal=(0, 1, 0), radius=50)[0]
            if line != "Mid":
                cmds.select("{}.cv[1]".format(fine_controller))
                cmds.select("{}.cv[3]".format(fine_controller), add=True)
                cmds.select("{}.cv[5]".format(fine_controller), add=True)
                cmds.select("{}.cv[7]".format(fine_controller), add=True)
                cmds.scale( 0.5, 0.5, 0.5, relative=True, pivot=(0, 0, 0))

            add_control_attribute(fine_controller)
            cmds.sets(fine_controller, include="animControls")

            color_controller(fine_controller, rgb=(1, 0, 0))
            fine_controller_dict[line].append(fine_controller)
            fine_controller_offset = cmds.group(fine_controller, name="{}_offset".format(fine_controller))
            cmds.parent(fine_controller_offset, joint)
            cmds.setAttr(fine_controller_offset + ".translate", 0, 0, 0)
            cmds.setAttr(fine_controller_offset + ".rotate", 0, 0, 0)
            cmds.parent(fine_controller_offset, world=True)
            cmds.parent(joint, fine_controller)
            if line is not "Mid":
                cmds.parent(fine_controller_offset, "M_MidFine{:02d}_ctl".format(controller_id))

    cmds.select(fine_joint_list)
    cmds.select(ribbon_surface, add=True)
    cmds.skinCluster()

    # CREATE MAIN CONTROLLERS, CHANGE HERE MAIN INTERVAL VARIABLE TO CHANGE THE FREQUENCE
    main_interval = 5
    scarf_main_controllers = []
    main_group = cmds.group(empty=True, name="ScarfMain_grp")
    cmds.parent(main_group, system_group)
    cmds.parentConstraint(mbase_offset, main_group)
    cmds.scaleConstraint(mbase_offset, main_group)
    for i in range(0, number_of_fine_controllers, main_interval):
        main_number = 1
        position = cmds.xform(fine_controller_dict["Mid"][i], query=True, worldSpace=True, translation=True)
        main_controller = cmds.circle(name='M_ScarfMain{:02d}_ctl'.format(i), normal=(0, 1, 0), radius=150)[0]
        add_control_attribute(main_controller)
        cmds.sets(main_controller, include="animControls")
        color_controller(main_controller, rgb=(1, 1, 0))
        offset = cmds.group(main_controller, name=main_controller + '_offset')
        cmds.xform(offset, worldSpace=True, translation=position)
        for j in range(i, i+5):
            cmds.parent("M_MidFine{:02d}_ctl_offset".format(j), main_controller)
            r,g,b = colorsys.hsv_to_rgb(float(j)/5, 1, 1)
            color_controller("M_MidFine{:02d}_ctl".format(j), (r,g,b))

            r,g,b = colorsys.hsv_to_rgb(float(j)/5-0.05, 1, 0.4)
            color_controller("M_UpFine{:02d}_ctl".format(j), (r,g,b))
            color_controller("M_DownFine{:02d}_ctl".format(j), (r,g,b))

        if scarf_main_controllers:
            parent_constraint_main = cmds.parentConstraint(scarf_main_controllers[-1], offset, maintainOffset=True)[0]
            cmds.connectAttr("{}.FK_Parent_Controllers".format(options_ctrl), "{}.{}W0".format(parent_constraint_main, scarf_main_controllers[-1]))
        scarf_main_controllers.append(main_controller)
        cmds.parent(offset, main_group)
        main_number += 1

create_ribbon_rig(
    geometry="C_sonamScarfC_geo_0",
    mbase_offset = "MbaseOffset_ctl",
    number_of_joints=151,           #TO CHANGE DEPENDING ON THE RESOLUTION OF YOUR MODEL
    number_of_fine_controllers=40,   #CHANGE HERE THE NUMBER OF FINE CONTROLLERS YOU WANT
    )
