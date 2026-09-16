import geopandas as gpd
import pandas as pd

POINT_FILE = r"C:\3D_KADASTER\bangunan.geojson"
FOOTPRINT_FILE = r"C:\3D_KADASTER\kirim\PERMUKIMAN_MERGE.shp"

# ============================================================
# LOAD
# ============================================================

points = gpd.read_file(POINT_FILE)
footprints = gpd.read_file(FOOTPRINT_FILE)

# Semua analisis jarak harus dalam meter
points = points.to_crs("EPSG:32748")
footprints = footprints.to_crs("EPSG:32748")

# ============================================================
# FIX GEOMETRY
# ============================================================

invalid = ~footprints.geometry.is_valid

if invalid.any():
    footprints.loc[invalid, "geometry"] = (
        footprints.loc[invalid, "geometry"].buffer(0)
    )

footprints = footprints[
    ~footprints.geometry.is_empty
    & footprints.geometry.notna()
].copy()

footprints = footprints.reset_index(drop=True)

footprints["footprint_id"] = footprints.index + 1

# Hitung area ASLI dari geometry dalam m²
footprints["area_m2"] = footprints.geometry.area

print("=" * 70)
print("ANALISIS JARAK TITIK → FOOTPRINT")
print("=" * 70)

print("Titik     :", len(points))
print("Footprint :", len(footprints))

print("\nLuas footprint:")
print(
    footprints["area_m2"]
    .describe()
    .round(2)
)

# ============================================================
# CEK WITHIN
# ============================================================

within = gpd.sjoin(
    points,
    footprints[
        [
            "footprint_id",
            "area_m2",
            "geometry"
        ]
    ],
    how="left",
    predicate="within"
)

matched_index = set(
    within[
        within["footprint_id"].notna()
    ].index
)

unmatched = points[
    ~points.index.isin(matched_index)
].copy()

print("\nTitik sudah masuk polygon :", len(matched_index))
print("Titik belum masuk polygon :", len(unmatched))

# ============================================================
# NEAREST FOOTPRINT
# ============================================================

nearest = gpd.sjoin_nearest(
    unmatched,
    footprints[
        [
            "footprint_id",
            "area_m2",
            "geometry"
        ]
    ],
    how="left",
    distance_col="jarak_meter"
)

# Kalau ada tie, ambil satu yang paling dekat
nearest = (
    nearest
    .sort_values("jarak_meter")
    .groupby(level=0)
    .first()
)

# ============================================================
# DISTRIBUSI JARAK
# ============================================================

print("\n" + "=" * 70)
print("DISTRIBUSI JARAK 262 TITIK YANG TIDAK MATCH")
print("=" * 70)

print(
    nearest["jarak_meter"]
    .describe()
    .round(2)
)

thresholds = [
    1,
    2,
    3,
    5,
    7.5,
    10,
    15,
    20,
    30,
    50
]

print("\nJumlah titik berdasarkan jarak:")

for threshold in thresholds:

    count = (
        nearest["jarak_meter"]
        <= threshold
    ).sum()

    print(
        f"<= {threshold:>4} m : "
        f"{count:>3} / {len(nearest)}"
    )

# ============================================================
# CONTOH TITIK
# ============================================================

print("\n" + "=" * 70)
print("20 TITIK TERDEKAT")
print("=" * 70)

columns = [
    "id_bangunan",
    "fungsi_bangunan",
    "jumlah_lantai",
    "footprint_id",
    "area_m2",
    "jarak_meter"
]

available = [
    c for c in columns
    if c in nearest.columns
]

print(
    nearest[available]
    .sort_values("jarak_meter")
    .head(20)
    .to_string(index=False)
)

print("\n" + "=" * 70)
print("20 TITIK TERJAUH")
print("=" * 70)

print(
    nearest[available]
    .sort_values(
        "jarak_meter",
        ascending=False
    )
    .head(20)
    .to_string(index=False)
)

# ============================================================
# SIMPAN HASIL
# ============================================================

nearest_output = nearest.copy()

nearest_output = nearest_output.to_crs(
    "EPSG:4326"
)

nearest_output.to_file(
    r"C:\3D_KADASTER\nearest_footprint.geojson",
    driver="GeoJSON"
)

nearest.drop(
    columns="geometry"
).to_csv(
    r"C:\3D_KADASTER\nearest_footprint.csv",
    index=False
)

print("\nOutput:")
print(
    r"C:\3D_KADASTER\nearest_footprint.csv"
)
print(
    r"C:\3D_KADASTER\nearest_footprint.geojson"
)