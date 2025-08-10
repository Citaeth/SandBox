Small tool to update EXRs from an Harmony project. 
Harmony always output the layers channels as RGBA, even if we need only a alone channel mask. 
On heavy shots, Nuke reach really easly the 1023channels limits, so we need to update the EXRs to reduce the channels count.
It was also the occasion to do a first try of multithreading library in python, that allow us to divide by 3 the process time.
First, the request was to create the whole script in BatchScript, and we changed it to a simple batch lunch script calling a python one.

Tool step:
- CHeck the last no-omit version for select shot version in ShotGrid
- Recreate the Harmony Project (necessary step to follow the pipeline publish process after editing the EXRs)
- For each layers on the selected versionm, we want to analyse and store all EXRs info using OpenImageIO,
  to identify which channel should be kept, deleted or change into a channel only `.mask`.
- still using OIIO library, we edit and rewrite the layer that we need, and simply copy the unchanged ones.
- Publish on SG the new version of the Layers as a new Harmony publish. 
