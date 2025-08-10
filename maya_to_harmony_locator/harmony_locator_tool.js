/*
 * Based off on Mike Overbeck 2013's, which user need to copy attribute one by one
 */

function print(message)
{
    MessageLog.trace(message);
    System.println(message);
}

/*
Maya command in ASCII file can be multi-line. Take an openned file as arg, continue reading until semicolon is found.
*/
function readFullCommand(file)
{
    var line = file.readLine();
    var completeLine = line;

    while (!file.eof && line.search(/;/) == -1)
    {
        line = file.readLine();
        completeLine = completeLine + line;
    }

    return completeLine;
}

/*
Take a Maya command as text and check if it is a createNode command. Return the created node name.
*/
function extractNodeNameFromCommand(text, node_type)
{
    if (!node_type)
    {
        node_type = "[a-zA-Z0-9]+";
    }

    var commandArgs = ["^createNode", node_type, "-n"];
    var command = commandArgs.join(" ");
    var matchList = text.match(new RegExp(command));

    if (matchList)
    {
        // Extract and peel off commas and semicolon from the name string
        var nodeName = text.slice(matchList[0].length + 2, text.length - 3);
        return nodeName;
    }
    else
    {
        return null;
    }
}

/*
* Functions to create a Peg Node and add an OrthoLock node in Harmony
*/

function createPegNode(name, tx, ty, tz, rx, ry, rz, sx, sy, sz) {
    if (!name) {
        MessageBox.information("Missing Locator Name.");
        return null;
    }

    // Create a PEG node under Top with the given name
    var pegPath = node.add("Top", name, "PEG", 0, 0, 0);
    node.setCoord(pegPath, 1250, -650);
    node.link('Top/3D_Set_peg', 0, pegPath, 0);
    node.setTextAttr(pegPath, "ENABLE_3D", 1, true);
    node.setTextAttr(pegPath, "position.separate",  1, "Off");

    if (pegPath) {
        node.setTextAttr(pegPath, "POSITION.X", 1, tx);
        node.setTextAttr(pegPath, "POSITION.Y", 1, ty);
        node.setTextAttr(pegPath, "POSITION.Z", 1, tz);

        node.setTextAttr(pegPath, "ROTATION.ANGLEX", 1, rx);
        node.setTextAttr(pegPath, "ROTATION.ANGLEY", 1, ry);
        node.setTextAttr(pegPath, "ROTATION.ANGLEZ", 1, rz);

        node.setTextAttr(pegPath, "SCALE.X", 1, sx);
        node.setTextAttr(pegPath, "SCALE.Y", 1, sy);
        node.setTextAttr(pegPath, "SCALE.Z", 1, sz);

        return pegPath;
    } else {
        MessageBox.critical("Failed to create Peg.");
        return null;
    }
}

function addOrthoLock(pegPath) {
    var orthoLockPath = node.add("Top", pegPath + "_OrthoLock", "ORTHOLOCK", 0, 0, 0);
    node.setCoord(orthoLockPath, 1250, -625);

    if (orthoLockPath) {
        node.link(pegPath, 0, orthoLockPath, 0);
        return orthoLockPath;
    } else {
        MessageBox.critical("Failed to create OrthoLock.");
        return null;
    }
}

/*
* Main interface and processing function
*/

