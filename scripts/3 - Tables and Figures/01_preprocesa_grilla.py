from sfi import Macro
import os
import numpy as np
import xarray as xr
import geopandas as gpd

PATH_DATAIN = Macro.getGlobal("PATH_DATAIN")
PATH_DATAOUT = Macro.getGlobal("PATH_DATAOUT")

# Importa gdf
gdf = gpd.read_file(rf"{PATH_DATAIN}\radios_eph_with_link.shp")
gdf = gdf.loc[gdf.eph_aglome.isin(["Partidos del GBA", "CABA"])]
gdf = gdf.to_crs(epsg=4326)

for year in ["2013", "2018", "2022"]:
    # Importa grilla predicciones
    grid = gpd.read_file(rf"{PATH_DATAIN}\income_estimates_{year}.shp")

    # Assigna cantidad de personas en censo a la grilla (en procesa base calculo el share de gente)
    eph_grid = grid.sjoin(gdf[["geometry", "personas"]])
    eph_grid = eph_grid.drop_duplicates(subset="id", keep="first").drop(
        columns="index_right"
    )
    oeste, sur, este, norte = eph_grid.total_bounds

    # Importa WSF para filtrar dónde hay gente
    wsf_ds = xr.open_dataset(
        rf"{PATH_DATAIN}\WSF2015_v2_-60_-36.tif"
    ) # Dataset can be downloaded from: https://download.geoservice.dlr.de/WSF2015/
    wsf_ds = wsf_ds.sel(x=slice(oeste, este), y=slice(norte, sur))
    wsf_df = wsf_ds["band_data"].sel(band=1).to_dataframe().reset_index()
    wsf_df = wsf_df.dropna()
    wsf2015_gdf = gpd.GeoDataFrame(
        wsf_df.band_data, geometry=gpd.points_from_xy(wsf_df.x, wsf_df.y)
    )

    # Solo me quedo con los polígonos de la grilla que tienen gente
    areas_with_people = eph_grid.to_crs(epsg=4326).sjoin(wsf2015_gdf.set_crs(epsg=4326))
    areas_with_people = areas_with_people[areas_with_people.band_data>0]
    areas_with_people = areas_with_people.drop_duplicates(subset="id")
    print(areas_with_people.active_geometry_name)
    areas_with_people = areas_with_people[
        [
            "id",
            "link",
            "real_value",
            "prediction",
            "personas",
            "geometry"
        ]
    ]
    
    # Elimino predicciones nulas (imágenes negras) - Es la moda porque el único valor que se repite exactamente igual muchas veces es el nulo
    areas_with_people = areas_with_people[areas_with_people.prediction != areas_with_people.prediction.mode()[0]]
    print(f"Cantidad de áreas con gente en {year}: {len(areas_with_people)}")
    areas_with_people.to_parquet(
        rf"{PATH_DATAOUT}\predictions_grid_eph_income_estimates_{year}.parquet"
    )
