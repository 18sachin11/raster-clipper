import streamlit as st
import geopandas as gpd
import rasterio
from rasterio.mask import mask
import tempfile, os, io, zipfile

st.set_page_config(page_title="Raster Clipper", layout="wide")
st.title("🌍 Raster Clipper Web App")

st.markdown("""
Upload all shapefile components (​.shp, ​.shx, ​.dbf, ​.prj) together, then select one or more GeoTIFFs to clip.  
Click **Clip Rasters** to process, and download a ZIP of all clipped outputs.
""")

# 1. Upload shapefile parts
shp_upload = st.file_uploader(
    "1. Upload shapefile components",
    type=["shp","shx","dbf","prj"],
    accept_multiple_files=True
)

# 2. Upload TIFFs
tif_upload = st.file_uploader(
    "2. Upload GeoTIFF files to clip",
    type="tif",
    accept_multiple_files=True
)

# 3. Trigger processing
if st.button("▶ Clip Rasters"):
    if not shp_upload or not tif_upload:
        st.error("Please upload **both** shapefile components and TIFF files.")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            # a) Save shapefile components to temp
            for f in shp_upload:
                with open(os.path.join(tmpdir, f.name), "wb") as dst:
                    dst.write(f.getbuffer())

            # b) Find the .shp file path
            shapefile_paths = [os.path.join(tmpdir, f.name) for f in shp_upload]
            shp_path = next(path for path in shapefile_paths if path.lower().endswith(".shp"))

            # c) Read shapefile and extract geometries
            shapefile = gpd.read_file(shp_path).to_crs("EPSG:4326")
            geoms = [feat.__geo_interface__ for feat in shapefile.geometry]

            # d) Prepare in-memory ZIP
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zipf:
                # process each uploaded TIFF
                for tif in tif_upload:
                    tif_path = os.path.join(tmpdir, tif.name)
                    with open(tif_path, "wb") as dst:
                        dst.write(tif.getbuffer())

                    with rasterio.open(tif_path) as src:
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

                        # add to ZIP
                        zipf.writestr(f"clipped_{tif.name}", clipped_bytes)

            zip_buf.seek(0)
            st.success("✅ Clipping complete!")
            st.download_button(
                "📥 Download All Clipped TIFFs",
                data=zip_buf,
                file_name="clipped_tifs.zip",
                mime="application/zip"
            )
