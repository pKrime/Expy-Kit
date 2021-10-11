import unreal
try:
    from . import bone_mapping
except ImportError:
    import sys
    import os
    parent_path = os.path.dirname(__file__)
    if parent_path not in sys.path:
        sys.path.append(parent_path)
    import bone_mapping


def add_bone_mapping(container, source=bone_mapping.UnrealSkeleton(), target=bone_mapping.RigifySkeleton()):
    rig_map = source.conversion_map(target)
    for k, v in rig_map.items():
        rig_map[k] = v.replace(".", "_")

    container.set_editor_property('source_to_target', rig_map)


def map_selected():
    assets = unreal.EditorUtilityLibrary.get_selected_assets()
    for asset in assets:
        if asset.get_class().get_name() != "NodeMappingContainer":
            continue
        add_bone_mapping(asset)


if __name__ == "__main__":
    map_selected()
