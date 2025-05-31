import os
import geopandas as gpd
from sfi import Macro


def gdf_to_dta(file, output):
    gdf = gpd.read_parquet(file)

    # Agrego Municipios
    gdf["geometry"] = gdf.centroid
    print(rf"{PATH_DATAIN}\departamentos.zip")
    departamentos = gpd.read_file(rf"{PATH_DATAIN}\departamento.zip")
    departamentos["nam"] = (
        departamentos["nam"]
        .str.normalize("NFKD")  # Remove accents
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
        .str.replace(".", "")  # Remove points
    )
    gdf = gdf.to_crs(epsg=4326).sjoin(departamentos[["geometry", "nam"]].to_crs(epsg=4326))

    # Formateo a Stata
    gdf = gdf.rename(columns={"nam": "departamento"})
    gdf = gdf.drop(
        columns=["geometry", "point", "link_polygon"], errors="ignore"
    )
    print(gdf.columns)
    gdf.to_stata(output)
    print("Se creó el archivo:", output)

    return


SAVENAME = Macro.getGlobal("SAVENAME")
PATH_DATAIN = Macro.getGlobal("PATH_DATAIN")
PATH_DATAOUT = Macro.getGlobal("PATH_DATAOUT")

# Datos censales
gdf_to_dta(file=rf"{PATH_DATAOUT}\small_area_estimates.parquet", output=rf"{PATH_DATAIN}/census_data.dta")

# Grilla de predicciones
for year in ["2013", "2018", "2022"]:
    # Importa grilla predicciones

    gdf_to_dta(
        file=rf"{PATH_DATAOUT}/predictions_grid_eph_income_estimates_{year}.parquet",
        output=rf"{PATH_DATAOUT}/gridded_data_{year}.dta",
    )
