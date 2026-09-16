import json
import os

output = r"C:\3D_KADASTER\gempa.geojson"

# Koordinat dari Data.xls
# Bujur   : 105°14'40"
# Lintang : 5°32'57" LS

longitude = 105 + (14 / 60) + (40 / 3600)
latitude = -(5 + (32 / 60) + (57 / 3600))

geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",

            "properties": {
                "jenis_data": "Parameter Bahaya Gempa",

                "pga": 0.0220,
                "ss": 0.0480,
                "s1": 0.0410,
                "tl": 4,

                "kelas_tanah": {
                    "SB": {
                        "T0": 0.13,
                        "Ts": 0.67,
                        "Sds": 0.03,
                        "Sd1": 0.02
                    },

                    "SC": {
                        "T0": 0.20,
                        "Ts": 1.00,
                        "Sds": 0.04,
                        "Sd1": 0.04
                    },

                    "SD": {
                        "T0": 0.28,
                        "Ts": 1.40,
                        "Sds": 0.05,
                        "Sd1": 0.07
                    },

                    "SE": {
                        "T0": 0.28,
                        "Ts": 1.38,
                        "Sds": 0.08,
                        "Sd1": 0.11
                    }
                }
            },

            "geometry": {
                "type": "Point",
                "coordinates": [
                    longitude,
                    latitude
                ]
            }
        }
    ]
}

with open(
    output,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        geojson,
        f,
        ensure_ascii=False,
        indent=2
    )

print("=" * 60)
print("GEMPA GEOJSON BERHASIL")
print("=" * 60)

print("Longitude :", longitude)
print("Latitude  :", latitude)

print("\nParameter:")
print("PGA :", 0.0220)
print("SS  :", 0.0480)
print("S1  :", 0.0410)
print("TL  :", 4)

print("\nOutput:")
print(output)