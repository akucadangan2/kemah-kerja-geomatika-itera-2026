import pandas as pd
import json
import os

input_file = r"C:\3D_KADASTER\Kemker1.csv"

output_all = r"C:\3D_KADASTER\bangunan.geojson"
output_1 = r"C:\3D_KADASTER\bangunan_1_lantai.geojson"
output_2 = r"C:\3D_KADASTER\bangunan_2_lantai.geojson"
output_clean = r"C:\3D_KADASTER\Kemker1_clean.csv"

# =========================================================
# BACA DATA
# =========================================================

df = pd.read_csv(
    input_file,
    sep=";",
    encoding="cp1252"
)

lat_col = "Koordinat Latitude (Y)"
lon_col = "Koordinat Longitude (X)"

print("Jumlah data awal:", len(df))


# =========================================================
# BERSIHKAN STRING
# =========================================================

df[lat_col] = (
    df[lat_col]
    .astype(str)
    .str.strip()
)

df[lon_col] = (
    df[lon_col]
    .astype(str)
    .str.strip()
    .str.replace("/", "", regex=False)
)


# =========================================================
# UBAH KE NUMERIC
# =========================================================

df[lat_col] = pd.to_numeric(
    df[lat_col],
    errors="coerce"
)

df[lon_col] = pd.to_numeric(
    df[lon_col],
    errors="coerce"
)


# =========================================================
# PERBAIKAN DATA YANG SUDAH TERIDENTIFIKASI
# =========================================================

corrections = {
    126: {
        lon_col: 105.229219
    },
    141: {
        lat_col: -5.548319
    },
    230: {
        lat_col: -5.552295
    },
    404: {
        lat_col: -5.551036
    },
    526: {
        lat_col: -5.553730,
        lon_col: 105.241100
    }
}

for nomor, values in corrections.items():

    mask = df["Nomor"] == nomor

    for column, value in values.items():
        df.loc[mask, column] = value


# =========================================================
# VALIDASI
# =========================================================

invalid = df[
    (df[lat_col] < -6) |
    (df[lat_col] > -5) |
    (df[lon_col] < 104) |
    (df[lon_col] > 106) |
    df[lat_col].isna() |
    df[lon_col].isna()
]

print("\n========================================")
print("VALIDASI KOORDINAT")
print("========================================")

if len(invalid) == 0:
    print("SEMUA KOORDINAT VALID")
else:
    print("Masih ditemukan koordinat bermasalah:")
    print(invalid.to_string(index=False))


# =========================================================
# SIMPAN CSV BERSIH
# =========================================================

df.to_csv(
    output_clean,
    index=False,
    encoding="utf-8-sig"
)

print("\nCSV bersih:")
print(output_clean)


# =========================================================
# FUNCTION GEOJSON
# =========================================================

def dataframe_to_geojson(dataframe):

    features = []

    for _, row in dataframe.iterrows():

        feature = {
            "type": "Feature",

            "properties": {
                "nomor": int(row["Nomor"]),
                "id_bangunan": str(row["ID Bangunan"]),
                "fungsi_bangunan": str(row["Fungsi Bangunan"]),
                "jumlah_lantai": int(row["Jumlah Lantai"])
            },

            "geometry": {
                "type": "Point",

                # GeoJSON = Longitude, Latitude
                "coordinates": [
                    float(row[lon_col]),
                    float(row[lat_col])
                ]
            }
        }

        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


# =========================================================
# SEMUA BANGUNAN
# =========================================================

geojson_all = dataframe_to_geojson(df)

with open(
    output_all,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        geojson_all,
        f,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# BANGUNAN 1 LANTAI
# =========================================================

df_1 = df[
    df["Jumlah Lantai"] == 1
].copy()

geojson_1 = dataframe_to_geojson(df_1)

with open(
    output_1,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        geojson_1,
        f,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# BANGUNAN 2 LANTAI
# =========================================================

df_2 = df[
    df["Jumlah Lantai"] == 2
].copy()

geojson_2 = dataframe_to_geojson(df_2)

with open(
    output_2,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        geojson_2,
        f,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# HASIL
# =========================================================

print("\n========================================")
print("SELESAI")
print("========================================")

print("Total bangunan :", len(df))
print("1 lantai       :", len(df_1))
print("2 lantai       :", len(df_2))

print("\nFile:")
print(output_all)
print(output_1)
print(output_2)