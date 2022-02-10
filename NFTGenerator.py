import bpy
import json
import os
import random

def create_material_collections(mat_name):
    col = []
    for material in bpy.data.materials:
        if str(mat_name) in material.name:
            col.append(material)
    return col

### DATA ###
# material collections
BODY_MAT_COL = create_material_collections("Body")
ACCESSORY_MAT_COL = create_material_collections("Accessory")
EYE_MAT_COL = create_material_collections("Eye")
# procedural generation
HEAD_COL_SIZE = 5
ARM_COL_SIZE = 5
LEG_COL_SIZE = 5
EYELID_COL_SIZE = 5
EYE_COL_SIZE = 5
PATTERN_COL_SIZE = len(BODY_MAT_COL)
COLOR_COL_SIZE = 13

# render settings
CURRENT_TASK = 0 # 0 for data generation, 1 for rendering (probably best to split these into different files later on and remove this)
CURRENT_RENDER = 1 # Should set the position of which JSON object we are rendering
END_POINT_DATA = 1000 # How many data sets to generate this session
START_POINT_RENDER = 0 # Which data to begin with for a new session of renders

# scene
scene = bpy.context.scene
scene.render.image_settings.file_format = 'PNG'

DNA_FILE_PATH = "" # path to put your dna file
color_combinations_file_path = "" # input file of the color palette you want

# OUTPUT
OUTPUT_SIZE = 1000
RENDER_BATCH_SIZE = 2
RENDER_TIME_IN_SEC = 195


DNABank = [HEAD_COL_SIZE, ARM_COL_SIZE, LEG_COL_SIZE, EYELID_COL_SIZE,  EYE_COL_SIZE, PATTERN_COL_SIZE, COLOR_COL_SIZE] 

def get_collections_parts_children():
    col_list = []
    collection = bpy.data.collections['Parts'].children
    for sub_collection in collection:
        col_list.append(sub_collection)
    return col_list

### DNA GENERATION ###
def generate_one_dna():
    dna = []
    for element_size in DNABank:
        dna.append(random_generate(0, element_size))
    # Eye, should match EyeLid, eye is index 4, eyelid 3
    dna[4] = dna[3]
    return dna

def generate_dna_data(size):
    dna_dict = {}
    while len(dna_dict) < size:
        dna_dict[tuple(generate_one_dna())] = 1
    dna_list = list(dna_dict.keys())
    return dna_list
        
def apply_mat_to_part_recursive(object, dna):
        
    if "STATIC_MAT" in object.name:
        return
    
    if "Eyeball" in object.name:
        object.data.materials[0] = EYE_MAT_COL[dna[5]]
        colorRamp = object.data.materials[0].node_tree.nodes['ColorRamp'].color_ramp
        colorRamp.elements[1].color = hex_to_rgb(int(colorCombinations['colors'][dna[6]]['Color 1'], 16))
        colorRamp.elements[2].color = hex_to_rgb(int(colorCombinations['colors'][dna[6]]['Color 2'], 16))
            
    elif object.material_slots:
        object.data.materials[0] = ACCESSORY_MAT_COL[dna[5]]
        if object.data.materials[0].node_tree.nodes['ColorRamp'].color_ramp:
            colorRamp = object.data.materials[0].node_tree.nodes['ColorRamp'].color_ramp
            colorRamp.elements[0].color = hex_to_rgb(int(colorCombinations['colors'][dna[6]]['Color 1'], 16))
            colorRamp.elements[1].color = hex_to_rgb(int(colorCombinations['colors'][dna[6]]['Color 2'], 16))

    for child in object.children:      
        apply_mat_to_part_recursive(child, dna)

def configure_character(dna):
    body = bpy.data.objects['Body']
    body.data.materials[0] = BODY_MAT_COL[dna[5]]
    colorRamp = body.data.materials[0].node_tree.nodes['ColorRamp'].color_ramp
    colorRamp.elements[0].color = hex_to_rgb(int(colorCombinations['colors'][dna[6]]['Color 1'], 16))
    colorRamp.elements[1].color = hex_to_rgb(int(colorCombinations['colors'][dna[6]]['Color 2'], 16))
    
    for part_index, part in enumerate(bpy.data.collections['Parts'].children):
        for m, n in enumerate(part.children):
            if m == dna[part_index]:
                if m <= 4:    
                    for object in n.all_objects:
                        apply_mat_to_part_recursive(object, dna)
                        
def generate():
    # procedurally generate dna and store it in file for rendering
    dna = generate_dna_data(OUTPUT_SIZE)
    dna_data = json.dumps(dna)
    write_json_to_file(dna_data, DNA_FILE_PATH)

### RENDERING ###

def hide_all_items():
    for item in bpy.data.collections['Parts'].children:
        for variation in item.children:
            variation.hide_render = True
            
def unhide_dna_items(dna_code):
    for part_index, part in enumerate(bpy.data.collections['Parts'].children):
        for m, n in enumerate(part.children):
            if m == dna_code[part_index]: 
                n.hide_render = False
        if part_index == 5: # ignore color as it is not a part
            break

def render_image():
    renderedImage = bpy.ops.render.render(write_still = 1, use_viewport = True)
    
    
### HELPER ### 
def random_generate(p, q):
    return random.choice(range(p, q))

def srgb_to_linearrgb(c):
    if   c < 0:       return 0
    elif c < 0.04045: return c/12.92
    else:             return ((c+0.055)/1.055)**2.4

def hex_to_rgb(h,alpha=1):
    r = (h & 0xff0000) >> 16
    g = (h & 0x00ff00) >> 8
    b = (h & 0x0000ff)
    return tuple([srgb_to_linearrgb(c/0xff) for c in (r,g,b)] + [alpha])

def load_json_to_dict(json_file):
    with open(json_file, encoding = 'utf-8-sig') as json_file:
        data = json.load(json_file)
        return data
    
def write_json_to_file(json, file):
    with open(file, 'w') as out_file:
        out_file.write(json + '\n')
    
# MAIN

colorCombinations = load_json_to_dict(color_combinations_file_path)

# get all parts as procedural elements
partList = get_collections_parts_children()

# generate data, comment out when rendering
# generate()

# render result
generated_dna = load_json_to_dict(DNA_FILE_PATH)
id = 877
end_id = id + RENDER_BATCH_SIZE 
def run_x_times():
    global id
    
    scene.render.filepath = "" + str(id)  # path to folder of where you want put all the final renders
    
    # construct subject
    configure_character(generated_dna[id - 1])

    # clean up the scene and un hide items relevant to the archetype
    hide_all_items()
    unhide_dna_items(generated_dna[id - 1])

    render_image()
    
    id += 1
    
    if id >= end_id:
        return None
    return RENDER_TIME_IN_SEC
bpy.app.timers.register(run_x_times)

