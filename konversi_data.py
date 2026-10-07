import json
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from PIL import Image
from pyproj import Transformer
from shapely.geometry import shape
from rasterio.features import shapes
from rasterio.warp import calculate_default_transform, reproject, Resampling

ROOT = Path(r"C:\3D_KADASTER")
SHP_DIR = ROOT / "SHP tsunami gempa"
CSV_FILE = ROOT / "TAKSONOMI20KELOMPOK20FIX.csv"
BANGUNAN_IN = ROOT / "bangunan_lod1_optimal.geojson"
OUT = ROOT

KELAS_GEMPA_RASTER = {1: "Rendah", 2: "Sedang", 3: "Tinggi"}
KELAS_LUAR = "Tidak Terdampak"
BUANG_PUTIH = False  # set True kalau PNG inundasi muncul kotak putih


def simpan(gdf, path):
    if path.exists():
        path.unlink()
    gdf.to_file(path, driver="GeoJSON", COORDINATE_PRECISION=7)
    print(f"  -> {path.name} ({len(gdf)} fitur, {path.stat().st_size / 1024:.0f} KB)")


# ======================================================
# 1. TITIK EKSPOSUR (gempa & tsunami)
# ======================================================
KOLOM_TITIK = [
    "ID_BGN", "KELAS", "BLOK", "FUNGSI", "KLS_6", "JML_LNT1",
    "MAT_DOM", "STR_TAMP", "KONDISI", "TAXONOMI", "LUAS_M2", "N_EXP",
]


def proses_titik(nama_shp, nama_out):
    print(f"\n[TITIK] {nama_shp}")
    gdf = gpd.read_file(SHP_DIR / nama_shp).to_crs(4326)

    x = gdf.geometry.x.values
    y = gdf.geometry.y.values
    salah = y > 0
    if salah.any():
        print("  Latitude positif, dibalik:", gdf.loc[salah, "ID_BGN"].tolist())
        y = np.where(salah, -y, y)

    gdf = gpd.GeoDataFrame(
        gdf[KOLOM_TITIK].copy(),
        geometry=gpd.points_from_xy(x, y),
        crs=4326,
    )
    gdf["ID_BGN"] = gdf["ID_BGN"].astype(str).str.strip()
    gdf["KELAS"] = (
        gdf["KELAS"].astype(str).str.strip()
        .replace({"0": KELAS_LUAR, "None": KELAS_LUAR, "nan": KELAS_LUAR, "": KELAS_LUAR})
    )

    dup = gdf.loc[gdf["ID_BGN"].duplicated(), "ID_BGN"].unique().tolist()
    if dup:
        print(f"  ID duplikat ({len(dup)}):", dup)
    print("  Sebaran KELAS:", gdf["KELAS"].value_counts().to_dict())

    simpan(gdf, OUT / nama_out)
    return gdf


# ======================================================
# 2. ZONA BAHAYA GEMPA (raster kategori -> poligon)
# ======================================================
def proses_zona_gempa():
    print("\n[RASTER] Kelas_Bahaya_Gempa1.tif -> poligon")
    with rasterio.open(SHP_DIR / "Kelas_Bahaya_Gempa1.tif") as src:
        arr = src.read(1)
        mask = arr != src.nodata
        rows = [
            {"kelas_kode": int(v), "geometry": shape(g)}
            for g, v in shapes(arr, mask=mask, transform=src.transform)
        ]
        crs = src.crs

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=crs)
    gdf = gdf.dissolve(by="kelas_kode", as_index=False)
    gdf["luas_ha"] = (gdf.area / 10000).round(2)
    gdf["kelas"] = gdf["kelas_kode"].map(KELAS_GEMPA_RASTER)
    gdf = gdf.to_crs(4326)[["kelas_kode", "kelas", "luas_ha", "geometry"]]

    print("  Luas per kelas (ha):", dict(zip(gdf["kelas"], gdf["luas_ha"])))
    simpan(gdf, OUT / "bahaya_gempa.geojson")


