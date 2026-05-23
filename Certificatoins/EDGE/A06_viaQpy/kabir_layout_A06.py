# ===============================================================================
# PACKAGES & MODULE IMPORTS
# ===============================================================================
import os
import processing
from PyQt5.QtGui import QColor, QFont
from qgis.core import (
    QgsProject,
    QgsCoordinateReferenceSystem,
    QgsPrintLayout,
    QgsLayoutItemMap,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemScaleBar,
    QgsLayoutItemPicture,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsUnitTypes,
    QgsLayoutItemMapGrid,
    Qgis,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsSingleSymbolRenderer,
    QgsLegendStyle,
    QgsLayoutExporter
)

# ===============================================================================
# USER CONFIGURATION INPUTS
# ===============================================================================
# A. Administrative Boundaries
vector_layer = "SourceDatabaseUTM — districtlged2021"   # Boundary source layer name
target_column = 'DISTRICT'                         # Administrative boundary field
value_to_match = 'Sirajganj'                            # Selected workspace value
desired_crs_authid = "EPSG:32645"                       # Mapping projection system (UTM)

# B. Filtering Criteria
expression_layer = "SourceDatabaseUTM — bdhealthfacilitiesosm2020"
filter_expression = '"Amenity" = \'hospital\' or "Aminity" = \'clinic\''

# C. Analysis Criteria (Buffers)
healthcare_buffer_km = 5
roads_buffer_km = 1

healthcare_buffer_m = healthcare_buffer_km * 1000
roads_buffer_m = roads_buffer_km * 1000

# D. File Export Paths & Layout Typography
export_folder = r"C:\Users\santo\Documents"  # Target directory location
pdf_output_path = os.path.join(export_folder, f"Sirajganj_Analysis_Report.pdf")
map_title_text = f"Spatial Access Analysis\nDistrict Workspace: {value_to_match}"

# E. Map Canvas Stylization Colors (Hex Codes)
color_district = "#f7f7f7"       # Light gray background
color_district_roads = "#a6a6a6" # Muted background gray for complete district roads
color_hc_buff = "#ffcccc"        # Soft red transparency fill
color_roads_buff = "#e6f2ff"     # Light blue accessibility zone
color_settlements = "#ffb2e0"    # Soft pink for original settlements
color_intersected = "#ff6a83"    # Vivid pink/coral for targeted served settlements
color_roads = "#1a1a1a"          # Dark charcoal for active transit paths

# ===============================================================================
# STEP 1: GLOBAL SOURCE GEOMETRY CLEANING & VERIFICATION
# ===============================================================================
print("🛠 Running preemptive geometry verification on raw panel assets...")

layers_to_validate = [
    vector_layer,
    "SourceDatabaseUTM — bdhealthfacilitiesosm2020", 
    "SourceDatabaseUTM — bdroadsusaid2021", 
    "SourceDatabaseUTM — settlementlged2020"
]

validated_source_layers = {}

for name in layers_to_validate:
    matching_layers = QgsProject.instance().mapLayersByName(name)
    if not matching_layers:
        print(f"⚠️ Warning: Could not locate map asset layer '{name}' in workspace.")
        continue
    
    raw_layer = matching_layers[0]
    
    # Run the fix geometries tool to resolve topological discrepancies early
    fix_params = {'INPUT': raw_layer, 'OUTPUT': 'TEMPORARY_OUTPUT'}
    fix_result = processing.run("native:fixgeometries", fix_params)
    clean_geo_layer = fix_result['OUTPUT']
    
    validated_source_layers[name] = clean_geo_layer

print("✅ Preemptive geometry normalization complete. Proceeding with spatial clipping operations...")


# ===============================================================================
# STEP 2: EXTRACT REQUIRED DISTRICT BOUNDARY
# ===============================================================================
print(f"📌 Isolating focus area sector boundary line framework...")
extract_parameters = {
    'INPUT': validated_source_layers[vector_layer],
    'FIELD': target_column,
    'OPERATOR': 0,
    'VALUE': value_to_match,
    'OUTPUT': 'TEMPORARY_OUTPUT'
}

extract_action = processing.run("native:extractbyattribute", extract_parameters)
extracted_boundary_layer = extract_action['OUTPUT']
extracted_boundary_layer.setName(f"Extracted ({value_to_match})")
QgsProject.instance().addMapLayer(extracted_boundary_layer)

