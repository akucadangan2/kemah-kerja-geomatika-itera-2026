import pandas as pd

path = r"C:\3D_KADASTER\Kemker1.csv"

df = pd.read_csv(
    path,
    sep=";",
    encoding="cp1252"
)

# tampilkan sekitar data bermasalah
nomor = [126, 141, 230, 404, 526]

for n in nomor:
    print("\n" + "=" * 80)
    print("SEKITAR NOMOR", n)
    print("=" * 80)

    idx = df.index[df["Nomor"] == n]

    if len(idx):
        i = idx[0]

        print(
            df.iloc[max(0, i-3):i+4][
                [
                    "Nomor",
                    "ID Bangunan",
                    "Koordinat Latitude (Y)",
                    "Koordinat Longitude (X)",
                    "Fungsi Bangunan",
                    "Jumlah Lantai"
                ]
            ].to_string(index=False)
        )