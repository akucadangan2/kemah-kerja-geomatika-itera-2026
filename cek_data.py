import geopandas as gpd
import os

FILES = [
    r"C:\3D_KADASTER\kirim\PERMUKIMAN_MERGE.shp",
    r"C:\3D_KADASTER\SHP SIDODADI\DESA_SIDODADI.shp",
]

for shp in FILES:
    print("\n")
    print("=" * 80)
    print(os.path.basename(shp))
    print("=" * 80)

    try:
        gdf = gpd.read_file(shp)

        print("\n[INFO DASAR]")
        print("Path           :", shp)
        print("Jumlah feature :", len(gdf))
        print("CRS            :", gdf.crs)

        print("\n[GEOMETRY]")
        print("Geometry column:", gdf.geometry.name)
        print("Geometry type:")
        print(gdf.geom_type.value_counts(dropna=False))

        print("\n[BOUNDS]")
        print("minX, minY, maxX, maxY:")
        print(gdf.total_bounds)

        print("\n[VALIDITAS]")
        print("Geometry valid :", int(gdf.is_valid.sum()))
        print("Geometry invalid:", int((~gdf.is_valid).sum()))
        print("Geometry kosong:", int(gdf.geometry.is_empty.sum()))
        print("Geometry null  :", int(gdf.geometry.isna().sum()))

        print("\n[KOLOM]")
        for col in gdf.columns:
            print("-", col)

        print("\n[5 DATA PERTAMA]")
        print(gdf.head().to_string())

        # --------------------------------------------------
        # WGS84 untuk melihat lokasi sebenarnya
        # --------------------------------------------------

        if gdf.crs is not None:

            wgs = gdf.to_crs(epsg=4326)

            print("\n[BOUNDS WGS84]")
            print("Longitude/Latitude:")
            print(wgs.total_bounds)

            print("\n[CENTROID APPROX WGS84]")

            center_lon = (
                wgs.total_bounds[0]
                + wgs.total_bounds[2]
            ) / 2

            center_lat = (
                wgs.total_bounds[1]
                + wgs.total_bounds[3]
            ) / 2

            print("Longitude:", center_lon)
            print("Latitude :", center_lat)

        else:

            print("\nWARNING:")
            print("Shapefile tidak memiliki CRS.")

        # --------------------------------------------------
        # AREA jika polygon
        # --------------------------------------------------

        polygon_mask = gdf.geom_type.isin(
            ["Polygon", "MultiPolygon"]
        )

        if polygon_mask.any():

            print("\n[POLYGON]")

            try:

                # Kalau CRS geographic, pindahkan sementara
                # ke UTM berdasarkan lokasi dataset.

                wgs = gdf.to_crs(4326)

                centroid = wgs.geometry.union_all().centroid

                lon = centroid.x
                lat = centroid.y

                zone = int((lon + 180) / 6) + 1

                if lat >= 0:
                    epsg_utm = 32600 + zone
                else:
                    epsg_utm = 32700 + zone

                metric = gdf.to_crs(
                    epsg=epsg_utm
                )

                area = metric.geometry.area

                print(
                    "UTM analisis :",
                    f"EPSG:{epsg_utm}"
                )

                print(
                    "Luas minimum :",
                    round(area.min(), 2),
                    "m²"
                )

                print(
                    "Luas rata-rata:",
                    round(area.mean(), 2),
                    "m²"
                )

                print(
                    "Luas median  :",
                    round(area.median(), 2),
                    "m²"
                )

                print(
                    "Luas maksimum:",
                    round(area.max(), 2),
                    "m²"
                )

            except Exception as e:

                print(
                    "Gagal menghitung luas:",
                    e
                )

    except Exception as e:

        print("ERROR:")
        print(repr(e))


print("\n")
print("=" * 80)
print("SELESAI")
print("=" * 80)