print(f"--> Extracted features matching reference query: '{target_column}' = '{value_to_match}'")


# ===============================================================================
# STEP 3: BATCH BOUNDARY CLIPPING & HEALTH INFRASTRUCTURE FILTERING
# ===============================================================================
layers_to_clip = [
    "SourceDatabaseUTM — bdhealthfacilitiesosm2020", 
    "SourceDatabaseUTM — bdroadsusaid2021", 
    "SourceDatabaseUTM — settlementlged2020"
]

clipped_layer_objects = []
print("\n✂️ Executing localized workspace spatial subset cropping...")

for layer_name in layers_to_clip:
    if layer_name not in validated_source_layers:
        continue
        
    input_layer = validated_source_layers[layer_name]
    
    clip_parameters = {
        'INPUT': input_layer,
        'OVERLAY': extracted_boundary_layer,
        'OUTPUT': 'TEMPORARY_OUTPUT'
    }
    result = processing.run("native:clip", clip_parameters)
    output_layer = result['OUTPUT']
    
    if layer_name == expression_layer:
        expr_params = {
            'INPUT': output_layer,
            'EXPRESSION': filter_expression,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }
        expr_result = processing.run("native:extractbyexpression", expr_params)
        output_layer = expr_result['OUTPUT']
        output_layer.setName(f"{layer_name} (Filtered & Clipped)")
    else:
        output_layer.setName(f"{layer_name} (Clipped)")
        
    QgsProject.instance().addMapLayer(output_layer)
    clipped_layer_objects.append(output_layer)

print("--> Local workspace spatial subset cropping successfully processed.")


# ===============================================================================
# STEP 4: COORDINATE SYSTEM SYSTEM VALIDATION & LAYER REPROJECTION
# ===============================================================================
target_crs = QgsCoordinateReferenceSystem(desired_crs_authid)
cleaned_layers = {}

print(f"\n🌐 Checking projection parameters against standard: {desired_crs_authid}")

for layer in clipped_layer_objects:
    original_name = layer.name()
    working_layer = layer
    
    if layer.crs().authid() != desired_crs_authid:
        print(f"--> Reprojecting system metrics context: '{original_name}'...")
        reproject_params = {
            'INPUT': working_layer,
            'TARGET_CRS': target_crs,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }
        reproject_result = processing.run("native:reprojectlayer", reproject_params)
        working_layer = reproject_result['OUTPUT']
        
    clean_name = original_name.replace(" (Clipped)", " (Cleaned)").replace(" (Filtered & Clipped)", " (Filtered & Cleaned)")
    working_layer.setName(clean_name)
    QgsProject.instance().addMapLayer(working_layer)
    
    # Store clean tracking handles inside a global storage dictionary
    if "bdhealthfacilities" in original_name:
        cleaned_layers['healthcare'] = working_layer
    elif "bdroads" in original_name:
        cleaned_layers['roads_district'] = working_layer  # Static full district-wide road network asset
        cleaned_layers['roads'] = working_layer           # Dynamic layer used for subsequent analysis chains
    elif "settlement" in original_name:
        cleaned_layers['settlements'] = working_layer

print("--> Spatial reference validation checks completed safely.")


# ===============================================================================
# STEP 5: SEQUENTIAL ANALYSIS CHAIN (WITH BOUNDARY ACCESS MASKS)
# ===============================================================================
print("\n⛓ Executing mathematical buffer proximity calculation modeling...")

# A. Generate Primary Healthcare Influence Buffers (5km Zone)
print(f"1. Calculating spatial service area footprint around clinics ({healthcare_buffer_km}km)...")
hc_buffer_params = {
    'INPUT': cleaned_layers['healthcare'],
    'DISTANCE': healthcare_buffer_m,
    'SEGMENTS': 5,
    'DISSOLVE': True, 
    'OUTPUT': 'TEMPORARY_OUTPUT'
}
hc_buffer_action = processing.run("native:buffer", hc_buffer_params)
raw_healthcare_buffer = hc_buffer_action['OUTPUT']

