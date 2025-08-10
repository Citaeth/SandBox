import maya.cmds as cmds
import logging

logger = logging.getLogger(__name__)

'''
Add in a world space set up. V009
For use in assets that have used a skin setup and will
require vector data for surfacing.
Adds attributes for world space transform data on all 
specified meshes to be cached at tech publish time, 
driven by direct connection from locators
'''
# Secondary controls visible by default
cmds.setAttr("assetAnnotation.secondary", 1)


# Add world space attributes to the mesh
def add_world_space_attributes(obj):
    selectedMesh = obj

    # List of attributes to add
    attributes = ["Cache_tpose2shotTX", "Cache_tpose2shotTY", "Cache_tpose2shotTZ",  # Translate
                  "Cache_tpose2shotRX", "Cache_tpose2shotRY", "Cache_tpose2shotRZ",  # Rotate
                  "Cache_tpose2shotSX", "Cache_tpose2shotSY", "Cache_tpose2shotSZ",  # Scale

                  "Cache_shot2worldTX", "Cache_shot2worldTY", "Cache_shot2worldTZ",
                  "Cache_shot2worldRX", "Cache_shot2worldRY", "Cache_shot2worldRZ",

                  "Cache_world2tposeTX", "Cache_world2tposeTY",
                  "Cache_world2tposeTZ", ]  # Rotation Inverse Matrix used to reset the position

    for attr in attributes:
        if not cmds.attributeQuery(attr, node=selectedMesh, exists=True):
            cmds.addAttr(selectedMesh, ln=attr, at="double", keyable=True)
            cmds.setAttr("{}.{}".format(selectedMesh, attr), keyable=False)


def create_expression(obj):
    """
    Create expressions driven by the joint with the highest influence
    on a skinned mesh, that drives xform transform data onto attributes
    on the skinned mesh, including bounding box centre pivot
    """

    selectedMesh = obj
    drivingJoint = skinnedMeshes[obj]
    bigAttrList = ["X", "Y", "Z"]
    logger.info("selectedMesh is {}".format(selectedMesh))
    logger.info("Driving joint is {}".format(drivingJoint))

    # Query if the Mconstraints_grp exists, otherwise create it
    if not cmds.objExists("Mconstraints_grp"):
        cmds.group(n="Mconstraints_grp", p="System", em=True)

    # Query if the MglobalSurfacing_grp exists, otherwise create it
    if not cmds.objExists("MglobalSurfacing_grp"):
        cmds.group(n="MglobalSurfacing_grp", p="System", em=True)

    # Check if locators already exist
    # in case geo is being controlled by similar joints
    locatorsExist = cmds.objExists("{}_XYZ".format(drivingJoint))

    if locatorsExist == True:
        bufferLocator = "{}_XYZ".format(drivingJoint)

    else:
        bufferLocator = cmds.spaceLocator(n="{}_XYZ".format(drivingJoint))[0]

    # Get centred pivot point data on mesh
    worldPivotTransform = cmds.objectCenter(selectedMesh)
    logger.info("Debug: 'worldPivotTransform':  {}".format(worldPivotTransform))

    bufferTranslate = "{}.translate".format(bufferLocator)
    # Add constraints to locators
    if locatorsExist == False:
        cmds.setAttr(bufferTranslate, worldPivotTransform[0], worldPivotTransform[1], worldPivotTransform[2],
                     type="double3")
        newParentConstraint = cmds.parentConstraint(drivingJoint, bufferLocator, mo=True)
        newScaleConstraint = cmds.scaleConstraint(drivingJoint, bufferLocator, mo=False)

        # File everything away to neat locations
        '''
        jointSuffix = drivingJoint.split("_")[-1]
        jointSuffix = "_" + jointSuffix
        print("jointSuffix is {}".format(jointSuffix))
        '''

        cmds.parent(newParentConstraint, "Mconstraints_grp")
        cmds.parent(bufferLocator, "MglobalSurfacing_grp")
        cmds.setAttr('Mconstraints_grp.visibility', 0)

    # Connect locators buffer to get translate, rotate and scale value
    for attr in bigAttrList:
        cmds.connectAttr("{}.translate{}".format(bufferLocator, attr), "{}.Cache_worldT{}".format(selectedMesh, attr))
        cmds.connectAttr("{}.rotate{}".format(bufferLocator, attr), "{}.Cache_worldR{}".format(selectedMesh, attr))
        cmds.connectAttr("{}.scale{}".format(bufferLocator, attr), "{}.Cache_worldS{}".format(selectedMesh, attr))

    # Connect the Rotation Proxy
    compose_mat = cmds.createNode("composeMatrix")
    inverse_mat = cmds.createNode("inverseMatrix")
    decompose_mat = cmds.createNode("decomposeMatrix")

    cmds.connectAttr("{}.outputMatrix".format(compose_mat), "{}.inputMatrix".format(inverse_mat))
    cmds.connectAttr("{}.outputMatrix".format(inverse_mat), "{}.inputMatrix".format(decompose_mat))

    for axe in bigAttrList:
        cmds.connectAttr("{}.rotate{}".format(bufferLocator, axe), "{}.inputRotate{}".format(compose_mat, axe))
        cmds.connectAttr("{}.outputRotate{}".format(decompose_mat, axe),
                         "{}.Cache_proxyR{}".format(selectedMesh, axe))


