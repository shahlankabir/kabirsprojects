# packages
from math import cos, radians
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import fiona
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# pre-process
layers = fiona.listlayers("SourceDatabaseUTM.gpkg")
target_crs = "EPSG:32645"
gdfs = {}
for layer in layers:
    gdfs[layer] = gpd.read_file("SourceDatabaseUTM.gpkg", layer=layer)
    gdfs[layer] = gdfs[layer].to_crs(target_crs)

# location mask (keeping it in UTM coordinate space for safe spatial buffering)
mask_utm = gdfs["districtlged2021"][
    gdfs["districtlged2021"]["DISTRICT"].isin(["Sirajganj"])
]

# clipping all layers with mask natively in UTM
clipped_gdfs = {}
for layer, gdf in gdfs.items():
    clipped_gdfs[layer] = gpd.clip(gdf, mask_utm)

# healthcare facility query
clipped_gdfs["bdhealthfacilitiesosm2020"] = clipped_gdfs[
    "bdhealthfacilitiesosm2020"
][
    clipped_gdfs["bdhealthfacilitiesosm2020"]["Amenity"].isin(
        ["hospital", "clinic"]
    )
]

# accurate spatial processing using meter units (UTM)
buff_h_utm = clipped_gdfs["bdhealthfacilitiesosm2020"].copy()
buff_h_utm["geometry"] = (
    buff_h_utm["geometry"].buffer(5000).clip(mask_utm)
)  # healthcares 5km buffer

buff_r_utm = clipped_gdfs["bdroadsusaid2021"].copy()
buff_r_utm["geometry"] = (
    buff_r_utm["geometry"].buffer(1000).clip(buff_h_utm)
)  # roads 1km buffer

final_s_utm = gpd.overlay(
    clipped_gdfs["settlementlged2020"], buff_r_utm, how="intersection"
)

# ----------------------------
# 1. PROJECTION SETUP
# ----------------------------
map_proj = ccrs.PlateCarree()

# ----------------------------
# 2. CRS CONVERSION FOR MAP DISPLAY
# ----------------------------
mask = mask_utm.to_crs("EPSG:4326")
roads_layer = clipped_gdfs["bdroadsusaid2021"].to_crs("EPSG:4326")
settlements_layer = clipped_gdfs["settlementlged2020"].to_crs("EPSG:4326")

buff_h = buff_h_utm.to_crs("EPSG:4326")
buff_r = buff_r_utm.to_crs("EPSG:4326")
final_s = final_s_utm.to_crs("EPSG:4326")


# ----------------------------
# SCALE BAR HELPER FUNCTION
# ----------------------------
def add_accurate_scale_bar(ax, dist_km=10):
    """Dynamically calculates and draws a mathematically accurate scale bar

    based on the current axis extent and geographical mid-latitude.
    """
    # 1. Grab axis tracking limits
    lon_min, lon_max, lat_min, lat_max = ax.get_extent(crs=ccrs.PlateCarree())

    # 2. Compute horizontal scale distortion factor based on mid-latitude target
    avg_lat = (lat_min + lat_max) / 2
    km_per_degree = 111.32 * cos(radians(avg_lat))

    # 3. Scale width map conversion
    scale_width_deg = dist_km / km_per_degree

    # 4. Corner positions anchoring coordinate links
    x_start = lon_min + (lon_max - lon_min) * 0.05
    y_pos = lat_min + (lat_max - lat_min) * 0.15

    # Tick mark size bounds matching visual scale frame depth
    tick_height = (lat_max - lat_min) * 0.015

    # Main horizontal bar line
    ax.plot(
        [x_start, x_start + scale_width_deg],
        [y_pos, y_pos],
        transform=ccrs.PlateCarree(),
        color="black",
        lw=2,
        zorder=20,
    )

    # Left vertical tick boundary
    ax.plot(
        [x_start, x_start],
        [y_pos, y_pos + tick_height],
        transform=ccrs.PlateCarree(),
        color="black",
        lw=2,
        zorder=20,
    )

    # Right vertical tick boundary
    ax.plot(
        [x_start + scale_width_deg, x_start + scale_width_deg],
        [y_pos, y_pos + tick_height],
        transform=ccrs.PlateCarree(),
        color="black",
        lw=2,
        zorder=20,
    )

    # Metric label text
    ax.text(
        x_start + scale_width_deg / 2,
        y_pos - ((lat_max - lat_min) * 0.02),
        f"{dist_km} km",
        transform=ccrs.PlateCarree(),
        ha="center",
        va="top",
        fontsize=9,
        fontweight="bold",
    )


# ----------------------------
# 3. FIGURE
# ----------------------------
fig = plt.figure(figsize=(10, 12), dpi=300)
ax = fig.add_axes([0.1, 0.1, 0.8, 0.8], projection=map_proj)

ax.set_extent([89.25, 89.85, 24.0, 24.8], crs=ccrs.PlateCarree())

