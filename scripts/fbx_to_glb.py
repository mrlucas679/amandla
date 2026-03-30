"""
fbx_to_glb.py — Convert FBX skeleton files → GLB for Three.js
==============================================================
Usage (requires Blender 3.3+):
    blender --background --python scripts/fbx_to_glb.py

Output:
    assets/models/avatar.glb        ← primary (human_signing.fbx)
    assets/models/avatar_sasl.glb   ← secondary (SG ASL ADHD skeleton)

The primary avatar.glb is loaded by avatar.js via AvatarDriver / GLTFLoader.
"""

import bpy
import os
import sys

# ── Paths ─────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR    = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR  = os.path.join(ROOT_DIR, 'assets', 'models')

SOURCES = [
    {
        'fbx':    os.path.join(ROOT_DIR, 'src', 'windows', 'deaf', 'human_signing.fbx'),
        'out':    'avatar.glb',           # primary — loaded by default
        'scale':  1.0,
    },
    {
        'fbx':    os.path.join(ROOT_DIR, 'SASL DOCUMEENTS', 'SG ASL ADHD 1 2023-8-16 No Mesh Full.fbx'),
        'out':    'avatar_sasl.glb',      # SASL skeleton reference
        'scale':  0.01,                   # FBX cm → m
    },
]

os.makedirs(OUTPUT_DIR, exist_ok=True)


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:     bpy.data.meshes.remove(block)
    for block in bpy.data.armatures:  bpy.data.armatures.remove(block)
    for block in bpy.data.materials:  bpy.data.materials.remove(block)


def import_fbx(fbx_path, global_scale=1.0):
    """Import FBX with settings tuned for Mixamo-style rigs."""
    bpy.ops.import_scene.fbx(
        filepath              = fbx_path,
        global_scale          = global_scale,
        bake_space_transform  = True,     # apply axis correction bake
        use_custom_normals    = True,
        use_image_search      = True,
        use_anim              = True,
        anim_offset           = 1.0,
        use_subsurf           = False,
        use_custom_props      = True,
        ignore_leaf_bones     = True,     # removes Mixamo leaf end-bones
        force_connect_children= False,
        automatic_bone_orientation = True,
        primary_bone_axis     = 'Y',
        secondary_bone_axis   = 'X',
        use_prepost_rot       = True,
    )


def export_glb(output_path):
    """Export selected objects as GLB with skins + morph targets."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath                    = output_path,
        export_format               = 'GLB',
        use_selection               = True,
        export_apply                = False,
        export_animations           = True,
        export_frame_range          = True,
        export_frame_step           = 1,
        export_force_sampling       = True,
        export_nla_strips           = True,
        export_def_bones            = True,         # include deformation bones
        export_optimize_animation_size = True,
        export_skins                = True,          # armature / skeleton
        export_morph                = True,          # blendshapes for NMMs
        export_morph_normal         = True,
        export_morph_tangent        = False,
        export_lights               = False,
        export_cameras              = False,
        export_materials            = 'EXPORT',
        export_colors               = True,
        export_texcoords            = True,
        export_normals              = True,
        export_tangents             = False,
        export_image_format         = 'AUTO',
    )


def convert(source):
    fbx_path = source['fbx']
    out_name = source['out']
    scale    = source.get('scale', 1.0)

    if not os.path.exists(fbx_path):
        print(f'[SKIP] FBX not found: {fbx_path}')
        return False

    print(f'\n[CONVERT] {os.path.basename(fbx_path)}  →  {out_name}')

    clear_scene()
    import_fbx(fbx_path, global_scale=scale)

    output_path = os.path.join(OUTPUT_DIR, out_name)
    export_glb(output_path)

    size_kb = os.path.getsize(output_path) / 1024 if os.path.exists(output_path) else 0
    print(f'[OK]  {output_path}  ({size_kb:.0f} KB)')
    return True


# ── Run ───────────────────────────────────────────────────────────────
print('\n══ AMANDLA FBX→GLB Converter ══')
for src in SOURCES:
    convert(src)

print('\n[Done] GLB files written to assets/models/')
print('       Set window.AMANDLA_CONFIG.avatarUrl = "assets/models/avatar.glb" to use custom path.')