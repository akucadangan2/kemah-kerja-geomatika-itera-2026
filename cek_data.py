import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

ROOT = Path(r"C:\3D_KADASTER")
SHP_DIR = ROOT / "SHP tsunami gempa"
CSV_FILE = ROOT / "TAKSONOMI20KELOMPOK20FIX.csv"


def garis(judul):
    print("\n" + "=" * 80)
    print(judul)
    print("=" * 80)


# ======================================================
# 1. SHAPEFILE (titik eksposur gempa & tsunami)
# ======================================================
for shp in sorted(SHP_DIR.glob("*.shp")):
    garis(f"SHAPEFILE: {shp.name}")
    try:
        gdf = gpd.read_file(shp)
        print("CRS            :", gdf.crs)
        print("Jumlah fitur   :", len(gdf))
        print("Tipe geometri  :", gdf.geom_type.value_counts().to_dict())
        print("Bounds (asli)  :", gdf.total_bounds.round(6).tolist())
        if gdf.crs is not None:
            print("Bounds (4326)  :", gdf.to_crs(4326).total_bounds.round(6).tolist())
        print("Geometri kosong:", int(gdf.geometry.is_empty.sum() + gdf.geometry.isna().sum()))
        print("\nKolom & tipe:")
        print(gdf.drop(columns="geometry").dtypes.to_string())
        print("\n5 baris pertama:")
        print(gdf.drop(columns="geometry").head().to_string())

        # Nilai unik untuk kolom kategori (maks 20)
        print("\nNilai unik kolom teks (maks 20):")
        for col in gdf.columns:
            if col == "geometry":
                continue
            if gdf[col].dtype == object:
                u = gdf[col].dropna().unique()
                print(f"  {col} ({len(u)} unik): {list(u[:20])}")
    except Exception as e:
        print("GAGAL:", e)


# ======================================================
# 2. RASTER (inundasi tsunami & kelas bahaya gempa)
# ======================================================
for tif in sorted(SHP_DIR.glob("*.tif")):
    garis(f"RASTER: {tif.name}")
    try:
        with rasterio.open(tif) as src:
            print("CRS        :", src.crs)
            print("Ukuran     :", src.width, "x", src.height, "piksel")
            print("Resolusi   :", src.res)
            print("Jumlah band:", src.count)
            print("Tipe data  :", src.dtypes)
            print("NoData     :", src.nodata)
            print("Bounds     :", [round(v, 6) for v in src.bounds])

            if src.crs is not None:
                from rasterio.warp import transform_bounds
                b4326 = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
                print("Bounds 4326:", [round(v, 6) for v in b4326])

            arr = src.read(1, masked=True)
            valid = arr.compressed()
            print("Piksel valid:", valid.size)

            if valid.size:
                print("Min / Max  :", float(valid.min()), "/", float(valid.max()))
                uniq = np.unique(valid)
                if uniq.size <= 30:
                    nilai, jml = np.unique(valid, return_counts=True)
                    print("Nilai unik (kategori):")
                    for n, j in zip(nilai, jml):
                        print(f"  {n}: {j} piksel")
                else:
                    print("Kontinu, jumlah nilai unik:", uniq.size)
                    print("Persentil 5/25/50/75/95:",
                          np.percentile(valid, [5, 25, 50, 75, 95]).round(3).tolist())
    except Exception as e:
        print("GAGAL:", e)

    # Tabel atribut raster (VAT), kalau ada
    vat = tif.with_suffix(".tif.vat.dbf")
    if vat.exists():
        print("\nTabel atribut raster (VAT):")
        try:
            print(gpd.read_file(vat).drop(columns="geometry", errors="ignore").to_string())
        except Exception as e:
            print("GAGAL baca VAT:", e)


# ======================================================
# 3. CSV TAKSONOMI
# ======================================================
garis(f"CSV: {CSV_FILE.name}")
df = None
for enc in ["utf-8-sig", "latin-1"]:
    try:
        df = pd.read_csv(CSV_FILE, sep=None, engine="python", encoding=enc)
        print("Encoding    :", enc)
        break
    except Exception as e:
        print(f"Gagal encoding {enc}:", e)

if df is not None:
    print("Baris x kolom:", df.shape)
    print("\nKolom & tipe:")
    print(df.dtypes.to_string())
    print("\n5 baris pertama:")
    print(df.head().to_string())
    print("\nKolom kosong per kolom:")
    print(df.isna().sum().to_string())

    # Cek kolom koordinat / ID untuk join
    kandidat = [c for c in df.columns
                if any(k in c.lower() for k in ["lat", "lon", "lng", "x", "y", "id", "bangunan", "kode"])]
    print("\nKandidat kolom koordinat/ID:", kandidat)
    for c in kandidat:
        print(f"  {c}: {df[c].nunique()} unik, contoh {df[c].dropna().head(3).tolist()}")


# ======================================================
# 4. GEOJSON BANGUNAN (untuk cek kecocokan join)
# ======================================================
for g in ROOT.rglob("bangunan_lod1_optimal.geojson"):
    garis(f"GEOJSON BANGUNAN: {g}")
    b = gpd.read_file(g)
    print("CRS   :", b.crs, "| fitur:", len(b))
    print("Kolom :", list(b.columns))
    if "id_bangunan" in b.columns:
        print("Contoh id_bangunan:", b["id_bangunan"].head(5).tolist())
    break

print("\nSELESAI")