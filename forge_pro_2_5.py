bl_info = {
    "name": "Splatmap Shader Forge PRO",
    "author": "Doğukan & ChatGPT",
    "version": (2, 5),
    "blender": (4, 3, 0),
    "location": "Properties > Material Tab",
    "description": "Generate shaders, create alpha masks, preview and paint – all in one panel.",
    "category": "Material",
}

import bpy
from bpy.props import IntProperty, StringProperty, FloatVectorProperty, EnumProperty
import os

def create_shader_forge(count):
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        return

    mat = bpy.data.materials.new("Splatmap_Material")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (count * 300 + 600, 0)

    splatmap_nodes = []
    for i in range(count):
        x = i * 300
        splat = nodes.new("ShaderNodeTexImage")
        splat.label = f"Splatmap_{i+1}"
        splat.name = f"Splatmap_{i+1}"
        splat.location = (x, 1000)
        splatmap_nodes.append(splat)

    frame = nodes.new("NodeFrame")
    frame.label = "ALPHA MAPS"
    frame.name = "ALPHA MAPS"
    frame.label_size = 20
    frame.location = (0, 950)

    for node in splatmap_nodes:
        node.parent = frame

    prev_shader = None
    for i in range(count):
        y = -i * 300
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (-1000, y)

        if i == 0:
            prev_shader = bsdf
        else:
            mix = nodes.new("ShaderNodeMixShader")
            mix.location = (-600 + i * 400, 0)
            links.new(prev_shader.outputs[0], mix.inputs[1])
            links.new(bsdf.outputs[0], mix.inputs[2])
            links.new(splatmap_nodes[i].outputs["Color"], mix.inputs[0])
            prev_shader = mix

    links.new(prev_shader.outputs[0], output.inputs["Surface"])

    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

def get_fac_linked_images():
    obj = bpy.context.active_object
    if not obj or not obj.active_material or not obj.active_material.use_nodes:
        return []
    images = []
    for node in obj.active_material.node_tree.nodes:
        if node.type == 'MIX_SHADER':
            fac = node.inputs.get("Fac")
            if fac and fac.is_linked:
                from_node = fac.links[0].from_node
                if from_node.type == 'TEX_IMAGE':
                    images.append(from_node)
    return images

class SSF_OT_GenerateImages(bpy.types.Operator):
    bl_idname = "ssf.generate_images"
    bl_label = "Generate Images"

    def execute(self, context):
        scn = context.scene
        w, h = scn.ssf_img_width, scn.ssf_img_height
        col, typ = scn.ssf_img_color, scn.ssf_img_type
        for node in get_fac_linked_images():
            img = bpy.data.images.new(name=node.name, width=w, height=h, alpha=True, float_buffer=False)
            img.generated_type = typ
            img.generated_color = col
            img.update()
            node.image = img
        self.report({'INFO'}, "Images created.")
        return {'FINISHED'}

class SSF_OT_SaveImages(bpy.types.Operator):
    bl_idname = "ssf.save_images"
    bl_label = "Save Images"

    def execute(self, context):
        path = bpy.path.abspath(context.scene.ssf_img_save_path)
        count = 0
        for node in get_fac_linked_images():
            img = node.image
            if img:
                filepath = os.path.join(path, f"{img.name}.png")
                img.filepath_raw = filepath
                img.file_format = 'PNG'
                img.save()
                count += 1
        self.report({'INFO'}, f"{count} image(s) saved.")
        return {'FINISHED'}

