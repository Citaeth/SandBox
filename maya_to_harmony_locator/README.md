Tools to send animation data from Maya to Harmony.
The first tool is a python QT script in maya, that allow you to create locator, connect them to what you want, 
and apply on them slight offset if needed. 
For exemple if we want to get the contact point of the foot on the grood, we will connect the locator to a controler, 
but this controler could be a bit offseted from the flat of the foot. 
Then an export buttom that will deal with all the scale changes between Maya and Harmony.

On harmony side, the JavaScript tool is an update of an old tool from Mike Overbeck.
It will open an UI that will allow us the load the locator ma scene we generated from maya, load the animations datas and
create a new PEG filled with this datas.
