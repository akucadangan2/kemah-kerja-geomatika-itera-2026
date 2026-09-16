import geopandas as gpd
import pandas as pd
import numpy as np

POINT_FILE = r"C:\3D_KADASTER\bangunan.geojson"
FOOTPRINT_FILE = r"C:\3D_KADASTER\kirim\PERMUKIMAN_MERGE.shp"

OUTPUT_LOD1 = r"C:\3D_KADASTER\bangunan_lod1.geojson"
OUTPUT_UNMATCHED = r"C:\3D_KADASTER\bangunan_unmatched.geojson"
OUTPUT_CSV = r"C:\3D_KADASTER\hasil_matching.csv"

CRS_METRIC = "EPSG:32748"
MAX_DISTANCE = 15.0

FLOOR_HEIGHT = 4.0


# ============================================================
# LOAD
# ============================================================

points = gpd.read_file(POINT_FILE)
footprints = gpd.read_file(FOOTPRINT_FILE)

points = points.to_crs(CRS_METRIC)
footprints = footprints.to_crs(CRS_METRIC)

points = points.reset_index(drop=True)
points["point_id"] = points.index

footprints = footprints.reset_index(drop=True)
footprints["footprint_id"] = footprints.index + 1


# ============================================================
# FIX FOOTPRINT
# ============================================================

invalid = ~footprints.geometry.is_valid

if invalid.any():

    footprints.loc[
        invalid,
        "geometry"
    ] = footprints.loc[
        invalid,
        "geometry"
    ].buffer(0)


footprints = footprints[
    footprints.geometry.notna()
    & ~footprints.geometry.is_empty
].copy()


footprints["area_m2"] = (
    footprints.geometry.area
)


# centroid hanya untuk menentukan
# polygon terbaik jika overlap

footprints["centroid_geom"] = (
    footprints.geometry.centroid
)


# ============================================================
# STEP 1
# CARI POLYGON YANG MENGANDUNG TITIK
# ============================================================

