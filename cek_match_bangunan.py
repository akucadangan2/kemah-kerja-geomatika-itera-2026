import geopandas as gpd
import pandas as pd

# ============================================================
# PATH
# ============================================================

POINT_FILE = r"C:\3D_KADASTER\bangunan.geojson"
FOOTPRINT_FILE = r"C:\3D_KADASTER\kirim\PERMUKIMAN_MERGE.shp"

# ============================================================
# LOAD
# ============================================================

points = gpd.read_file(POINT_FILE)
footprints = gpd.read_file(FOOTPRINT_FILE)

print("=" * 70)
print("MATCH TITIK SURVEI → FOOTPRINT BANGUNAN")
print("=" * 70)

print("Titik survei :", len(points))
print("Footprint    :", len(footprints))

# ============================================================
# CRS
# ============================================================

print("\nCRS titik     :", points.crs)
print("CRS footprint :", footprints.crs)

# Samakan ke UTM 48S
points = points.to_crs("EPSG:32748")
footprints = footprints.to_crs("EPSG:32748")

# ============================================================
# FIX INVALID GEOMETRY
# ============================================================

invalid = ~footprints.geometry.is_valid

print("\nFootprint invalid sebelum fix:", invalid.sum())

if invalid.any():
    footprints.loc[invalid, "geometry"] = (
        footprints.loc[invalid, "geometry"].buffer(0)
    )

print(
    "Footprint invalid setelah fix:",
    (~footprints.geometry.is_valid).sum()
)

# ============================================================
# ID FOOTPRINT
# ============================================================

footprints = footprints.reset_index(drop=True)

footprints["footprint_id"] = (
    footprints.index + 1
)

# ============================================================
# SPATIAL JOIN
# titik yang berada di dalam polygon
# ============================================================

footprint_subset = footprints[
    [
        "footprint_id",
        "SHAPE_Area",
        "geometry"
    ]
].copy()

matched = gpd.sjoin(
    points,
    footprint_subset,
    how="left",
    predicate="within"
)

# ============================================================
# HASIL
# ============================================================

inside = matched["footprint_id"].notna()

jumlah_match = inside.sum()
jumlah_tidak_match = (~inside).sum()

print("\n" + "=" * 70)
print("HASIL")
print("=" * 70)

print("Total titik          :", len(points))
print("Masuk footprint      :", jumlah_match)
print("Tidak masuk footprint:", jumlah_tidak_match)

print(
    "Persentase match     :",
    round(
        jumlah_match / len(points) * 100,
        2
    ),
    "%"
)

# ============================================================
# DUPLIKASI
# ============================================================

duplicate_points = (
    matched
    .groupby(matched.index)
    .size()
)

duplicate_points = duplicate_points[
    duplicate_points > 1
]

print(
    "Titik masuk >1 polygon:",
    len(duplicate_points)
)

# ============================================================
# CONTOH MATCH
# ============================================================

print("\nContoh berhasil match:")

cols = [
    "id_bangunan",
    "fungsi_bangunan",
    "jumlah_lantai",
    "footprint_id",
    "SHAPE_Area"
]

available = [
    c for c in cols
    if c in matched.columns
]

print(
    matched.loc[
        inside,
        available
    ]
    .head(15)
    .to_string(index=False)
)

# ============================================================
# YANG TIDAK MATCH
# ============================================================

print("\nContoh TIDAK match:")

print(
    matched.loc[
        ~inside,
        [
            c for c in [
                "id_bangunan",
                "fungsi_bangunan",
                "jumlah_lantai"
            ]
            if c in matched.columns
        ]
    ]
    .head(20)
    .to_string(index=False)
)

# ============================================================
# SIMPAN UNTUK INSPEKSI
# ============================================================

unmatched = matched[
    ~inside
].copy()

unmatched = unmatched.to_crs(4326)

unmatched.to_file(
    r"C:\3D_KADASTER\bangunan_tidak_match.geojson",
    driver="GeoJSON"
)

print("\nFile titik tidak match:")
print(
    r"C:\3D_KADASTER\bangunan_tidak_match.geojson"
)