print("   [Masking] Truncating footprint vector bounds strictly to Administrative limits...")
hc_mask_params = {
    'INPUT': raw_healthcare_buffer,
    'OVERLAY': extracted_boundary_layer,
    'OUTPUT': 'TEMPORARY_OUTPUT'
}
hc_mask_action = processing.run("native:clip", hc_mask_params)
healthcare_buffer_zone = hc_mask_action['OUTPUT']
healthcare_buffer_zone.setName(f"Healthcare {healthcare_buffer_km}km Buffer (Masked to District)")
QgsProject.instance().addMapLayer(healthcare_buffer_zone)


# B. Clip the Road Network by the Localized Healthcare Service Footprint
print("2. Mapping road corridors contained within accessible infrastructure sectors...")
road_clip_params = {
    'INPUT': cleaned_layers['roads'],
    'OVERLAY': healthcare_buffer_zone,
    'OUTPUT': 'TEMPORARY_OUTPUT'
}
road_clip_action = processing.run("native:clip", road_clip_params)
roads_clipped_by_hc = road_clip_action['OUTPUT']
roads_clipped_by_hc.setName("Roads Cleaned (Inside HC Buffer)")
QgsProject.instance().addMapLayer(roads_clipped_by_hc)


# C. Generate Secondary Proximity Buffers around Accessible Roads (1km Zone)
print(f"3. Building transit access proximity threshold envelopes ({roads_buffer_km}km)...")
road_buffer_params = {
    'INPUT': roads_clipped_by_hc,
    'DISTANCE': roads_buffer_m,
    'SEGMENTS': 5,
    'DISSOLVE': True,
    'OUTPUT': 'TEMPORARY_OUTPUT'
}
road_buffer_action = processing.run("native:buffer", road_buffer_params)
raw_buffered_roads = road_buffer_action['OUTPUT']

print("   [Masking] Eliminating peripheral intersections outside spatial domain...")
road_mask_params = {
    'INPUT': raw_buffered_roads,
    'OVERLAY': healthcare_buffer_zone,
    'OUTPUT': 'TEMPORARY_OUTPUT'
}
road_mask_action = processing.run("native:clip", road_mask_params)
buffered_roads_zone = road_mask_action['OUTPUT']
buffered_roads_zone.setName(f"Roads {roads_buffer_km}km Buffer (Masked to HC Zone)")
QgsProject.instance().addMapLayer(buffered_roads_zone)


# D. Execute Vector Intersections to Extract Target Served Settlements
print("4. Evaluating geometric intersections to map demographic access metrics...")
intersection_params = {
    'INPUT': buffered_roads_zone,
    'OVERLAY': cleaned_layers['settlements'],
    'INPUT_FIELDS': [],
    'OVERLAY_FIELDS': [],
    'OVERLAY_PREFIX': 'settle_',
    'OUTPUT': 'TEMPORARY_OUTPUT'
}
intersection_action = processing.run("native:intersection", intersection_params)
final_settlement_intersection = intersection_action['OUTPUT']
final_settlement_intersection.setName("Served Settlements") # Custom named per target profile
QgsProject.instance().addMapLayer(final_settlement_intersection)

print("\n🎉 Spatial modeling complete. Pipeline outputs generated without structural errors.")


# ===============================================================================
# STEP 6: CARTOGRAPHIC DESIGN & FEATURE SYMBOLOGY SPECIFICATION
# ===============================================================================
print("\n🎨 Loading map layer visual styling variables...")

# A. Base Administrative Boundary Vector Layer
style_district = QgsFillSymbol.createSimple({'color': color_district, 'outline_color': '#4a4a4a', 'outline_width': '0.5'})
extracted_boundary_layer.setRenderer(QgsSingleSymbolRenderer(style_district))
extracted_boundary_layer.triggerRepaint()

# B. District-Wide Reference Base Roads (Muted background display)
style_district_roads = QgsLineSymbol.createSimple({'color': color_district_roads, 'width': '0.2', 'capstyle': 'round'})
cleaned_layers['roads_district'].setRenderer(QgsSingleSymbolRenderer(style_district_roads))
cleaned_layers['roads_district'].triggerRepaint()

# C. Healthcare Infrastructure Buffer Boundary Zones
style_hc_buff = QgsFillSymbol.createSimple({'color': color_hc_buff, 'outline_color': '#ff4d4d', 'outline_style': 'dash', 'outline_width': '0.4'})
style_hc_buff.setOpacity(0.6)
healthcare_buffer_zone.setRenderer(QgsSingleSymbolRenderer(style_hc_buff))
healthcare_buffer_zone.triggerRepaint()

