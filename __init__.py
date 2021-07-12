# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

#  COLLECTION GROUPS
#  Collection Groups add-on for Blender 2.92+
#  (c) 2021 Andrey Sokolov (so_records)

bl_info = {
    "name": "Collection Groups",
    "author": "Andrey Sokolov",
    "version": (1, 0, 0),
    "blender": (2, 92, 0),
    "location": "3D Viewport > N-Panel > ColGr",
    "description": "Collection Groups to control Collections settings simultaneously",
    "warning": "",
    "wiki_url": "https://github.com/sorecords/collection_groups/blob/main/README.md",
    "tracker_url": "https://github.com/sorecords/collection_groups/issues",
    "category": "Collections"
}

import bpy
from bpy.types import PropertyGroup, Collection, Operator, Panel, UIList, Scene, LayerCollection
from bpy.props import CollectionProperty, PointerProperty, StringProperty, IntProperty, BoolProperty
from bpy.utils import register_class, unregister_class
from typing import List


def col_update_name(self, context):
    """Update on setting Collection"""
    sc = context.scene
    colgr = sc.colgr[sc.colgr_active]
    col = colgr.cols[colgr.cols_active]
    if col.collection is not None:
        col.name = col.collection.name


def clrg_update(self, context):
    """Update on change any Collection Group visibility settings"""
    bpy.ops.colgr.exe('INVOKE_DEFAULT')


class COLGR_Collection(PropertyGroup):
    """Collections for Collection Groups"""
    index: IntProperty(default=0)
    name: StringProperty(default="Collection")
    collection: PointerProperty(type=Collection, update=col_update_name)


class COLGR_CollectionsGroup(PropertyGroup):
    """Collection Groups Properties"""
    index: IntProperty(default=0)
    name: StringProperty(default="Collection Group")
    cols: CollectionProperty(type=COLGR_Collection)
    cols_active: IntProperty(default=0)
    enabled: BoolProperty(default=True, update=clrg_update, name="Exclude from View Layer")
    select: BoolProperty(default=True, update=clrg_update, name="Disable Selection")
    preview: BoolProperty(default=True, update=clrg_update, name="Hide in Viewport")
    viewport: BoolProperty(default=True, update=clrg_update, name="Disable in Viewports")
    render: BoolProperty(default=True, update=clrg_update, name = "Disable in Renders")


class COLGR_Slots:
    """Add/Remove Collection or Collection Group slots. Executing functions"""

    def slot_add(self, source, prop_path: str, prop_active: str):
        """Add new Collection item and UI slot"""
        props = getattr(source, prop_path)
        active = getattr(source, prop_active)
        props.add()
        index = len(props) - 1
        setattr(source, prop_active, index)
        props[index].index = index

    def slot_remove(self, source, prop_path: str, prop_active: str):
        """Remove active Collection item and UI slot"""
        props = getattr(source, prop_path)
        index = int(getattr(source, prop_active))
        props.remove(index)
        for i, ar in enumerate(props):
            ar.index = i
        setattr(source, prop_active, index - 1)


class COLGR_UL_Add(Operator, COLGR_Slots):
    """Add new Collection Group"""
    bl_idname = 'colgr.add_slot'
    bl_label = 'Add new slot'

    def invoke(self, context, event):
        bpy.ops.ed.undo_push()
        self.slot_add(context.scene, "colgr", "colgr_active")
        return {'FINISHED'}


class COLGR_UL_Remove(Operator, COLGR_Slots):
    """Remove active Collection Group"""
    bl_idname = 'colgr.remove_slot'
    bl_label = 'Remove active slot'

    def invoke(self, context, event):
        bpy.ops.ed.undo_push()
        self.slot_remove(context.scene, "colgr", "colgr_active")
        return {'FINISHED'}


class COLGR_UL_ColAdd(Operator, COLGR_Slots):
    """Add new Collection"""
    bl_idname = 'colgr.add_slot_col'
    bl_label = 'Add new slot'

    def invoke(self, context, event):
        bpy.ops.ed.undo_push()
        sc = context.scene
        source = sc.colgr[sc.colgr_active]
        self.slot_add(source, "cols", "cols_active")
        return {'FINISHED'}


