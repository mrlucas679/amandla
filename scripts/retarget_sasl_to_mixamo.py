"""
retarget_sasl_to_mixamo.py — Retarget Galtis_Rig SASL animation → Mixamo T-pose skeleton
==========================================================================================
Run with:
    blender --background --python scripts/retarget_sasl_to_mixamo.py

What it does:
  1. Imports the Galtis_Rig animation (SG ASL ADHD … No Mesh Full.fbx)
     - Custom rig: Hip → Chest_1-4 → Collar/Bicep/Elbow/Forearm/Hand → fingers
     - 4.08 seconds, 60fps, 245 frames, 42,906 keyframes
     - FK + IK dual chains (we bake FK chain only)

  2. Imports a Mixamo T-pose skeleton (avatar.glb or any Mixamo FBX)
     - Namespace: mixamorig: or mixamorig2: (auto-detected)

  3. Retargets animations using Blender's NLA / constraint-based retargeting:
     - Maps Galtis bones → Mixamo bones via BONE_RETARGET_MAP
     - Bakes the result to the Mixamo skeleton as a new action

  4. Exports the Mixamo skeleton with baked SASL animation as GLB:
     - Output: assets/models/avatar_sasl_retargeted.glb
     - This file is then used by avatar.js as the signing avatar

BONE_RETARGET_MAP: Galtis_Rig → mixamorigRig
(Only the signing-relevant upper body; legs/lower body ignored)

Notes:
  - The Galtis rig has FK and IK chains in parallel. We bake the FK chain
    (Collar→Bicep→Elbow→Forearm→Hand) which drives the visual deformation.
  - Palm bones (MiddlePalm_L/R etc.) in Galtis rig have no Mixamo equivalent;
    finger root positions are absorbed into Hand bone rotation.
  - Chest_1/2/3/4 chain in Galtis → Mixamo Spine/Spine1/Spine2 (3 spine bones).
"""

import bpy
import os
import math

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR    = os.path.dirname(SCRIPT_DIR)

SASL_FBX    = os.path.join(ROOT_DIR, 'SASL DOCUMEENTS',
                           'SG ASL ADHD 1 2023-8-16 No Mesh Full.fbx')
MIXAMO_GLB  = os.path.join(ROOT_DIR, 'assets', 'models', 'avatar.glb')
OUTPUT_GLB  = os.path.join(ROOT_DIR, 'assets', 'models', 'avatar_sasl_retargeted.glb')

# ── Bone retarget map: Galtis_Rig → Mixamo ────────────────────────────────
# Format: { 'galtis_bone': 'mixamo_bone' }
# Mixamo namespace prefix auto-detected at runtime ('mixamorig:' or 'mixamorig2:')
BONE_RETARGET_MAP = {
    'Hip':       'Hips',
    'Chest_1':   'Spine',
    'Chest_2':   'Spine1',
    'Chest_4':   'Spine2',
    'Neck':      'Neck',
    'Head':      'Head',
    # Right arm (FK chain)
    'Collar_R':  'RightShoulder',
    'Bicep_R':   'RightArm',
    'Elbow_R':   'RightForeArm',
    'Forearm_R': 'RightForeArm',   # Galtis has both Elbow_R and Forearm_R
    'Hand_R':    'RightHand',
    # Right fingers
    'Thumb1_R':  'RightHandThumb1',
    'Thumb2_R':  'RightHandThumb2',
    'Thumb3_R':  'RightHandThumb3',
    'Index1_R':  'RightHandIndex1',
    'Index2_R':  'RightHandIndex2',
    'Index3_R':  'RightHandIndex3',
    'Middle1_R': 'RightHandMiddle1',
    'Middle2_R': 'RightHandMiddle2',
    'Middle3_R': 'RightHandMiddle3',
    'Ring1_R':   'RightHandRing1',
    'Ring2_R':   'RightHandRing2',
    'Ring3_R':   'RightHandRing3',
    'Pinky1_R':  'RightHandPinky1',
    'Pinky2_R':  'RightHandPinky2',
    'Pinky3_R':  'RightHandPinky3',
    # Left arm (FK chain)
    'Collar_L':  'LeftShoulder',
    'Bicep_L':   'LeftArm',
    'Elbow_L':   'LeftForeArm',
    'Forearm_L': 'LeftForeArm',
    'Hand_L':    'LeftHand',
    # Left fingers
    'Thumb1_L':  'LeftHandThumb1',
    'Thumb2_L':  'LeftHandThumb2',
    'Thumb3_L':  'LeftHandThumb3',
    'Index1_L':  'LeftHandIndex1',
    'Index2_L':  'LeftHandIndex2',
    'Index3_L':  'LeftHandIndex3',
    'Middle1_L': 'LeftHandMiddle1',
    'Middle2_L': 'LeftHandMiddle2',
    'Middle3_L': 'LeftHandMiddle3',
    'Ring1_L':   'LeftHandRing1',
    'Ring2_L':   'LeftHandRing2',
    'Ring3_L':   'LeftHandRing3',
    'Pinky1_L':  'LeftHandPinky1',
    'Pinky2_L':  'LeftHandPinky2',
    'Pinky3_L':  'LeftHandPinky3',
}


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.meshes) + list(bpy.data.armatures) + list(bpy.data.actions):
        try: block.user_clear(); bpy.data.batch_remove([block])
        except: pass


