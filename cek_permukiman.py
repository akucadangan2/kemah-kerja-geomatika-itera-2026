import geopandas as gpd

path = r"C:\3D_KADASTER\kirim\PERMUKIMAN_MERGE.shp"

gdf = gpd.read_file(path)

print("=" * 60)
print("PERMUKIMAN_MERGE")
print("=" * 60)

print("Jumlah feature :", len(gdf))
print("CRS            :", gdf.crs)

print("\nGeometry:")
print(gdf.geom_type.value_counts())

print("\nKolom:")
print(gdf.columns.tolist())

print("\nBounds:")
print(gdf.total_bounds)

print("\nValid :", gdf.is_valid.sum())
print("Invalid:", (~gdf.is_valid).sum())

print("\n5 atribut pertama:")
print(
    gdf.drop(columns="geometry")
       .head()
       .to_string()
)

if gdf.crs:
    wgs = gdf.to_crs(4326)

    print("\nBounds WGS84:")
    print(wgs.total_bounds)