class SSF_OT_SetImagePaint(bpy.types.Operator):
    bl_idname = "ssf.set_image_paint"
    bl_label = "Start Painting"
    image_name: StringProperty()

    def execute(self, context):
        img = bpy.data.images.get(self.image_name)
        if not img:
            self.report({'ERROR'}, "Image not found.")
            return {'CANCELLED'}

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object.")
            return {'CANCELLED'}

        if not obj.data.uv_layers:
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.uv.smart_project()
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.mode_set(mode='TEXTURE_PAINT')

        found_editor = False
        for area in context.window.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                for space in area.spaces:
                    if space.type == 'IMAGE_EDITOR':
                        space.image = img
                        found_editor = True
                        break

        if not found_editor:
            self.report({'WARNING'}, "No Image Editor area found.")
        else:
            self.report({'INFO'}, f"{img.name} ready for painting.")
        return {'FINISHED'}

class SSF_PT_MainPanel(bpy.types.Panel):
    bl_label = "Splatmap Shader Forge PRO"
    bl_idname = "SSF_PT_MainPanel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"

    def draw(self, context):
        l = self.layout
        scn = context.scene

        l.label(text="1. Build Shader")
        l.prop(scn, "ssf_layer_count")
        l.operator("ssf.build_shader", icon='NODE_MATERIAL')

        l.separator()
        l.label(text="2. Generate Masks")
        l.prop(scn, "ssf_img_width")
        l.prop(scn, "ssf_img_height")
        l.prop(scn, "ssf_img_color")
        l.prop(scn, "ssf_img_type")
        l.operator("ssf.generate_images", icon='IMAGE_DATA')

        l.separator()
        l.label(text="3. Save & Paint")
        l.prop(scn, "ssf_img_save_path")
        l.operator("ssf.save_images", icon='FILE_TICK')

        for node in get_fac_linked_images():
            row = l.row(align=True)
            img = node.image
            if img and img.preview:
                row.template_preview(img, hide_buttons=True)
            row.label(text=node.name)
            op = row.operator("ssf.set_image_paint", text="Paint", icon='BRUSH_DATA')
            op.image_name = img.name if img else node.name

class SSF_OT_BuildShader(bpy.types.Operator):
    bl_idname = "ssf.build_shader"
    bl_label = "Build Shader"

    def execute(self, context):
        create_shader_forge(context.scene.ssf_layer_count)
        self.report({'INFO'}, "Shader created.")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(SSF_PT_MainPanel)
    bpy.utils.register_class(SSF_OT_BuildShader)
    bpy.utils.register_class(SSF_OT_GenerateImages)
    bpy.utils.register_class(SSF_OT_SaveImages)
    bpy.utils.register_class(SSF_OT_SetImagePaint)

    bpy.types.Scene.ssf_layer_count = IntProperty(name="Layers", default=4, min=1, max=12)
    bpy.types.Scene.ssf_img_width = IntProperty(name="Width", default=1024)
    bpy.types.Scene.ssf_img_height = IntProperty(name="Height", default=1024)
    bpy.types.Scene.ssf_img_color = FloatVectorProperty(name="Color", subtype='COLOR', default=(0, 0, 0, 1), size=4, min=0, max=1)
    bpy.types.Scene.ssf_img_type = EnumProperty(
        name="Type",
        items=[('BLANK', "Blank", ""), ('UV_GRID', "UV Grid", ""), ('COLOR_GRID', "Color Grid", "")],
        default='BLANK'
    )
    bpy.types.Scene.ssf_img_save_path = StringProperty(name="Save Path", subtype='DIR_PATH', default="//")

def unregister():
    bpy.utils.unregister_class(SSF_PT_MainPanel)
    bpy.utils.unregister_class(SSF_OT_BuildShader)
    bpy.utils.unregister_class(SSF_OT_GenerateImages)
    bpy.utils.unregister_class(SSF_OT_SaveImages)
    bpy.utils.unregister_class(SSF_OT_SetImagePaint)

    del bpy.types.Scene.ssf_layer_count
    del bpy.types.Scene.ssf_img_width
    del bpy.types.Scene.ssf_img_height
    del bpy.types.Scene.ssf_img_color
    del bpy.types.Scene.ssf_img_type
    del bpy.types.Scene.ssf_img_save_path

if __name__ == "__main__":
    register()