class COLGR_UL_ColRemove(Operator, COLGR_Slots):
    """Remove active Collection from the active Collection Group"""
    bl_idname = 'colgr.remove_slot_col'
    bl_label = 'Remove active slot'

    def invoke(self, context, event):
        bpy.ops.ed.undo_push()
        sc = context.scene
        source = sc.colgr[sc.colgr_active]
        self.slot_remove(source, "cols", "cols_active")
        return {'FINISHED'}


class COLGR_AddLaunch(Operator):
    """Add/Remove Collections selected in the Outliner to the active Collection Group"""
    bl_idname = "colgr.add_launch"
    bl_label = "Add/Remove selected Collections from Group"
    remove_cols: BoolProperty(default=False)

    def context_override(self, context):
        window = bpy.data.window_managers[0].windows[0]
        screen = window.screen
        areas = [ar for ar in screen.areas if ar.type == "OUTLINER"]
        area = areas[0] if len(areas) else screen.areas[0]
        region = area.regions[1]
        scene = bpy.context.scene

        override = {'window': window,
                    'screen': screen,
                    'area': area,
                    'region': region,
                    'scene': scene,
                    }
        return override

    def execute(self, context):
        override = self.context_override(context)
        bpy.ops.colgr.add_selected(override, 'INVOKE_DEFAULT', remove_cols=self.remove_cols)
        return {'FINISHED'}


class COLGR_AddSelected(Operator, COLGR_Slots):
    """Add/Remove Collections selected in the Outliner to the active Collection Group"""
    bl_idname = "colgr.add_selected"
    bl_label = "Add/Remove selected Collections from Group"
    remove_cols: BoolProperty(default=False)

    def get_source_cols(self, context) -> List[Collection]:
        return [c for c in context.selected_ids if type(c) == Collection]

    def cols_in_list(self) -> List[Collection]:
        return [c.collection for c in self.colprops.cols if c.collection is not None]

    def cols_remove(self):
        print(self.colprops.cols)
        for c in self.colprops.cols:
            while c.collection in self.source_cols:
                self.colprops.cols_active = c.index
                self.slot_remove(self.colprops, "cols", "cols_active")

    def cols_add(self):
        cols_in_list = self.cols_in_list()
        for c in self.source_cols:
            if c not in cols_in_list:
                self.slot_add(self.colprops, "cols", "cols_active")
                self.colprops.cols[self.colprops.cols_active].collection = c

    def invoke(self, context, event):
        sc = context.scene
        self.colprops = sc.colgr[sc.colgr_active]
        self.source_cols = self.get_source_cols(context)
        if self.remove_cols:
            self.cols_remove()
        else:
            self.cols_add()
        return {'FINISHED'}


class COLGR_Clear(Operator, COLGR_Slots):
    """Clear active Collection Group"""
    bl_idname = "colgr.clear"
    bl_label = "Clear"

    def execute(self, context):
        sc = context.scene
        props = sc.colgr[sc.colgr_active]
        for c in props.cols:
            props.cols_active = c.index
            self.slot_remove(props, "cols", "cols_active")
        return {'FINISHED'}


class COLGR_Exe(Operator):
    """Update Collections visibility according to the \
active Collection Group settings"""
    bl_idname = "colgr.exe"
    bl_label = "Update Collections Settings"

    def get_cols(self) -> List[Collection]:
        """Get all Collection Group Collections"""
        return [c.collection for c in self.props.cols]

    def lcol_from_col(self, source: LayerCollection, c: Collection) -> LayerCollection:
        """Find Layer Collection equal to the actual Collection"""
        if source.name == c.name:
            return source
        elif not len(source.children):
            return
        else:
            for lc in source.children:
                result = self.lcol_from_col(lc, c)
                if result:
                    return result

    def get_lcols(self) -> List[LayerCollection]:
        """Get all Layer Collections equal to the actual Collections \
in the active Collection Group"""
        source = self.vl.layer_collection
        return [self.lcol_from_col(source, c) for c in self.cols]

    def update(self) -> None:
        """Set actual Collections' visibility according to the active \
Collection Group visibility"""
        for c in self.cols:
            c.hide_render = not self.props.render
            c.hide_select = not self.props.select
            c.hide_viewport = not self.props.viewport
        for lc in self.lcols:
            lc.hide_viewport = not self.props.preview
            lc.exclude = not self.props.enabled

    def execute(self, context):
        self.sc = context.scene
        self.vl = context.view_layer
        self.props = self.sc.colgr[self.sc.colgr_active]
        self.cols = self.get_cols()
        self.lcols = self.get_lcols()
        self.update()
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