# D. Transportation Core Transit Proximity Buffers
style_roads_buff = QgsFillSymbol.createSimple({'color': color_roads_buff, 'outline_color': '#2b8cbe', 'outline_style': 'dot', 'outline_width': '0.3'})
style_roads_buff.setOpacity(0.5)
buffered_roads_zone.setRenderer(QgsSingleSymbolRenderer(style_roads_buff))
buffered_roads_zone.triggerRepaint()

# E. Complete Base Settlement Background Footprints
style_settlements = QgsFillSymbol.createSimple({'color': color_settlements, 'outline_style': 'no', 'outline_color': 'transparent'})
cleaned_layers['settlements'].setRenderer(QgsSingleSymbolRenderer(style_settlements))
cleaned_layers['settlements'].triggerRepaint()

# F. Target High-Priority Served Settlements (Intersection Layer Highlight)
style_intersected = QgsFillSymbol.createSimple({'color': color_intersected, 'outline_color': '#d35400', 'outline_width': '0.2'})
final_settlement_intersection.setRenderer(QgsSingleSymbolRenderer(style_intersected))
final_settlement_intersection.triggerRepaint()

# G. Active Transit Line Paths Inside Primary Buffers
style_roads = QgsLineSymbol.createSimple({'color': color_roads, 'width': '0.4', 'capstyle': 'round'})
roads_clipped_by_hc.setRenderer(QgsSingleSymbolRenderer(style_roads))
roads_clipped_by_hc.triggerRepaint()


# ===============================================================================
# STEP 7: HIERARCHICAL CANVAS Z-ORDER LAYER STACKING SPECIFICATION
# ===============================================================================
print("🗂 Configuring layer stacking rendering sequence rules...")
layer_manager = QgsProject.instance().layerTreeRoot()

# Bottom-to-Top ordered compilation layer array mapping layout references
ordered_layers_bottom_to_top = [
    extracted_boundary_layer,          # 1. BOTTOM LAYER (Regional Boundary Structure)
    cleaned_layers['roads_district'],  # 2. Complete background district-wide road lines
    healthcare_buffer_zone,            # 3. Macro Proximity Boundary Footprints
    buffered_roads_zone,               # 4. Micro Transportation Proximity Limits
    cleaned_layers['settlements'],     # 5. Native Demographics Coverage Area
    final_settlement_intersection,     # 6. HIGH LIGHT INSIGHTS (Served Settlements)
    roads_clipped_by_hc                # 7. TOP LAYER (Active Foreground Access Roads)
]

for layer in ordered_layers_bottom_to_top:
    layer_node = layer_manager.findLayer(layer.id())
    if layer_node:
        clone = layer_node.clone()
        layer_manager.insertChildNode(0, clone)
        layer_manager.removeChildNode(layer_node)


# ===============================================================================
# STEP 8: AUTOMATED PRINT LAYOUT COMPILATION & GENERATION (A4 PORTRAIT)
# ===============================================================================
print("📐 Constructing automated A4 portrait publication layout canvas...")
project = QgsProject.instance()
layout_name = "Sirajganj Health Accessibility Report"

existing_layout = project.layoutManager().layoutByName(layout_name)
if existing_layout:
    project.layoutManager().removeLayout(existing_layout)

layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName(layout_name)

page = layout.pageCollection().pages()[0]
page.setPageSize(QgsLayoutSize(210, 297, QgsUnitTypes.LayoutMillimeters))

# A. Central Map View Component Canvas Framing configuration settings
map_item = QgsLayoutItemMap(layout)
map_item.setRect(0, 0, 10, 10)
map_item.attemptMove(QgsLayoutPoint(14, 45, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(186, 165, QgsUnitTypes.LayoutMillimeters))
map_item.zoomToExtent(extracted_boundary_layer.extent())
layout.addLayoutItem(map_item)

# B. Geographic Neatline Grids & Coordinate Labels Configuration
print("🌐 Formatting projection reference coordinate grid frames...")
grid = QgsLayoutItemMapGrid("map_grid", map_item)

lat_lon_crs = QgsCoordinateReferenceSystem("EPSG:4326")
grid.setCrs(lat_lon_crs)

# Clean, low-density 0.2-degree markers for structural clarity
grid.setIntervalX(0.2) 
grid.setIntervalY(0.2)
grid.setAnnotationEnabled(True)
grid.setAnnotationFormat(QgsLayoutItemMapGrid.DecimalWithSuffix)

grid.setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, QgsLayoutItemMapGrid.Left)
grid.setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, QgsLayoutItemMapGrid.Right)
grid.setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, QgsLayoutItemMapGrid.Top)
grid.setAnnotationPosition(QgsLayoutItemMapGrid.OutsideMapFrame, QgsLayoutItemMapGrid.Bottom)