# ----------------------------
# 4. BASE MAP BACKGROUND
# ----------------------------
ax.add_feature(
    cfeature.LAND,
    facecolor="#ffffff",
    hatch="....",
    edgecolor="#bff7d6",
    linewidth=0.02,
    zorder=0,
)

# ----------------------------
# 5. DATA LAYERS
# ----------------------------
mask.plot(
    ax=ax,
    facecolor="#fffbe3",
    edgecolor="black",
    linewidth=1,
    transform=ccrs.PlateCarree(),
    zorder=1,
)

buff_h.plot(
    ax=ax, color="#ff5a5a", alpha=0.25, transform=ccrs.PlateCarree(), zorder=2
)
buff_r.plot(
    ax=ax, color="#0029af", alpha=0.25, transform=ccrs.PlateCarree(), zorder=3
)

roads_layer.plot(
    ax=ax, color="#444444", linewidth=0.5, transform=ccrs.PlateCarree(), zorder=4
)

settlements_layer.plot(
    ax=ax,
    color="#ff5ae4",
    markersize=4,
    alpha=0.6,
    transform=ccrs.PlateCarree(),
    zorder=5,
)

final_s.plot(
    ax=ax,
    color="red",
    markersize=8,
    edgecolor="white",
    linewidth=0.5,
    transform=ccrs.PlateCarree(),
    zorder=6,
)

# ----------------------------
# 6. GRIDLINES
# ----------------------------
gl = ax.gridlines(
    draw_labels=True, linewidth=0.5, color="gray", alpha=0.4, linestyle="--"
)
gl.top_labels = True
gl.right_labels = True
gl.xlabel_style = {"size": 8}
gl.ylabel_style = {"size": 8}

# ----------------------------
# 7. TITLE
# ----------------------------
plt.title(
    "ACCESS TO HEALTHCARE FACILITIES \nFROM SETTLEMENTS IN SIRAJGANJ, BANGLADESH",
    fontsize=14,
    fontweight="bold",
    pad=20,
)

# ----------------------------
# 8. NORTH ARROW UI
# ----------------------------
nx, ny = 0.95, 0.92
ax.text(
    nx,
    ny,
    "N",
    transform=ax.transAxes,
    ha="center",
    va="bottom",
    fontsize=16,
    fontweight="bold",
)

ax.annotate(
    "",
    xy=(nx, ny - 0.01),
    xytext=(nx, ny - 0.06),
    arrowprops=dict(facecolor="black", width=1, headwidth=8),
    xycoords="axes fraction",
)

# ----------------------------
# 9. RUN DYNAMIC SCALE BAR (10 km setup works best inside district scopes)
# ----------------------------
add_accurate_scale_bar(ax, dist_km=10)

# ----------------------------
# 10. LEGEND SETUP
# ----------------------------
legend_elements = [
    Line2D(
        [0],
        [0],
        color="red",
        marker="o",
        ls="None",
        markersize=8,
        label="Final Access Settlements",
    ),
    Line2D(
        [0],
        [0],
        color="#ff5ae4",
        marker="o",
        ls="None",
        markersize=5,
        label="Settlements",
    ),
    Line2D([0], [0], color="#444444", lw=1, label="Roads"),
    plt.Rectangle((0, 0), 1, 1, fc="#ff5a5a", alpha=0.3, label="Health Buffer"),
    plt.Rectangle((0, 0), 1, 1, fc="#0029af", alpha=0.3, label="Road Buffer"),
]

ax.legend(handles=legend_elements, loc="lower left", fontsize=8, frameon=True)

# ----------------------------
# 11. METADATA ANNOTATION
# ----------------------------
ax.text(
    0.98,
    0.02,
    "EPSG:4326 display\nEPSG:32645 processing\nSource: GPKG 2026 \nRoad Buffer: 1km \nHealthcare Buffer: 5km",
    transform=ax.transAxes,
    ha="right",
    fontsize=8,
    bbox=dict(facecolor="white", alpha=0.8, edgecolor="none"),
)

# ----------------------------
# 12. INSET REGIONAL POSITION MAP
# ----------------------------
inset_ax = fig.add_axes([0.18, 0.70, 0.18, 0.18], projection=ccrs.PlateCarree())

inset_ax.add_feature(
    cfeature.LAND, facecolor="#ffffff", edgecolor="black", linewidth=0.2
)
inset_ax.add_feature(
    cfeature.BORDERS, linestyle="-", linewidth=0.5, edgecolor="gray"
)

# Draw full country boundaries index marker using parent district frame context
mask.plot(ax=inset_ax, color="red", alpha=0.8, transform=ccrs.PlateCarree())

inset_ax.set_extent([88, 93, 20.5, 26.5], crs=ccrs.PlateCarree())
inset_ax.set_xticks([])
inset_ax.set_yticks([])

# ----------------------------
# 13. FILE EXPORT EXECUTED PRIOR TO SHOW WINDOW LIFECYCLE CLOSURE
# ----------------------------
plt.savefig("sirajganj_health_map.png", dpi=300, bbox_inches="tight")
plt.show()