# Find all meshes with "worldSpaceControls" tag
allMesh = [i for i in cmds.ls(type="transform") if "_geo_" in i]
worldSpaceMeshes = []
for i in allMesh:
    attrQuery = cmds.attributeQuery("worldSpaceControl", node=i, exists=True)
    if attrQuery == True:
        logger.info("'worldSpaceControl' found on {}".format(i))
        worldSpaceMeshes.append(i)
    else:
        logger.info("no 'worldSpaceControl' found on {}".format(i))
cmds.select(worldSpaceMeshes)

# Create dictionary to store skinned mesh and joint
skinnedMeshes = {}


# Extract joints from skinclusters from those worldspace meshes
def extractJoint(obj):
    mainMesh = obj
    logger.info("Debug A - mainMesh is {}".format(mainMesh))

    meshSkinCluster = [i for i in cmds.ls(cmds.listHistory(mainMesh)) if "skinCluster" in i][0]
    logger.info("Debug B - skinCluster is {}".format(meshSkinCluster))

    influenceJoints = cmds.skinCluster(meshSkinCluster, q=True, influence=True)
    logger.info("Debug C - influenceJoints are {}".format(influenceJoints))

    allVerts = cmds.polyListComponentConversion(mainMesh, tv=True)[0]
    logger.info("Debug D - allVerts are {}".format(allVerts))

    arbitraryVert = allVerts.replace("[*]", "[0]")
    logger.info("Debug E - arbitraryVert is {}".format(arbitraryVert))

    skinValueDictionary = {}
    skinValueSortList = []

    # Get the joint's skin weight value to find the heaviest weighted joint
    for i in influenceJoints:
        value = cmds.skinPercent(meshSkinCluster, arbitraryVert, query=True, value=True)[0]
        skinValueDictionary[value] = i
        skinValueSortList.append(value)

    logger.info("Debug F - skinValueSortList is {}".format(skinValueSortList))

    skinValueSortList.sort()
    logger.info("Debug G - sorted skinValueSortList is {}".format(skinValueSortList))

    mainJointKey = skinValueSortList[-1]
    logger.info("Debug H - mainJointKey is {}".format(mainJointKey))

    mainJoint = skinValueDictionary[mainJointKey]
    logger.info("Debug I - mainJoint is {}".format(mainJoint))

    skinnedMeshes[mainMesh] = mainJoint
    logger.info("{} added to skinnedMeshes with {}".format(mainMesh, mainJoint))


for obj in worldSpaceMeshes:
    extractJoint(obj)

for obj in skinnedMeshes:
    add_world_space_attributes(obj)
    create_expression(obj)
    logger.info("World space tracking setup on {} complete".format(obj))
