
# Expy Kit
## blender addon
### switch between different types of Character Rig

[![Alt text](https://img.youtube.com/vi/pFouaNVxcso/0.jpg)](https://www.youtube.com/watch?v=pFouaNVxcso)

* Convert *Rigify* armatures to a single hierarchy for game engines
* Extract rigify metarig from rigged character
* Restore *Rigify* **.L**/**.R** naming on skeletons reimported from Unreal Engine
* Convert Bone Names to export *Rigify*/*Unreal* characters to *Mixamo*
* Connect child bones
* Enable/Disable/Remove all constraints
* Constrain bones to another armature
* Set playback range from action start/end


### How to use

Click the **Code** button and choose **Download Zip**, then install via the blender **Add-ons** preferences.

Or git-clone to your `Scripts/addons` path if u're a gangsta

Once enabled, the script will add the following entries to the pose menu (mouse right click in **pose mode**)

* Binding
    * Bind to Active Armature
    * Enable/disable constraints
    * Select Constrained Controls

* Conversion
    * Rigify Game Friendly
    * Revert dots in Names
    * Convert Bone Names
    * Extract Metarig
    * Create Scale Offset
    
* Animation
    * Action Range to Scene
    * Bake Constrained Actions
    * Rename Actions from .fbx data
    * Hips to Root Motion
    * Select Animated Controls