# Precise side-coordinate vertical orientation definitions
grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Left)
grid.setAnnotationDirection(QgsLayoutItemMapGrid.BoundaryDirection, QgsLayoutItemMapGrid.Right)

grid.setAnnotationDisplay(QgsLayoutItemMapGrid.ShowAll, QgsLayoutItemMapGrid.Left)
grid.setAnnotationDisplay(QgsLayoutItemMapGrid.ShowAll, QgsLayoutItemMapGrid.Right)

grid.setGridLineColor(QColor(200, 200, 200, 120))
map_item.grids().addGrid(grid)

# C. Header Title Component Element Configuration Panel
title_item = QgsLayoutItemLabel(layout)
title_item.setText(map_title_text)
title_item.setFont(QFont("Arial", 18, QFont.Bold))
title_item.attemptMove(QgsLayoutPoint(10, 15, QgsUnitTypes.LayoutMillimeters))
title_item.attemptResize(QgsLayoutSize(190, 25, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(title_item)

# D. Linear Metric Scale Bar Display Component block
print("📏 Positioning metric scale components...")
scale_bar = QgsLayoutItemScaleBar(layout)
scale_bar.setLinkedMap(map_item)
scale_bar.setUnits(QgsUnitTypes.DistanceKilometers)
scale_bar.setNumberOfSegments(3)
scale_bar.setUnitsPerSegment(5.0)  
scale_bar.setUnitLabel("km")
scale_bar.setFont(QFont("Arial", 9))
scale_bar.applyDefaultSettings()
scale_bar.attemptMove(QgsLayoutPoint(15, 195, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(scale_bar)

# E. True North Reference Arrow Graphical Compass asset pointer
print("🧭 Anchoring layout directional compass needle pointers...")
north_arrow = QgsLayoutItemPicture(layout)
north_arrow.setPicturePath(":/images/north_arrows/layout_default_north_arrow.svg")
north_arrow.attemptMove(QgsLayoutPoint(175, 50, QgsUnitTypes.LayoutMillimeters))
north_arrow.attemptResize(QgsLayoutSize(15, 15, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(north_arrow)

# F. Cartographic Data Legend Display Interface box
print("📋 Structuring final presentation map layer legend entries...")
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setAutoUpdateModel(False)

# Rebuild matching layout reference tracking titles top-to-bottom
legend_root = legend.model().rootGroup()
legend_root.clear()
for layer in reversed(ordered_layers_bottom_to_top):
    legend_root.addLayer(layer)

legend.setTitle("Map Layers Legend")
legend_font = QFont("Arial", 10)
legend.setStyleFont(QgsLegendStyle.Title, legend_font)
legend.setStyleFont(QgsLegendStyle.SymbolLabel, legend_font)
legend.attemptMove(QgsLayoutPoint(10, 222, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)


# ===============================================================================
# STEP 9: REGISTRY COMPILATION & OPTIMIZED PDF PRODUCTION EXPORT TERMINATION
# ===============================================================================
project.layoutManager().addLayout(layout)
print(f"\n💾 Initiating high-efficiency optimized PDF publication compression write routine...")

exporter = QgsLayoutExporter(layout)
pdf_settings = QgsLayoutExporter.PdfExportSettings()

# Production Size & Processing Vector Optimization Tuning parameters
pdf_settings.dpi = 150.0 
pdf_settings.simplifyGeometries = True
pdf_settings.forceRaster = True  # Flattens complex spatial boundaries to preserve small output sizes

export_status = exporter.exportToPdf(pdf_output_path, pdf_settings)

if export_status == QgsLayoutExporter.Success:
    print(f"\n🎉 EXPORT SUCCESS! Your clean, highly optimized document has been generated at:\n--> {pdf_output_path}")
else:
    print("\n❌ System Export Error. Verify operational file system write permissions profiles.")