function ImportMayaObjWindow()
{
    var self = this;

    self.onBrowsePressed = function()
    {
        self.txt_filepath.text = FileDialog.getOpenFileName();
    }

    self.onReadPressed = function()
    {
        var ktvCmdRegExp = new RegExp(/^\tsetAttr (?:-s \d{1,4} )?\".ktv\[\d{1,4}(?::\d{1,4})?\]\"\s+/);

        var file = new File(self.txt_filepath.text);
        file.open(FileAccess.ReadOnly);

        /*
        * The main loop has 3 steps:
        * 1. Look for createNode transform command, find out the main object name.
        * 2. Look for createNode animgraph command, which tells the attribute name.
        * 3. Look for sub commands that contain animation key values, then repeat step 2 for other attributes.
        */
        var firstTx;
        var channel;
        var ktvArrayString;

        // Iteration-related variables
        var line;
        var step = 0;
        var wasReadAhead = false;

        while (!file.eof)
        {
            // Some steps need to read ahead. This flag indicates that the line was already read.
            if (!wasReadAhead)
            {
                line = readFullCommand(file);
            }
            else
            {
                wasReadAhead = false;
            }

            switch (step)
            {
                case 0:
                    firstTx = extractNodeNameFromCommand(line, "transform");
                    if (firstTx)
                    {
                        self.txt_objName.text = firstTx;
                        step++;
                    }
                    break;

                case 1:
                    var nodeName = extractNodeNameFromCommand(line);
                    if (!nodeName)
                    {
                        break;
                    }

                    var nodeNameTokens = nodeName.split("_");
                    channel = nodeNameTokens[nodeNameTokens.length - 1];
                    if (channel)
                    {
                        step++;
                    }
                    break;

                case 2:
                    if (line.search(/^\t\w/) != 0)
                    {
                        wasReadAhead = true;
                        step--;
                        break;
                    }

                    var match_list = line.match(ktvCmdRegExp);

                    if (match_list)
                    {
                        // Get string of tuples of animation keys, removing trailing characters.
                        ktvArrayString = line.slice(match_list[0].length, line.length - 2);
                        ktvArrayString = ktvArrayString.replace(/[\s\t]+/g, " ");

                        switch (channel)
                        {
                            case "translateX":
                                self.txt_translate_x.text = ktvArrayString;
                                break;
                            case "translateY":
                                self.txt_translate_y.text = ktvArrayString;
                                break;
                            case "translateZ":
                                self.txt_translate_z.text = ktvArrayString;
                                break;
                            case "rotateX":
                                self.txt_rotate_x.text = ktvArrayString;
                                break;
                            case "rotateY":
                                self.txt_rotate_y.text = ktvArrayString;
                                break;
                            case "rotateZ":
                                self.txt_rotate_z.text = ktvArrayString;
                                break;
                            case "scaleX":
                                self.txt_scale_x.text = ktvArrayString;
                                break;
                            case "scaleY":
                                self.txt_scale_y.text = ktvArrayString;
                                break;
                            case "scaleZ":
                                self.txt_scale_z.text = ktvArrayString;
                                break;
                            case "focalLength":
                                self.txt_focal_length.text = ktvArrayString;
                                break;
                            case "horizontalFilmAperture":
                                self.txt_aperture.text = ktvArrayString;
                                break;
                        }

                        step--;
                    }
                    break;
            }
        }

        file.close();
    }

    self.onOkPressed = function()
    {
        // Array.reduce() will run this function for every element of the array
        function parseFrameValues(value_list, value, index)
        {
            if (index % 2)
            {
                value_list.push(parseFloat(value));
            }
            return value_list;
        }

        var XlocArray = self.txt_translate_x.text.split(" ").reduce(parseFrameValues, []);
        var YlocArray = self.txt_translate_y.text.split(" ").reduce(parseFrameValues, []);
        var ZlocArray = self.txt_translate_z.text.split(" ").reduce(parseFrameValues, []);
        var XrotArray = self.txt_rotate_x.text.split(" ").reduce(parseFrameValues, []);
        var YrotArray = self.txt_rotate_y.text.split(" ").reduce(parseFrameValues, []);
        var ZrotArray = self.txt_rotate_z.text.split(" ").reduce(parseFrameValues, []);
        var XsizeArray = self.txt_scale_x.text.split(" ").reduce(parseFrameValues, []);
        var YsizeArray = self.txt_scale_y.text.split(" ").reduce(parseFrameValues, []);
        var ZsizeArray = self.txt_scale_z.text.split(" ").reduce(parseFrameValues, []);
        var focalArray = self.txt_focal_length.text.split(" ").reduce(parseFrameValues, []);
        var camApArray = self.txt_aperture.text.split(" ").reduce(parseFrameValues, []);

        // Check that xyz locations or rotations have the same number of data points.
        if ((XlocArray.length != YlocArray.length ||
            YlocArray.length != ZlocArray.length) ||
            (XrotArray.length != YrotArray.length ||
            YrotArray.length != ZrotArray.length) ||
            (XsizeArray.length != YsizeArray.length ||
            YsizeArray.length != ZsizeArray.length))
        {
            MessageBox.information("If you want to bring in location or rotation information, you must copy over all data of x, y, and z.");
            return;
        }

        // Function to create keyframe paths from arrays
        function makeKeys(pathName, propX, propY, propZ)
        {
            for (var i = 0; i < propX.length; i++)
            {
                func.addKeyFramePath3d(pathName, i + 1, propX[i], propY[i], propZ[i], 0, 0, 0);
            }
        }

        // Create column and input keyframes.
        if (XlocArray.length > 0)
        {
            var locColName = self.txt_objName.text + "Path";
            column.add(locColName, "3DPATH");
            makeKeys(locColName, XlocArray, YlocArray, ZlocArray);
        }
        if (XrotArray.length > 0)
        {
            var rotColName = self.txt_objName.text + "Rot";
            column.add(rotColName, "QUATERNIONPATH");
            makeKeys(rotColName, XrotArray, YrotArray, ZrotArray);
        }
        // Cherie need size as Bezier?
        if (XsizeArray.length > 0)
        {
            var sizeColName = self.txt_objName.text + "Size x";
            //column.add(sizeColName, "3DPATH");
            //makeKeys(sizeColName, XsizeArray, YsizeArray, ZsizeArray);
            column.add(sizeColName, "BEZIER");
            for (var i = 0; i < XsizeArray.length; i++)
            {
                func.setBezierPoint(sizeColName, i + 1, XsizeArray[i], 0, 0, 0, 0, true, "STRAIGHT");
            }
        }
        if (YsizeArray.length > 0)
        {
            var sizeColName = self.txt_objName.text + "Size y";
            //column.add(sizeColName, "3DPATH");
            //makeKeys(sizeColName, XsizeArray, YsizeArray, ZsizeArray);
            column.add(sizeColName, "BEZIER");
            for (var i = 0; i < YsizeArray.length; i++)
            {
                func.setBezierPoint(sizeColName, i + 1, YsizeArray[i], 0, 0, 0, 0, true, "STRAIGHT");
            }
        }
        if (ZsizeArray.length > 0)
        {
            var sizeColName = self.txt_objName.text + "Size z";
            //column.add(sizeColName, "3DPATH");
            //makeKeys(sizeColName, XsizeArray, YsizeArray, ZsizeArray);
            column.add(sizeColName, "BEZIER");
            for (var i = 0; i < ZsizeArray.length; i++)
            {
                func.setBezierPoint(sizeColName, i + 1, ZsizeArray[i], 0, 0, 0, 0, true, "STRAIGHT");
            }
        }

        //    New function to convert Focal Distance and Aperture into FOV
        var userFocal = self.txt_objName.text + "FOV";
        var pi = Math.PI;
        var aspect = scene.defaultResolutionX() / scene.defaultResolutionY();
        function FOV(CamAp, FocLen){
            var CamApMM = CamAp * 25.4; // converts inches to mm
            var xrad = (Math.atan(((CamApMM / aspect) / 2) / FocLen)) * 2;  // calculates Angle of View
            var AngleOfView = xrad * 180 / pi;  // converts radians to degrees
            return AngleOfView;
        }

        var FOVArray = [];
        // Populate FOVArray if there is enough data present
        if (focalArray.length == camApArray.length)
        {
            for (var i = 0; i < focalArray.length; i++)
            {
                FOVArray.push(FOV(camApArray[i], focalArray[i]));
            }
        }
        else
        {
            MessageBox.information("You need to copy both Focal Length and Horizontal Film Aperture to get an accurate camera FOV");
        }

        // Create FOV column as Bezier type.
        if (FOVArray.length > 0)
        {
            column.add(userFocal, "BEZIER");
            for (var i = 0; i < FOVArray.length; i++)
            {
                func.setBezierPoint(userFocal, i + 1, FOVArray[i], 0, 0, 0, 0, true, "STRAIGHT");
            }
        }
    }

    // Create a new setup peg/Orthoblock with locator infos
    self.CreateNodePressed = function()
    {
        onOkPressed();

    var name = txt_objName.text;

    var peg = createPegNode(name, 0, 0, 0, 0, 0, 0, 1, 1, 1);
    if (!peg) {
        return;
    }

    // Auto-link les colonnes
    var posCol = name + "Path";
    if (column.type(posCol) == "3DPATH") {
        node.linkAttr(peg, "POSITION.3DPATH", posCol);
    }

    var rotCol = name + "Rot";
    if (column.type(rotCol) == "QUATERNIONPATH") {
        node.linkAttr(peg, "ROTATION.QUATERNIONPATH", rotCol);
    }

    // FOV (optionnel) – tu peux faire un lien ici si besoin
    var fov = name + "FOV";
    if (column.type(fov) == "BEZIER") {
        MessageLog.trace("FOV column exists: " + fov);
    }

    var scaleXCol = name + "Size x";
    if (column.type(scaleXCol) == "BEZIER") {
        node.linkAttr(peg, "SCALE.X", scaleXCol);
    }

    var scaleYCol = name + "Size y";
    if (column.type(scaleYCol) == "BEZIER") {
        node.linkAttr(peg, "SCALE.Y", scaleYCol);
    }

    var scaleZCol = name + "Size z";
    if (column.type(scaleZCol) == "BEZIER") {
        node.linkAttr(peg, "SCALE.Z", scaleZCol);
    }

    addOrthoLock(peg);

    MessageBox.information("Peg successfully created and filled.");
}

    self.create = function()
    {
        /*
        Declare all widgets
        */
        self.ui = new Dialog;
        self.title = "paste Maya data";

        self.txt_filepath = new LineEdit();
        self.txt_filepath.label = "";

        self.btn_browse = new Button();
        self.btn_browse.label = "Browse";
        self.btn_browse.callback = "onBrowsePressed";

        self.btn_read = new Button();
        self.btn_read.label = "Read";
        self.btn_read.callback = "onReadPressed";

        self.txt_objName = new LineEdit();
        self.txt_objName.label = "Object Name";

        self.txt_translate_x = new LineEdit();
        self.txt_translate_x.label = "X location";

        self.txt_translate_y = new LineEdit();
        self.txt_translate_y.label = "Y location";

        self.txt_translate_z = new LineEdit();
        self.txt_translate_z.label = "Z location";

        self.txt_rotate_x = new LineEdit();
        self.txt_rotate_x.label = "X rotation";

        self.txt_rotate_y = new LineEdit();
        self.txt_rotate_y.label = "Y rotation";

        self.txt_rotate_z = new LineEdit();
        self.txt_rotate_z.label = "Z rotation";

        self.txt_scale_x = new LineEdit();
        self.txt_scale_x.label = "X size";

        self.txt_scale_y = new LineEdit();
        self.txt_scale_y.label = "Y size";

        self.txt_scale_z = new LineEdit();
        self.txt_scale_z.label = "Z size";

        self.txt_focal_length = new LineEdit();
        self.txt_focal_length.label = "Focal Length";

        self.txt_aperture = new LineEdit();
        self.txt_aperture.label = "Horizontal Film Aperture";

        /*
        UI Layout
        */
        var grp_readfile = new GroupBox();
        grp_readfile.title = "Read from ascii file";
        grp_readfile.add(self.txt_filepath);
        grp_readfile.add(self.btn_browse);
        grp_readfile.add(self.btn_read);
        self.ui.add(grp_readfile);

        var grp_objName = new GroupBox;
        grp_objName.add(self.txt_objName);
        self.ui.add(grp_objName);

        var grp_attributes = new GroupBox;
        grp_attributes.add(self.txt_translate_x);
        grp_attributes.add(self.txt_translate_y);
        grp_attributes.add(self.txt_translate_z);
        grp_attributes.add(self.txt_rotate_x);
        grp_attributes.add(self.txt_rotate_y);
        grp_attributes.add(self.txt_rotate_z);
        grp_attributes.add(self.txt_scale_x);
        grp_attributes.add(self.txt_scale_y);
        grp_attributes.add(self.txt_scale_z);
        self.ui.add(grp_attributes);

        var grp_optional_attrs = new GroupBox;
        grp_optional_attrs.title = "Optional Attributes";
        grp_optional_attrs.add(self.txt_focal_length);
        grp_optional_attrs.add(self.txt_aperture);
        self.ui.add(grp_optional_attrs);

        // Add the new "Create Node" button to the UI, that should create all the node using maya locator informartions
        self.btn_apply = new Button();
        self.btn_apply.label = "Create and fill Peg Node";
        self.btn_apply.callback = "CreateNodePressed";
        self.ui.add(self.btn_apply);

        /*
        * Signals
        * *** Doesn't work unless you build ui via UiLoader, unfortunately.
        */
        // self.btn_browse.clicked.connect(self, self.onBrowsePressed);
        // self.btn_read.clicked.connect(self, self.onReadPressed);

        if (self.ui.exec())
        {
            self.onOkPressed();
        }
    }

    self.create();
}