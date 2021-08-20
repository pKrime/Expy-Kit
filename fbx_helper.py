from io_scene_fbx import parse_fbx
from io_scene_fbx.fbx_utils import FBX_KTIME
from io_scene_fbx.import_fbx import elem_find_first


def get_fbx_local_time(filepath):
    try:
        elem_root, version = parse_fbx.parse(filepath)
    except Exception as e:
        # can't read
        return

    takes = elem_find_first(elem_root, b'Takes')
    local_time = None
    for take in takes:
        for elem in take:
            try:
                local_time = elem_find_first(elem, b'ReferenceTime')
            except (KeyError, AttributeError):
                continue
            if local_time:
                break

    if local_time:
        return local_time.props


def convert_from_fbx_duration(start, end):
    return (end - start)/FBX_KTIME

