import os
import geopandas as gpd
from sfi import Macro


def gdf_to_dta(file, output):
    file_path, extension = os.path.splitext(file)
    if extension == ".parquet":
        gdf = gpd.read_parquet(file)
    elif extension == ".feather":
        gdf = gpd.read_feather(file)
    else:
        gdf = gpd.read_file(file)

    # Agrego Municipios
    gdf["geometry"] = gdf.centroid
    departamentos = gpd.read_file(rf"{PATH_DATAIN}\departamentos.zip")
    departamentos["nam"] = (
        departamentos["nam"]
        .str.normalize("NFKD")  # Remove accents
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
        .str.replace(".", "")  # Remove points
    )
    gdf = gdf.sjoin(departamentos[["geometry", "nam"]])

    # Formateo a Stata
    gdf = gdf.rename(columns={"nam": "departamento"})
    gdf = gdf.drop(
        columns=["geometry", "point", "link_polygon", "bounds_geom"], errors="ignore"
    )
    print(gdf.columns)
    gdf.to_stata(output)
    print("Se creó el archivo:", output)

    return


SAVENAME = Macro.getGlobal("SAVENAME")
PATH_DATAIN = Macro.getGlobal("PATH_DATAIN")
PATH_DATAOUT = Macro.getGlobal("PATH_DATAOUT")
CENSUS_DATA = Macro.getGlobal("CENSUS_DATA")
GRID_PREDS_FOLDER = Macro.getGlobal("GRID_PREDS_FOLDER")

# Datos censales
print("CENSUS_DATA:", CENSUS_DATA)
gdf_to_dta(file=rf"{CENSUS_DATA}", output=rf"{PATH_DATAIN}/census_data.dta")

# Grilla de predicciones
for year in ["2013", "2018"]:
    # Importa grilla predicciones

    gdf_to_dta(
        file=rf"{PATH_DATAOUT}/predictions_grid_eph_{year}_{SAVENAME}.parquet",
        output=rf"{PATH_DATAOUT}/gridded_data_{year}_{SAVENAME}.dta",
    )