inside = gpd.sjoin(
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


# ============================================================
# RESOLVE OVERLAP
#
# Jika satu titik masuk >1 polygon,
# pilih centroid polygon yang paling dekat.
# ============================================================

inside_valid = inside[
    inside["footprint_id"].notna()
].copy()


candidates = []


for point_index, group in inside_valid.groupby(level=0):

    point_geom = points.loc[
        point_index,
        "geometry"
    ]

    best = None
    best_distance = float("inf")

    for _, row in group.iterrows():

        footprint_id = int(
            row["footprint_id"]
        )

        footprint_row = footprints[
            footprints["footprint_id"]
            == footprint_id
        ].iloc[0]

        centroid = footprint_row[
            "centroid_geom"
        ]

        distance = point_geom.distance(
            centroid
        )

        if distance < best_distance:

            best_distance = distance

            best = {
                "point_id": point_index,
                "footprint_id": footprint_id,
                "jarak_meter": 0.0,
                "metode_match": "within",
                "centroid_distance": distance
            }

    candidates.append(best)


inside_final = pd.DataFrame(
    candidates
)


# ============================================================
# POINT YANG BELUM MATCH
# ============================================================

matched_point_ids = set(
    inside_final["point_id"]
) if len(inside_final) else set()


unmatched_points = points[
    ~points["point_id"].isin(
        matched_point_ids
    )
].copy()


# ============================================================
# STEP 2
# NEAREST UNTUK YANG TIDAK WITHIN
# ============================================================

nearest = gpd.sjoin_nearest(
    unmatched_points,
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


# kalau jaraknya sama ke beberapa polygon
# pilih satu saja

nearest = (
    nearest
    .sort_values("jarak_meter")
    .groupby("point_id")
    .first()
    .reset_index()
)


nearest["metode_match"] = np.where(
    nearest["jarak_meter"] <= MAX_DISTANCE,
    "nearest",
    "unmatched"
)


nearest_valid = nearest[
    nearest["jarak_meter"]
    <= MAX_DISTANCE
].copy()


# ============================================================
# GABUNGKAN HASIL MATCH
# ============================================================

nearest_result = nearest_valid[
    [
        "point_id",
        "footprint_id",
        "jarak_meter",
        "metode_match"
    ]
].copy()


inside_result = inside_final[
    [
        "point_id",
        "footprint_id",
        "jarak_meter",
        "metode_match"
    ]
].copy()


matches = pd.concat(
    [
        inside_result,
        nearest_result
    ],
    ignore_index=True
)


matches["footprint_id"] = (
    matches["footprint_id"].astype(int)
)


# ============================================================
# CEK DUPLIKAT FOOTPRINT
#
# Sangat penting:
# jangan sampai dua titik survei
# memakai footprint yang sama.
# ============================================================

matches = matches.merge(
    points[
        [
            "point_id",
            "geometry"
        ]
    ],
    on="point_id",
    how="left"
)


def distance_to_footprint_centroid(row):

    fp = footprints[
        footprints["footprint_id"]
        == row["footprint_id"]
    ].iloc[0]

    return row["geometry"].distance(
        fp["centroid_geom"]
    )


matches["selection_distance"] = (
    matches.apply(
        distance_to_footprint_centroid,
        axis=1
    )
)


# Prioritas:
# 1. within
# 2. nearest
# 3. jarak centroid terkecil

matches["priority"] = (
    matches["metode_match"]
    .map({
        "within": 0,
        "nearest": 1
    })
)


matches = matches.sort_values(
    [
        "footprint_id",
        "priority",
        "selection_distance"
    ]
)


# satu footprint = satu bangunan survei

duplicates = matches[
    matches.duplicated(
        "footprint_id",
        keep=False
    )
]


print()
print(
    "Konflik footprint:",
    len(
        duplicates[
            "footprint_id"
        ].unique()
    )
)


matches_unique = (
    matches
    .drop_duplicates(
        "footprint_id",
        keep="first"
    )
    .copy()
)


# ============================================================
# BUAT LOD1 DARI FOOTPRINT ASLI
# ============================================================

records = []


for _, match in matches_unique.iterrows():

    point_id = int(
        match["point_id"]
    )

    footprint_id = int(
        match["footprint_id"]
    )


    point = points[
        points["point_id"]
        == point_id
    ].iloc[0]


    footprint = footprints[
        footprints["footprint_id"]
        == footprint_id
    ].iloc[0]


    try:

        floor = int(
            point.get(
                "jumlah_lantai",
                1
            )
        )

    except:

        floor = 1


    if floor < 1:
        floor = 1


    record = {

        "point_id":
            point_id,

        "footprint_id":
            footprint_id,

        "id_bangunan":
            point.get(
                "id_bangunan"
            ),

        "fungsi_bangunan":
            point.get(
                "fungsi_bangunan"
            ),

        "jumlah_lantai":
            floor,

        "tinggi_lantai":
            FLOOR_HEIGHT,

        "tinggi_total":
            floor * FLOOR_HEIGHT,

        "luas_m2":
            round(
                footprint.geometry.area,
                2
            ),

        "metode_match":
            match["metode_match"],

        "jarak_match_m":
            round(
                float(
                    match["jarak_meter"]
                ),
                2
            ),

        "geometry":
            footprint.geometry
    }


    records.append(record)


lod1 = gpd.GeoDataFrame(
    records,
    geometry="geometry",
    crs=CRS_METRIC
)


# ============================================================
# UNMATCHED FINAL
# ============================================================

final_matched_ids = set(
    matches_unique["point_id"]
)


unmatched_final = points[
    ~points["point_id"].isin(
        final_matched_ids
    )
].copy()


# ============================================================
# EXPORT WGS84
# ============================================================

lod1_wgs = lod1.to_crs(
    "EPSG:4326"
)


lod1_wgs.to_file(
    OUTPUT_LOD1,
    driver="GeoJSON"
)


unmatched_wgs = unmatched_final.to_crs(
    "EPSG:4326"
)


unmatched_wgs.to_file(
    OUTPUT_UNMATCHED,
    driver="GeoJSON"
)


# ============================================================
# CSV REPORT
# ============================================================

report = lod1.drop(
    columns="geometry"
).copy()


report.to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("LOD1 SELESAI")
print("=" * 70)

print(
    "Total titik survei :",
    len(points)
)

print(
    "LOD1 berhasil      :",
    len(lod1)
)

print(
    "Within polygon     :",
    (
        lod1["metode_match"]
        == "within"
    ).sum()
)

print(
    "Nearest <= 15 m    :",
    (
        lod1["metode_match"]
        == "nearest"
    ).sum()
)

print(
    "Belum match        :",
    len(unmatched_final)
)

print()
print(
    "Bangunan 1 lantai  :",
    (
        lod1["jumlah_lantai"]
        == 1
    ).sum()
)

print(
    "Bangunan 2 lantai  :",
    (
        lod1["jumlah_lantai"]
        >= 2
    ).sum()
)

print()
print("Output:")
print(OUTPUT_LOD1)
print(OUTPUT_UNMATCHED)
print(OUTPUT_CSV)