def detect_mixamo_prefix(armature):
    """Return 'mixamorig2:' if that namespace is used, else 'mixamorig:'"""
    for bone in armature.data.bones:
        if 'mixamorig2:' in bone.name:
            return 'mixamorig2:'
    return 'mixamorig:'


def get_bone(armature, name, prefix='mixamorig:'):
    """Get pose bone by name, trying both with and without namespace prefix."""
    pb = armature.pose.bones.get(name)
    if pb: return pb
    pb = armature.pose.bones.get(prefix + name)
    if pb: return pb
    # Try stripping prefix from name
    stripped = name.replace('mixamorig:', '').replace('mixamorig2:', '')
    return armature.pose.bones.get(stripped)


def retarget():
    print('\n══ AMANDLA SASL Animation Retargeter ══')

    if not os.path.exists(SASL_FBX):
        print(f'[ERROR] SASL FBX not found: {SASL_FBX}')
        return False

    # ── Step 1: Import SASL animation (Galtis_Rig) ──────────────────
    print(f'[1/4] Importing SASL animation: {os.path.basename(SASL_FBX)}')
    clear_scene()
    bpy.ops.import_scene.fbx(
        filepath             = SASL_FBX,
        global_scale         = 0.01,   # FBX cm → m
        bake_space_transform = True,
        use_anim             = True,
        automatic_bone_orientation = True,
        primary_bone_axis    = 'Y',
        secondary_bone_axis  = 'X',
        ignore_leaf_bones    = False,   # keep all finger bones
    )

    # Find Galtis armature
    galtis_arm = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            if any('Hip' in b.name or 'Chest' in b.name for b in obj.data.bones):
                galtis_arm = obj
                break

    if not galtis_arm:
        print('[ERROR] Could not find Galtis_Rig armature after import')
        return False

    print(f'  Found Galtis rig: {galtis_arm.name} ({len(galtis_arm.data.bones)} bones)')
    action_name = galtis_arm.animation_data.action.name if galtis_arm.animation_data else 'Unknown'
    print(f'  Animation: {action_name}')

    # Store reference to SASL action
    sasl_action = galtis_arm.animation_data.action if galtis_arm.animation_data else None
    if not sasl_action:
        print('[ERROR] No animation action found in Galtis rig')
        return False

    frame_start = int(sasl_action.frame_range[0])
    frame_end   = int(sasl_action.frame_range[1])
    print(f'  Frames: {frame_start}–{frame_end} ({frame_end - frame_start + 1} frames)')

    # ── Step 2: Import Mixamo target skeleton ────────────────────────
    print(f'\n[2/4] Importing Mixamo target: {os.path.basename(MIXAMO_GLB)}')

    if not os.path.exists(MIXAMO_GLB):
        print(f'  [WARN] avatar.glb not found at {MIXAMO_GLB}')
        print('  Falling back: extracting Galtis animation as-is for direct use...')
        _export_galtis_direct(galtis_arm, frame_start, frame_end)
        return True

    bpy.ops.import_scene.gltf(filepath=MIXAMO_GLB)

    mixamo_arm = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj != galtis_arm:
            mixamo_arm = obj
            break

    if not mixamo_arm:
        print('[ERROR] Could not find Mixamo armature in avatar.glb')
        return False

    prefix = detect_mixamo_prefix(mixamo_arm)
    print(f'  Mixamo rig: {mixamo_arm.name}, namespace prefix: "{prefix}"')

    # ── Step 3: Retarget using Copy Rotation constraints ─────────────
    print('\n[3/4] Retargeting animation...')

    bpy.context.view_layer.objects.active = mixamo_arm
    mixamo_arm.select_set(True)

    # Set scene frame range
    bpy.context.scene.frame_start = frame_start
    bpy.context.scene.frame_end   = frame_end
    bpy.context.scene.render.fps  = 60

    # Add Copy Rotation constraints to each mapped Mixamo bone
    constraints_added = 0
    for galtis_bone_name, mixamo_bone_suffix in BONE_RETARGET_MAP.items():
        mixamo_bone = get_bone(mixamo_arm, prefix + mixamo_bone_suffix, prefix)
        if not mixamo_bone:
            continue
        galtis_pose_bone = galtis_arm.pose.bones.get(galtis_bone_name)
        if not galtis_pose_bone:
            continue

        cns = mixamo_bone.constraints.new('COPY_ROTATION')
        cns.name    = f'RETARGET_{galtis_bone_name}'
        cns.target  = galtis_arm
        cns.subtarget = galtis_bone_name
        cns.mix_mode  = 'REPLACE'
        cns.owner_space  = 'LOCAL'
        cns.target_space = 'LOCAL'
        constraints_added += 1

    print(f'  Constraints applied: {constraints_added}/{len(BONE_RETARGET_MAP)}')

    # ── Bake constraints to keyframes ─────────────────────────────────
    bpy.context.view_layer.objects.active = mixamo_arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='SELECT')

    bpy.ops.nla.bake(
        frame_start     = frame_start,
        frame_end       = frame_end,
        only_selected   = False,
        visual_keying   = True,
        clear_constraints = True,
        clear_parents   = False,
        use_current_action = True,
        bake_types      = {'POSE'},
    )
    bpy.ops.object.mode_set(mode='OBJECT')
    print('  Bake complete.')

    # ── Step 4: Export as GLB ─────────────────────────────────────────
    print(f'\n[4/4] Exporting: {os.path.basename(OUTPUT_GLB)}')

    # Select only Mixamo objects for export
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj != galtis_arm and obj.name != galtis_arm.name:
            obj.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath              = OUTPUT_GLB,
        export_format         = 'GLB',
        use_selection         = True,
        export_animations     = True,
        export_frame_range    = True,
        export_frame_step     = 1,
        export_force_sampling = True,
        export_skins          = True,
        export_morph          = True,
        export_def_bones      = True,
        export_optimize_animation_size = True,
        export_materials      = 'EXPORT',
    )

    size_kb = os.path.getsize(OUTPUT_GLB) / 1024 if os.path.exists(OUTPUT_GLB) else 0
    print(f'[OK] {OUTPUT_GLB} ({size_kb:.0f} KB)')
    print('\n[Done] Use window.AMANDLA_CONFIG.avatarUrl = "assets/models/avatar_sasl_retargeted.glb"')
    return True


def _export_galtis_direct(galtis_arm, frame_start, frame_end):
    """Fallback: export the Galtis rig directly as GLB for inspection."""
    out = os.path.join(os.path.dirname(OUTPUT_GLB), 'avatar_galtis_direct.glb')
    bpy.ops.export_scene.gltf(
        filepath              = out,
        export_format         = 'GLB',
        use_selection         = False,
        export_animations     = True,
        export_frame_range    = True,
        export_skins          = True,
        export_def_bones      = True,
    )
    print(f'[OK] Galtis rig exported directly to: {out}')


# ── Run ───────────────────────────────────────────────────────────────────
retarget()