class COLGR_UL_colgr(UIList):
    """Collection Groups UI List"""

    def draw_item(self, _context, layout, _data, item, icon, _active_data,
                  _active_propname, _index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon_value=icon)
            layout.label(text="", icon='GROUP')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='GROUP')


class COLGR_UL_cols(UIList):
    """Collections UI List"""

    def draw_item(self, _context, layout, _data, item, icon, _active_data,
                  _active_propname, _index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon_value=icon)
            layout.label(text="", icon='OUTLINER_COLLECTION')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='OUTLINER_COLLECTION')


class COLGR_PT_Panel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ColGr"
    bl_label = "Collection Groups"

    def draw(self, context):
        layout = self.layout
        sc = context.scene
        props = sc.colgr
        row = layout.row(align=True)
        row.template_list("COLGR_UL_colgr", "", sc, "colgr", sc, "colgr_active", rows=3)
        col = row.column()
        col.operator("colgr.add_slot", text="", icon="ADD")
        col.operator("colgr.remove_slot", text="", icon="REMOVE")
        if len(props) > 0:
            cprops = sc.colgr[sc.colgr_active]
            row = layout.row(align=True, heading="Visibility")
            row.prop(cprops, "enabled", text="",
                     icon="CHECKBOX_HLT" if cprops.enabled else "CHECKBOX_DEHLT"
                     )
            row.prop(cprops, "select", text="",
                     icon="RESTRICT_SELECT_OFF" if cprops.select
                     else "RESTRICT_SELECT_ON"
                     )
            row.prop(cprops, "preview", text="",
                     icon="HIDE_OFF" if cprops.preview else "HIDE_ON"
                     )
            row.prop(cprops, "viewport", text="",
                     icon="RESTRICT_VIEW_OFF" if cprops.viewport
                     else "RESTRICT_VIEW_ON"
                     )
            row.prop(cprops, "render", text="",
                     icon="RESTRICT_RENDER_OFF" if cprops.render
                     else "RESTRICT_RENDER_ON"
                     )
            row.separator()
            row.operator("colgr.exe", text="", icon="FILE_REFRESH")
            row = layout.row(align=True)
            ops = row.operator("colgr.add_launch", text="Add Selected", icon='ADD')
            ops.remove_cols = False
            row = layout.row(align=True)
            op = row.operator("colgr.add_launch", text="Remove Selected", icon='REMOVE')
            op.remove_cols = True
            row = layout.row(align=True)
            row.template_list("COLGR_UL_cols", "", cprops, "cols", cprops, "cols_active", rows=3)
            col = row.column()
            col.operator("colgr.add_slot_col", text="", icon="ADD")
            col.operator("colgr.remove_slot_col", text="", icon="REMOVE")
            col.operator("colgr.clear", text="", icon="X")
            if len(cprops.cols) > 0:
                col = layout.column(align=True)
                cgprops = cprops.cols[cprops.cols_active]
                col.prop(cgprops, "collection")


classes = [
    COLGR_Collection,
    COLGR_CollectionsGroup,
    COLGR_UL_Add,
    COLGR_UL_Remove,
    COLGR_UL_ColAdd,
    COLGR_UL_ColRemove,
    COLGR_Exe,
    COLGR_AddLaunch,
    COLGR_AddSelected,
    COLGR_Clear,
    COLGR_UL_colgr,
    COLGR_UL_cols,
    COLGR_PT_Panel
]


def register():
    for cl in classes:
        register_class(cl)
    Scene.colgr = CollectionProperty(type=COLGR_CollectionsGroup)
    Scene.colgr_active = IntProperty(default=0, name="Active Collection Group")


def unregister():
    for cl in reversed(classes):
        unregister_class(cl)

if __name__ == "__main__":
    register()
