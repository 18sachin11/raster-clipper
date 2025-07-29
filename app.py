# … earlier code up to reading shapefile …
# Read shapefile once (keep in its native CRS)
shapefile = gpd.read_file(shp_path)

# Then, inside your TIFF-processing loop:
for tif in tif_upload:
    tif_path = os.path.join(tmpdir, tif.name)
    with open(tif_path, "wb") as dst:
        dst.write(tif.getbuffer())

    with rasterio.open(tif_path) as src:
        # 1. Reproject shapefile geometries into the raster's CRS
        shp_in_raster_crs = shapefile.to_crs(src.crs)
        geoms = [feature.__geo_interface__ for feature in shp_in_raster_crs.geometry]

        # 2. Now mask should work without overlap errors
        out_image, out_transform = mask(src, geoms, crop=True)

        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })

        # write clipped raster into a MemoryFile
        memfile = rasterio.io.MemoryFile()
        with memfile.open(**out_meta) as dest:
            dest.write(out_image)
        clipped_bytes = memfile.read()
        memfile.close()

        zipf.writestr(f"clipped_{tif.name}", clipped_bytes)
