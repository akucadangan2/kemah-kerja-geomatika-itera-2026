import json
import math
import os

INPUT_FILE = r"C:\3D_KADASTER\bangunan.geojson"
OUTPUT_FILE = r"C:\3D_KADASTER\bangunan_lod1.geojson"

# Ukuran footprint sementara
BUILDING_SIZE = 10  # meter

# Tinggi setiap lantai
FLOOR_HEIGHT = 4  # meter


def create_square(lon, lat, size_meter):
    """
    Membuat polygon kotak dengan titik bangunan
    sebagai pusatnya.
    """

    half = size_meter / 2

    # konversi meter -> derajat
    lat_offset = half / 111320

    lon_offset = half / (
        111320 * math.cos(math.radians(lat))
    )

    return [
        [lon - lon_offset, lat - lat_offset],
        [lon + lon_offset, lat - lat_offset],
        [lon + lon_offset, lat + lat_offset],
        [lon - lon_offset, lat + lat_offset],
        [lon - lon_offset, lat - lat_offset]
    ]


with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)


features = []


for feature in data["features"]:

    geometry = feature.get("geometry")

    if not geometry:
        continue

    if geometry["type"] != "Point":
        continue


    lon, lat = geometry["coordinates"]

    properties = feature.get(
        "properties",
        {}
    ).copy()


    try:
        jumlah_lantai = int(
            properties.get(
                "jumlah_lantai",
                1
            )
        )
    except:
        jumlah_lantai = 1


    # minimal 1 lantai
    if jumlah_lantai < 1:
        jumlah_lantai = 1


    footprint = create_square(
        lon,
        lat,
        BUILDING_SIZE
    )


    properties[
        "tinggi_lantai"
    ] = FLOOR_HEIGHT


    properties[
        "tinggi_total"
    ] = (
        jumlah_lantai
        * FLOOR_HEIGHT
    )


    properties[
        "footprint_estimasi"
    ] = True


    new_feature = {

        "type": "Feature",

        "properties": properties,

        "geometry": {

            "type": "Polygon",

            "coordinates": [
                footprint
            ]
        }
    }


    features.append(
        new_feature
    )


output = {

    "type": "FeatureCollection",

    "features": features
}


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


print("=" * 60)
print("LOD1 GEOJSON BERHASIL")
print("=" * 60)

print(
    f"Jumlah bangunan : {len(features)}"
)

print(
    f"Ukuran footprint: {BUILDING_SIZE} x {BUILDING_SIZE} meter"
)

print(
    f"Tinggi lantai   : {FLOOR_HEIGHT} meter"
)

print()
print("Output:")
print(OUTPUT_FILE)