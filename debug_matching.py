import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

POINT_FILE = r"C:\3D_KADASTER\bangunan.geojson"
FOOTPRINT_FILE = r"C:\3D_KADASTER\kirim\PERMUKIMAN_MERGE.shp"

OUTPUT = r"C:\3D_KADASTER\debug_matching.geojson"

CRS = "EPSG:32748"
MAX_DISTANCE = 15

# ============================================================
# LOAD
# ============================================================

points = gpd.read_file(POINT_FILE).to_crs(CRS)
footprints = gpd.read_file(FOOTPRINT_FILE).to_crs(CRS)

points = points.reset_index(drop=True)
points["point_id"] = points.index

footprints = footprints.reset_index(drop=True)
footprints["footprint_id"] = footprints.index + 1

# fix invalid
bad = ~footprints.geometry.is_valid

if bad.any():
    footprints.loc[bad, "geometry"] = (
        footprints.loc[bad, "geometry"].buffer(0)
    )

footprints["centroid"] = footprints.geometry.centroid

# ============================================================
# NEAREST UNTUK SEMUA TITIK
# ============================================================

nearest = gpd.sjoin_nearest(
    points,
    footprints[
        [
            "footprint_id",
            "geometry"
        ]
    ],
    how="left",
    distance_col="jarak_meter"
)

# kalau satu titik punya tie
nearest = (
    nearest
    .sort_values("jarak_meter")
    .groupby("point_id")
    .first()
    .reset_index()
)

# ============================================================
# HITUNG BERAPA TITIK MEMILIH FOOTPRINT SAMA
# ============================================================

counts = (
    nearest["footprint_id"]
    .value_counts()
)

nearest["jumlah_titik_footprint"] = (
    nearest["footprint_id"]
    .map(counts)
)

nearest["konflik"] = (
    nearest["jumlah_titik_footprint"] > 1
)

print("=" * 70)
print("DEBUG MATCHING")
print("=" * 70)

print("Total titik:", len(points))

print(
    "Footprint unik terpilih:",
    nearest["footprint_id"].nunique()
)

print(
    "Footprint konflik:",
    (
        counts > 1
    ).sum()
)

print(
    "Titik terlibat konflik:",
    nearest["konflik"].sum()
)

print("\nDistribusi jumlah titik per footprint:")

print(
    counts.value_counts()
    .sort_index()
)

# ============================================================
# BUAT GARIS TITIK -> CENTROID FOOTPRINT
# ============================================================

features = []

for _, row in nearest.iterrows():

    point_id = int(row["point_id"])

    fp_id = int(row["footprint_id"])

    point = points.loc[
        points["point_id"] == point_id
    ].iloc[0]

    fp = footprints.loc[
        footprints["footprint_id"] == fp_id
    ].iloc[0]

    line = LineString([
        point.geometry,
        fp["centroid"]
    ])

    features.append({
        "point_id":
            point_id,

        "id_bangunan":
            point.get("id_bangunan"),

        "fungsi_bangunan":
            point.get("fungsi_bangunan"),

        "jumlah_lantai":
            point.get("jumlah_lantai"),

        "footprint_id":
            fp_id,

        "jarak_meter":
            round(float(row["jarak_meter"]), 2),

        "jumlah_titik_footprint":
            int(row["jumlah_titik_footprint"]),

        "konflik":
            bool(row["konflik"]),

        "geometry":
            line
    })

# ============================================================
# OUTPUT
# ============================================================

debug = gpd.GeoDataFrame(
    features,
    geometry="geometry",
    crs=CRS
)

debug = debug.to_crs(4326)

debug.to_file(
    OUTPUT,
    driver="GeoJSON"
)

print("\nOutput:")
print(OUTPUT)

# ============================================================
# 30 KONFLIK TERBESAR
# ============================================================

print("\nFootprint dengan konflik terbesar:")

print(
    counts[counts > 1]
    .head(30)
    .to_string()
)