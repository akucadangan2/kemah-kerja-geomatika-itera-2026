import geopandas as gpd
import pandas as pd
import numpy as np

from scipy.optimize import linear_sum_assignment


# ============================================================
# CONFIG
# ============================================================

POINT_FILE = r"C:\3D_KADASTER\bangunan.geojson"
FOOTPRINT_FILE = r"C:\3D_KADASTER\kirim\PERMUKIMAN_MERGE.shp"

OUTPUT_LOD1 = r"C:\3D_KADASTER\bangunan_lod1_optimal.geojson"
OUTPUT_CSV = r"C:\3D_KADASTER\matching_optimal.csv"
OUTPUT_SUSPICIOUS = r"C:\3D_KADASTER\matching_perlu_cek.geojson"

CRS_METRIC = "EPSG:32748"

FLOOR_HEIGHT = 4.0

# hanya untuk FLAG QA, bukan untuk membuang
WARNING_DISTANCE = 15.0


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("ONE-TO-ONE OPTIMAL BUILDING MATCHING")
print("=" * 70)

points = gpd.read_file(
    POINT_FILE
).to_crs(CRS_METRIC)

footprints = gpd.read_file(
    FOOTPRINT_FILE
).to_crs(CRS_METRIC)


points = points.reset_index(drop=True)
footprints = footprints.reset_index(drop=True)

points["point_id"] = points.index

footprints["footprint_id"] = (
    footprints.index + 1
)


print("Titik survei :", len(points))
print("Footprint    :", len(footprints))


# ============================================================
# FIX INVALID GEOMETRY
# ============================================================

invalid = ~footprints.geometry.is_valid

print(
    "Invalid footprint sebelum fix:",
    invalid.sum()
)

if invalid.any():

    footprints.loc[
        invalid,
        "geometry"
    ] = (
        footprints.loc[
            invalid,
            "geometry"
        ]
        .buffer(0)
    )


footprints = footprints[
    footprints.geometry.notna()
    & ~footprints.geometry.is_empty
].copy()


print(
    "Invalid footprint setelah fix:",
    (~footprints.geometry.is_valid).sum()
)


# ============================================================
# HITUNG PROPERTI GEOMETRI
# ============================================================

footprints["area_m2"] = (
    footprints.geometry.area
)

footprints["centroid_geom"] = (
    footprints.geometry.centroid
)


# ============================================================
# COST MATRIX
#
# Cost = jarak titik ke GEOMETRY footprint,
# bukan hanya centroid.
#
# Jika titik berada di dalam polygon:
# distance = 0
#
# Untuk kasus sama-sama 0, kita tambahkan sedikit
# centroid distance sebagai tie-breaker.
# ============================================================

n_points = len(points)
n_footprints = len(footprints)

cost = np.zeros(
    (
        n_points,
        n_footprints
    ),
    dtype=np.float64
)

actual_distance = np.zeros_like(cost)


print()
print("Menghitung distance matrix...")


for i, point_geom in enumerate(
    points.geometry
):

    distances = (
        footprints.geometry
        .distance(point_geom)
        .to_numpy()
    )

    centroid_distances = (
        footprints["centroid_geom"]
        .distance(point_geom)
        .to_numpy()
    )

    actual_distance[i, :] = distances

    # distance geometry menjadi cost utama
    cost[i, :] = (
        distances
        + centroid_distances * 0.0001
    )

    if (
        (i + 1) % 50 == 0
        or i + 1 == n_points
    ):

        print(
            f"  {i + 1}/{n_points}"
        )


# ============================================================
# HUNGARIAN ASSIGNMENT
# ============================================================

print()
print("Menjalankan optimal assignment...")

row_ind, col_ind = (
    linear_sum_assignment(cost)
)


print(
    "Assignment selesai:",
    len(row_ind)
)


# ============================================================
# BUILD MATCH RESULT
# ============================================================

results = []


for point_idx, fp_idx in zip(
    row_ind,
    col_ind
):

    point = points.iloc[
        point_idx
    ]

    footprint = footprints.iloc[
        fp_idx
    ]

    distance = float(
        actual_distance[
            point_idx,
            fp_idx
        ]
    )

    centroid_distance = (
        point.geometry.distance(
            footprint["centroid_geom"]
        )
    )

    inside = (
        distance < 0.001
    )

    if inside:
        method = "within"
    else:
        method = "optimal_nearest"

    status = (
        "OK"
        if distance <= WARNING_DISTANCE
        else "PERLU_CEK"
    )

    results.append({

        "point_idx":
            point_idx,

        "point_id":
            int(point["point_id"]),

        "footprint_idx":
            fp_idx,

        "footprint_id":
            int(
                footprint[
                    "footprint_id"
                ]
            ),

        "jarak_meter":
            distance,

        "jarak_centroid":
            float(
                centroid_distance
            ),

        "metode_match":
            method,

        "status":
            status
    })


