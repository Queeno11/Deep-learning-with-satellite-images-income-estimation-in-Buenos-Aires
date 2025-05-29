from sfi import Macro
import os
import numpy as np
import xarray as xr
import geopandas as gpd

SAVENAME = Macro.getGlobal("SAVENAME")
PATH_DATAIN = Macro.getGlobal("PATH_DATAIN")
PATH_DATAOUT = Macro.getGlobal("PATH_DATAOUT")
CENSUS_DATA = Macro.getGlobal("CENSUS_DATA")
GRID_PREDS_FOLDER = Macro.getGlobal("GRID_PREDS_FOLDER")

# Importa icpag
icpag = gpd.read_file(rf"{CENSUS_DATA}")
icpag = icpag.loc[icpag.eph_aglome.isin(["Partidos del GBA", "CABA"])]

for year in ["2013", "2018"]:
    # Importa grilla predicciones
    if year == "2013":
        grid_predictions_file = os.listdir(rf"{GRID_PREDS_FOLDER}/{SAVENAME}")[0]
    else:
        grid_predictions_files = os.listdir(rf"{GRID_PREDS_FOLDER}/{SAVENAME}")
        grid_predictions_file = [f for f in grid_predictions_files if year in f][0]

    print("Se va a utilizar la siguiente grilla:", grid_predictions_file)
    grid = gpd.read_parquet(rf"{GRID_PREDS_FOLDER}\{SAVENAME}\{grid_predictions_file}")
    grid = grid.drop(columns="index_right")

    # Assigna cantidad de personas en censo a la grilla (en procesa base calculo el share de gente)
    eph_grid = grid.sjoin(icpag[["geometry", "personas"]])
    eph_grid = eph_grid.drop_duplicates(subset="id", keep="first").drop(
        columns="index_right"
    )
    oeste, sur, este, norte = eph_grid.total_bounds

    # Importa WSF para filtrar dónde hay gente
    wsf_ds = xr.open_dataset(
        r"D:\Maestría\Tesis\Repo\data\data_in\WSF 2015 - Urbanizacion\WSF 2015 AMBA.tif"
    )
    wsf_ds = wsf_ds.sel(x=slice(oeste, este), y=slice(norte, sur))
    wsf_df = wsf_ds["band_data"].sel(band=1).to_dataframe().reset_index()
    wsf_df = wsf_df.dropna()
    wsf2015_gdf = gpd.GeoDataFrame(
        wsf_df.band_data, geometry=gpd.points_from_xy(wsf_df.x, wsf_df.y)
    )

    # Solo me quedo con los polígonos de la grilla que tienen gente
    areas_with_people = eph_grid.sjoin(wsf2015_gdf.set_crs(epsg=4326))
    areas_with_people = areas_with_people.drop_duplicates(subset="id")
    areas_with_people = areas_with_people[
        [
            "id",
            "link",
            "bounds_geom",
            "dataset",
            "real_value",
            "prediction",
            "prediction_error",
            "personas",
        ]
    ]
    areas_with_people.to_parquet(
        rf"{PATH_DATAOUT}\predictions_grid_eph_{year}_{SAVENAME}.parquet"
    )
