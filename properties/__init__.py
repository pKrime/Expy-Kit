from . import retarget
from . import storage


def register_classes():
    retarget.register_classes()
    storage.register_classes()

def unregister_classes():
    retarget.unregister_classes()
    storage.unregister_classes()