matches = pd.DataFrame(
    results
)


# ============================================================
# VALIDASI ONE TO ONE
# ============================================================

print()
print("=" * 70)
print("VALIDASI ASSIGNMENT")
print("=" * 70)

print(
    "Jumlah assignment:",
    len(matches)
)

print(
    "Point unik       :",
    matches["point_id"].nunique()
)

print(
    "Footprint unik   :",
    matches["footprint_id"].nunique()
)

print(
    "Duplicate point  :",
    matches["point_id"].duplicated().sum()
)

print(
    "Duplicate footprint:",
    matches["footprint_id"].duplicated().sum()
)


# ============================================================
# DISTRIBUSI JARAK
# ============================================================

print()
print("=" * 70)
print("DISTRIBUSI JARAK")
print("=" * 70)

print(
    matches["jarak_meter"]
    .describe()
    .round(2)
)


thresholds = [
    0.01,
    1,
    2,
    3,
    5,
    10,
    15,
    20,
    30,
    50,
    100
]


print()

for threshold in thresholds:

    count = (
        matches["jarak_meter"]
        <= threshold
    ).sum()

    print(
        f"<= {threshold:>6} m : "
        f"{count:>3} / {len(matches)}"
    )


# ============================================================
# BUAT LOD1
# ============================================================

records = []


for _, match in matches.iterrows():

    point = points.iloc[
        int(match["point_idx"])
    ]

    footprint = footprints.iloc[
        int(match["footprint_idx"])
    ]


    try:

        floors = int(
            point.get(
                "jumlah_lantai",
                1
            )
        )

    except:

        floors = 1


    if floors < 1:
        floors = 1


    records.append({

        "point_id":
            int(point["point_id"]),

        "footprint_id":
            int(
                footprint[
                    "footprint_id"
                ]
            ),

        "id_bangunan":
            point.get(
                "id_bangunan"
            ),

        "fungsi_bangunan":
            point.get(
                "fungsi_bangunan"
            ),

        "jumlah_lantai":
            floors,

        "tinggi_lantai":
            FLOOR_HEIGHT,

        "tinggi_total":
            floors * FLOOR_HEIGHT,

        "luas_m2":
            round(
                float(
                    footprint[
                        "area_m2"
                    ]
                ),
                2
            ),

        "jarak_match_m":
            round(
                float(
                    match[
                        "jarak_meter"
                    ]
                ),
                2
            ),

        "metode_match":
            match[
                "metode_match"
            ],

        "status_match":
            match[
                "status"
            ],

        "geometry":
            footprint.geometry
    })


lod1 = gpd.GeoDataFrame(
    records,
    geometry="geometry",
    crs=CRS_METRIC
)


# ============================================================
# EXPORT LOD1
# ============================================================

lod1_wgs = lod1.to_crs(
    "EPSG:4326"
)

lod1_wgs.to_file(
    OUTPUT_LOD1,
    driver="GeoJSON"
)


# ============================================================
# EXPORT CSV
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
# SUSPICIOUS MATCHES
# ============================================================

suspicious = lod1[
    lod1["status_match"]
    == "PERLU_CEK"
].copy()


if len(suspicious) > 0:

    suspicious.to_crs(
        "EPSG:4326"
    ).to_file(
        OUTPUT_SUSPICIOUS,
        driver="GeoJSON"
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 70)
print("HASIL FINAL")
print("=" * 70)

print(
    "LOD1 total        :",
    len(lod1)
)

print(
    "Bangunan 1 lantai:",
    (
        lod1["jumlah_lantai"]
        == 1
    ).sum()
)

print(
    "Bangunan 2 lantai:",
    (
        lod1["jumlah_lantai"]
        == 2
    ).sum()
)

print(
    "Match <= 15 m     :",
    (
        lod1["jarak_match_m"]
        <= WARNING_DISTANCE
    ).sum()
)

print(
    "Perlu cek > 15 m  :",
    (
        lod1["jarak_match_m"]
        > WARNING_DISTANCE
    ).sum()
)


print()
print("10 MATCH TERJAUH:")

print(
    lod1[
        [
            "id_bangunan",
            "fungsi_bangunan",
            "jumlah_lantai",
            "footprint_id",
            "jarak_match_m"
        ]
    ]
    .sort_values(
        "jarak_match_m",
        ascending=False
    )
    .head(10)
    .to_string(index=False)
)


print()
print("Output:")
print(OUTPUT_LOD1)
print(OUTPUT_CSV)

if len(suspicious) > 0:
    print(OUTPUT_SUSPICIOUS)