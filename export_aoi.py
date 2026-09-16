import geopandas as gpd

INPUT = (
    r"C:\3D_KADASTER\SHP SIDODADI"
    r"\DESA_SIDODADI.shp"
)

OUTPUT = (
    r"C:\3D_KADASTER"
    r"\aoi_sidodadi.geojson"
)

aoi = gpd.read_file(INPUT)

print("CRS :", aoi.crs)
print("Feature :", len(aoi))

if not aoi.geometry.is_valid.all():
    aoi["geometry"] = aoi.geometry.buffer(0)

aoi = aoi.to_crs("EPSG:4326")

aoi.to_file(
    OUTPUT,
    driver="GeoJSON"
)

print("Selesai:")
print(OUTPUT)