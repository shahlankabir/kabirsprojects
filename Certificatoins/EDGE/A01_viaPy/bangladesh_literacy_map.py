"""
package install guide

mamba create -n geo_mapping python=3.11
mamba activate geo_mapping
mamba install geopandas cartopy geoplot pysal rasterio matplotlib -c conda-forge
"""

""" packages """
from math import cos, radians
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Point

""" Merging """

# data loading
temp_df = pd.read_csv("population2022.csv")
temp_gdf = gpd.read_file("bgd_admin2.shp")

# data info
print(temp_df.info())
print(temp_gdf.info())

# clean dataframes
temp_df = temp_df.dropna(axis=1, how="all")
temp_gdf = temp_gdf.dropna(axis=1, how="all")

# data info
print(temp_df.info())
print(temp_gdf.info())

temp_df2 = temp_df.drop(columns="District")


def clean_numeric(s):
    if s is None:
        return s
    s = str(s).strip()
    if s == "":
        return pd.NA
    s = s.replace(",", "")  # remove sep
    s = s.replace("$", "").replace("€", "")  # remove currency symbols
    if s.endswith("%"):
        return float(s.rstrip("%")) / 100.0  # convert percent to fraction
    return s


# Clean matrix elements map-wise (using .map instead of deprecated .applymap)
temp_df2_clean = temp_df2.astype(str).map(clean_numeric)
df_float = (
    temp_df2_clean.apply(pd.to_numeric, errors="coerce").astype("float64").copy()
)

df_float["District"] = temp_df["District"].copy()
df_float.info()

# data merge and new geopackage format
gdf = temp_gdf.merge(
    df_float, left_on="adm2_name", right_on="District", how="left"
)
gdf.info()
gdf.to_file("edge_a01_database.gpkg", driver="GPKG")

""" Visualization """

gdf_gpkg = gpd.read_file("edge_a01_database.gpkg")
median = gdf_gpkg.select_dtypes(
    include="number"
).median()  # getting numerical columns median value
gdf_gpkg[median.index] = gdf_gpkg[median.index].fillna(
    median
)  # filling missing values with median values
gdf_gpkg.isna().sum()
gdf = gdf_gpkg.copy()
gdf.to_file("edge_a01_database.gpkg", driver="GPKG")


def add_accurate_scale_bar(ax, dist_km=100):
    """Dynamically extracts map extents and draws a mathematically accurate scale bar

    for a PlateCarree (Equirectangular) projection map.
    """
    # 1. Dynamically grab the current map boundaries in Lat/Lon degrees
    lon_min, lon_max, lat_min, lat_max = ax.get_extent(crs=ccrs.PlateCarree())

    # 2. Calculate horizontal ground distance conversion at the center of the viewport
    avg_lat = (lat_min + lat_max) / 2
    km_per_degree = 111.32 * cos(radians(avg_lat))

    # 3. Convert targeted scale length to spatial degree coordinates
    scale_width_deg = dist_km / km_per_degree

    # 4. Corner positioning offsets anchors
    x_start = lon_min + (lon_max - lon_min) * 0.05
    y_pos = lat_min + (lat_max - lat_min) * 0.06

    # Tick mark bounds scaled perfectly alongside vertical viewport spread
    tick_height = (lat_max - lat_min) * 0.01

    # Base Line
    ax.plot(
        [x_start, x_start + scale_width_deg],
        [y_pos, y_pos],
        transform=ccrs.PlateCarree(),
        color="black",
        lw=2,
        zorder=20,
    )

    # Left boundary cap
    ax.plot(
        [x_start, x_start],
        [y_pos, y_pos + tick_height],
        transform=ccrs.PlateCarree(),
        color="black",
        lw=2,
        zorder=20,
    )

    # Right boundary cap
    ax.plot(
        [x_start + scale_width_deg, x_start + scale_width_deg],
        [y_pos, y_pos + tick_height],
        transform=ccrs.PlateCarree(),
        color="black",
        lw=2,
        zorder=20,
    )

    # Dynamic metrics label text
    ax.text(
        x_start + scale_width_deg / 2,
        y_pos - ((lat_max - lat_min) * 0.015),
        f"{dist_km} km",
        transform=ccrs.PlateCarree(),
        ha="center",
        va="top",
        fontsize=10,
        fontweight="bold",
        family="serif",
    )


# Coordinate setup
map_proj = ccrs.PlateCarree()

fig = plt.figure(figsize=(8.27, 11.69), dpi=300)
ax = plt.axes(projection=map_proj)

ax.add_feature(
    cfeature.OCEAN,
    facecolor="#e0e0e0",
    hatch="\\\\\\",
    edgecolor="#6fd3e0",
    linewidth=0,
)

ax.add_feature(
    cfeature.LAND,
    facecolor="#ffffff",
    hatch="....",
    edgecolor="#bff7d6",
    linewidth=0.02,
    zorder=0,
)

# Plot boundaries choropleth layer
plot = gdf.plot(
    ax=ax,
    column="Literacy",
    transform=ccrs.PlateCarree(),
    cmap="YlGnBu",
    legend=True,
    edgecolor="black",
    linewidth=0.3,
    legend_kwds={
        "label": "Literacy Percentage",
        "shrink": 0.5,
        "orientation": "vertical",
    },
)

plt.title(
    "CARTOGRAPHY MAP \n OF \n DISTRICT-WISE LITERACY PERCENTAGE OF BANGLADESH ",
    fontweight="bold",
    fontsize=12,
    pad=20,
    family="serif",
)

# Canvas Gridlines
gl = ax.gridlines(
    draw_labels=True, linewidth=0.5, color="gray", alpha=0.5, linestyle="--"
)
gl.top_labels = True
gl.right_labels = True
gl.xlabel_style = {"size": 6, "color": "black"}
gl.ylabel_style = {"size": 6, "color": "black"}

# Compass Pointer UI setup
nx, ny = 0.95, 0.95
arrow_length = 0.08

ax.text(
    nx,
    ny,
    "N",
    transform=ax.transAxes,
    ha="center",
    va="bottom",
    fontsize=18,
    fontweight="bold",
    family="serif",
)

ax.annotate(
    "",
    xy=(nx, ny - 0.01),
    xytext=(nx, ny - arrow_length),
    arrowprops=dict(
        facecolor="black", edgecolor="black", width=1, headwidth=8, headlength=12
    ),
    xycoords="axes fraction",
    ha="center",
)

# Context metadata box annotation
metadata_text = "Projection: WGS 84 / EPSG:4326\nData Source: EDGE project\nDate: 2026\nDrawn By: Md Shahlan Kabir"
plt.text(
    0.99,
    0.01,
    metadata_text,
    transform=ax.transAxes,
    fontsize=9,
    ha="right",
    va="bottom",
    color="#4d4d4d",
    bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"),
)

# Call the dynamic scale bar function (100 km scale reads nicely inside Bangladesh bounds)
add_accurate_scale_bar(ax, dist_km=100)

# Export assets out to workspace file system safely prior to window display lifecycle termination
plt.savefig("bangladesh_literacy_map.png", dpi=300, bbox_inches="tight")

plt.show()