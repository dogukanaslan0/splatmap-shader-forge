bl_info = {
    "name": "Splatmap Shader Forge PRO",
    "author": "Dogukan",
    "version": (2, 5),
    "blender": (4, 3, 0),
    "location": "Properties > Material Tab",
    "description": "Generate shaders, create alpha masks, preview and paint – all in one panel.",
    "category": "Material",
}

from . import forge_pro_2_5

def register():
    forge_pro_2_5.register()

def unregister():
    forge_pro_2_5.unregister()