# ======================================================
# 3. INUNDASI TSUNAMI (RGBA -> PNG overlay)
# ======================================================
def proses_inundasi():
    print("\n[RASTER] inunsidodadi1.tif -> PNG overlay")
    dst_crs = "EPSG:3857"

    with rasterio.open(SHP_DIR / "inunsidodadi1.tif") as src:
        nodata = src.nodata
        transform, w, h = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        out = np.full((src.count, h, w), nodata, dtype=np.uint32)
        for i in range(src.count):
            reproject(
                source=rasterio.band(src, i + 1),
                destination=out[i],
                src_transform=src.transform,
                src_crs=src.crs,
                src_nodata=nodata,
                dst_transform=transform,
                dst_crs=dst_crs,
                dst_nodata=nodata,
                resampling=Resampling.nearest,
            )

    valid = np.all(out[:3] != nodata, axis=0)
    rgb = np.clip(out[:3], 0, 255).astype(np.uint8)

    if out.shape[0] >= 4:
        alpha_src = np.clip(out[3], 0, 255).astype(np.uint8)
        print("  Nilai band 4:", np.unique(alpha_src[valid])[:10].tolist())
    else:
        alpha_src = np.full((h, w), 255, np.uint8)

    alpha = np.where(valid, alpha_src, 0).astype(np.uint8)

    putih = valid & np.all(rgb >= 250, axis=0)
    print(f"  Piksel hampir putih: {putih.sum()} dari {valid.sum()} piksel valid")
    if BUANG_PUTIH:
        alpha[putih] = 0

    png_path = OUT / "inundasi_tsunami.png"
    Image.fromarray(np.dstack([rgb[0], rgb[1], rgb[2], alpha])).save(png_path)

    left, top = transform.c, transform.f
    right = left + transform.a * w
    bottom = top + transform.e * h
    tf = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    corners = [
        tf.transform(left, top),
        tf.transform(right, top),
        tf.transform(right, bottom),
        tf.transform(left, bottom),
    ]

    meta = {
        "image": "./inundasi_tsunami.png",
        "coordinates": [[round(x, 7), round(y, 7)] for x, y in corners],
    }
    (OUT / "inundasi_tsunami.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"  -> inundasi_tsunami.png ({w}x{h}) + inundasi_tsunami.json")


# ======================================================
# 4. BANGUNAN + CSV TAKSONOMI + KELAS BAHAYA
# ======================================================
RENAME_CSV = {
    "ID Bangunan": "id_bangunan",
    "Blok": "blok",
    "Klasifikasi Fungsi": "klas_fungsi",
    "Material Dominan": "material",
    "Sistem Stuktur Tampak": "struktur",
    "Tipe Atap": "tipe_atap",
    "Material Penutup Atap": "penutup_atap",
    "Dinding Luar": "dinding",
    "Kondisi Visual": "kondisi",
    "Tingkat Keyakinan": "keyakinan",
    "TAKSONOMI": "taksonomi",
    "KODE SIGKAT": "kode_singkat",
    "Koefisien": "koefisien",
    "Nilai Exposure": "nilai_exposure",
    "Klasifikasi Rentang Exposure": "kelas_exposure",
}


def proses_bangunan(titik_gempa, titik_tsunami):
    print("\n[BANGUNAN] join CSV taksonomi + kelas bahaya")
    bgn = gpd.read_file(BANGUNAN_IN)
    bgn["id_bangunan"] = bgn["id_bangunan"].astype(str).str.strip()

    csv = pd.read_csv(CSV_FILE, sep=None, engine="python", encoding="utf-8-sig")
    csv.columns = csv.columns.str.strip()
    csv = csv.rename(columns=RENAME_CSV)[list(RENAME_CSV.values())]
    for c in csv.select_dtypes(include="object").columns:
        csv[c] = csv[c].astype(str).str.strip().replace({"nan": None})

    dup = csv.loc[csv["id_bangunan"].duplicated(), "id_bangunan"].unique().tolist()
    if dup:
        print(f"  ID duplikat di CSV ({len(dup)}), diambil baris pertama:", dup)
    csv = csv.drop_duplicates("id_bangunan", keep="first")

    # Urutan kelas exposure (1 = terendah)
    urut = csv.groupby("kelas_exposure")["nilai_exposure"].min().sort_values()
    rank = {k: i + 1 for i, k in enumerate(urut.index)}
    csv["exposure_rank"] = csv["kelas_exposure"].map(rank)
    print("  Rank exposure:", rank)

    bgn = bgn.merge(csv, on="id_bangunan", how="left")
    bgn["exposure_rank"] = bgn["exposure_rank"].fillna(0).astype(int)

    tanpa_csv = bgn["taksonomi"].isna().sum()
    print(f"  Bangunan tanpa data CSV: {tanpa_csv} dari {len(bgn)}")

    for kolom, titik in [("kelas_gempa", titik_gempa), ("kelas_tsunami", titik_tsunami)]:
        peta = titik.drop_duplicates("ID_BGN").set_index("ID_BGN")["KELAS"]
        bgn[kolom] = bgn["id_bangunan"].map(peta).fillna("Tidak Ada Data")
        print(f"  {kolom}:", bgn[kolom].value_counts().to_dict())

    simpan(bgn, OUT / "bangunan_lod1_risiko.geojson")


if __name__ == "__main__":
    tg = proses_titik("titikexpo_gempa.shp", "titik_expo_gempa.geojson")
    tt = proses_titik("titikexpo_tsunami.shp", "titik_expo_tsunami.geojson")
    proses_zona_gempa()
    proses_inundasi()
    proses_bangunan(tg, tt)
    print("\nSELESAI")