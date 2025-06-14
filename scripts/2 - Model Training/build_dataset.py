##############      Configuración      ##############
import os
import pickle
import pandas as pd
import geopandas as gpd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict
from PIL import Image
from dotenv import dotenv_values

pd.set_option("display.max_columns", None)

envpath = r"/mnt/d/Maestría/Tesis/Repo/scripts/globals.env"
if os.path.isfile(envpath):
    env = dotenv_values(envpath)
else:
    env = dotenv_values(r"D:\Maestría\Tesis\Repo\scripts\globals_win.env")

path_datain = env["PATH_DATAIN"]
path_dataout = env["PATH_DATAOUT"]
path_scripts = env["PATH_SCRIPTS"]
path_satelites = env["PATH_SATELITES"]
path_nocturnas = env["PATH_NOCTURNAS"]
path_landsat = env["PATH_LANDSAT"]
path_logs = env["PATH_LOGS"]
path_outputs = env["PATH_OUTPUTS"]
path_imgs = env["PATH_IMGS"]
# path_programas  = globales[7]

import affine
import geopandas as gpd
import rasterio.features
import xarray as xr
import rioxarray as xrx
import shapely.geometry as sg
import pandas as pd
from tqdm import tqdm
import utils
import true_metrics


def load_satellite_datasets(year=2013, stretch=False):
    """Load satellite datasets and get their extents"""
    print(rf"{path_satelites}/{year}")

    if not os.path.isdir(rf"{path_satelites}/{year}"):
        raise ValueError(f"Year {year} images not found. Check they are stored in WSL!")

    files = os.listdir(rf"{path_satelites}/{year}")
    files = [f for f in files if f.endswith(".tif")]
    assert all([os.path.isfile(rf"{path_satelites}/{year}/{f}") for f in files])

    datasets = {
        f.replace(".tif", ""): (filter_black_pixels(xr.open_dataset(rf"{path_satelites}/{year}/{f}")))
        for f in files
    }
    
    
    # Round x and y to 6 decimals
    for name, dataset in datasets.items():
        dataset["x"] = dataset["x"].round(6)
        dataset["y"] = dataset["y"].round(6)

    if stretch:
        datasets = {name: stretch_dataset(ds) for name, ds in datasets.items()}

    extents = {name: utils.get_dataset_extent(ds) for name, ds in datasets.items()}

    return datasets, extents


def load_satellite_mfdatasets(year=2013, stretch=False):
    """Load satellite datasets and get their extents"""
    print(rf"{path_satelites}/{year}")
    import warnings

    warnings.simplefilter("ignore")

    if not os.path.isdir(rf"{path_satelites}/{year}"):
        raise ValueError(f"Year {year} images not found. Check they are stored in WSL!")

    files = os.listdir(rf"{path_satelites}/{year}")
    files = [f for f in files if f.endswith(".tif")]
    capture_ids = set([f.split("_")[1] for f in files])

    assert all([os.path.isfile(rf"{path_satelites}/{year}/{f}") for f in files])

    files_by_id = {}
    datasets = {}
    for capture_id in capture_ids:
        # for capture_id, files in files_by_id.items():
        id_files = [rf"{path_satelites}/{year}/{f}" for f in files if capture_id in f]
        id_files_matrix = generate_matrix_of_files(id_files)
        ds = xr.open_mfdataset(
            id_files_matrix,
            combine="nested",
            concat_dim=["x", "y"],
            engine="rasterio",
            chunks={"x": 1000, "y": 1000},
        )

        if stretch:
            print(
                "Warning: Stretching dataset might not be compatible with new loading method..."
            )
            ds = stretch_dataset(ds)

        datasets[capture_id] = ds

    extents = {name: utils.get_dataset_extent(ds, 512) for name, ds in datasets.items()}

    return datasets, extents


def load_landsat_datasets(stretch=False):
    """Load satellite datasets and get their extents"""

    files = os.listdir(rf"{path_landsat}")
    assert os.path.isdir(rf"{path_landsat}")
    files = [f for f in files if f.endswith(".tif")]
    assert all([os.path.isfile(rf"{path_landsat}/{f}") for f in files])

    datasets = {
        f.replace(".tif", ""): (
            normalize_landsat(xr.open_dataset(rf"{path_landsat}/{f}"))
        )
        for f in files
    }
    if stretch:
        datasets = {name: stretch_dataset(ds) for name, ds in datasets.items()}

    extents = {name: utils.get_dataset_extent(ds) for name, ds in datasets.items()}

    return datasets, extents


def load_nightlight_datasets(stretch=False):
    """Load satellite datasets and get their extents"""

    files = os.listdir(rf"{path_nocturnas}")
    assert os.path.isdir(rf"{path_nocturnas}")
    files = [f for f in files if f.endswith(".tif")]
    assert all([os.path.isfile(rf"{path_nocturnas}/{f}") for f in files])

    datasets = {
        f.replace(".tif", ""): (xr.open_dataset(rf"{path_nocturnas}/{f}"))
        for f in files
    }
    if stretch:
        datasets = {name: stretch_dataset(ds) for name, ds in datasets.items()}

    extents = {name: utils.get_dataset_extent(ds) for name, ds in datasets.items()}

    return datasets, extents


def load_income_dataset(variable="ln_pred_inc_mean", trim=True):
    """Open income dataset and merge with ELL estimation (small area estimates)."""

    # Open ICPAG dataset
    gdf = gpd.read_parquet(rf"{path_dataout}/small_area_estimates.parquet")
    gdf = gdf.to_crs(epsg=4326)
    gdf = gdf[gdf.AMBA_legal == 1].reset_index(drop=True)
    if trim:
        gdf = gdf[gdf["Area"] <= 200000]  # Remove rc that are too big

    # Normalize ELL estimation:
    var_mean = gdf[variable].mean()
    var_std = gdf[variable].std()
    gdf["var"] = (gdf[variable] - var_mean) / var_std

    data_dict = {"mean": var_mean, "std": var_std}
    pd.DataFrame().from_dict(data_dict, orient="index", columns=[variable]).to_csv(
        rf"{path_dataout}/scalars_{variable}_trim{trim}.csv"
    )

    return gdf


def assign_datasets_to_gdf(
    gdf,
    extents,
    year=2013,
    centroid=False,
    buffer=True,
    select="first_match",
    verbose=True,
):
    """Assign each geometry a dataset if the census tract falls within the extent of the dataset (images)

    Parameters:
    -----------
    gdf: geopandas.GeoDataFrame, shapefile with the census tracts
    extents: dict, dictionary with the extents of the satellite datasets
    year: int, year of the satellite images
    centroid: bool, if True, the centroid of the census tract is used to assign the dataset
    select: str, method to select the dataset. Options are "first_match" or "all_matches"
    """
    import warnings
    def get_matching_names(row):
        # Create a list of all the names where the row has a True
        return [name for name in extents.keys() if row[name] is True]

    def keep_only_one_capture(file_list):
        # Extract the identifier from the first element
        if len(file_list)>0:
            capture_id = file_list[0].split("_")[1]
            # Filter the list to keep only the values that match the identifier
            file_list = [f for f in file_list if capture_id in f]
        return file_list

    warnings.filterwarnings("ignore")

    if centroid:
        gdf["geometry"] = gdf.centroid

    if year is None:
        colname = "dataset"
    else:
        colname = f"dataset_{year}"

    if select == "first_match":
        for name, bbox in extents.items():
            if buffer:
                gdf.loc[gdf.buffer(0.004).within(bbox), colname] = name
            else:
                gdf.loc[gdf.within(bbox), colname] = name

    elif select == "all_matches":
        for name, bbox in extents.items():
            print(name)
            if buffer:
                gdf[name] = gdf.buffer(0.004).intersects(bbox)
            else:
                gdf[name] = gdf.intersects(bbox)
    


        gdf[colname] = gdf.apply(get_matching_names, axis=1)
        # gdf[colname] = gdf[colname].apply(keep_only_one_capture)
        # Replace empty lists with NaN
        gdf[colname] = gdf[colname].apply(lambda x: x if len(x) > 0 else np.nan)
        gdf = gdf.drop(columns=list(extents.keys()))

    nan_links = gdf[colname].isna().sum()
    # gdf = gdf[gdf[colname].notna()]

    if verbose:
        print(
            f"Links without images ({year}):", nan_links, "out of", len(gdf) + nan_links
        )
        print(f"Remaining links for train/test ({year}):", len(gdf))
        gdf.plot()
        plt.savefig(rf"{path_dataout}/links_with_images.png")

    warnings.filterwarnings("default")

    return gdf


def split_train_test(df, buffer=0):
    """Blocks are counted from left to right, one count for test and one for train."""

    # Set bounds of test dataset blocks
    test1_max_x = -58.66
    test1_min_x = -58.71
    test2_max_x = -58.36
    test2_min_x = -58.41

    # These blocks are the test dataset.
    #   The hole image have to be inside the train region
    df["type"] = np.nan
    df.loc[
        (
            (df.min_x > test1_min_x) & (df.max_x < test1_max_x)
        )  # Entre test1_minx y test1_maxx
        | (
            (df.min_x > test2_min_x) & (df.max_x < test2_max_x)
        ),  # Entre test2_minx y test2_maxx
        "type",
    ] = "test"

    # These blocks are the train dataset.
    #   The hole image have to be inside the train region
    df.loc[df.max_x + buffer < test1_min_x, "train_block"] = (
        1  # A la izqauierda de test1
    )
    df.loc[
        (df.min_x - buffer > test1_max_x) & (df.max_x + buffer < test2_min_x),
        "train_block",
    ] = 2  # Entre test1 y test2
    df.loc[df.min_x - buffer > test2_max_x, "train_block"] = 3  # A la derecha de test2
    # print(df.train_block.value_counts())

    # Put nans in the overlapping borders
    df.loc[df.train_block.isin([1, 2, 3]), "type"] = "train"
    df = df.drop(columns="train_block")

    test_size = df[df["type"] == "test"].shape[0]
    train_size = df[df["type"] == "train"].shape[0]
    invalid_size = df[df["type"].isna()].shape[0]
    total_size = df["type"].shape[0]

    print(
        "",
        f"Size of test dataset: {test_size/total_size*100:.2f}% ({test_size} census tracts)",
        f"Size of train dataset: {train_size/total_size*100:.2f}% ({train_size} census tracts)",
        f"Deleted images due to train/test overlapping: {invalid_size/total_size*100:.2f}% ({invalid_size} census tracts))",
        sep="\n",
    )

    return df


def assert_train_test_datapoint(bounds, wanted_type="train"):
    min_x, _, max_x, _ = bounds  # Ignore min_y and max_y

    test_blocks = [(-58.71, -58.66), (-58.41, -58.36)]

    for test_min_x, test_max_x in test_blocks:
        if test_min_x < min_x < max_x < test_max_x:
            # Inside test bloc
            return wanted_type == "test"
        elif max_x < test_min_x:
            return wanted_type == "train"
        elif test_max_x < min_x < max_x:
            return wanted_type == "train"
        elif max_x < test_max_x:
            return wanted_type == "train"

    return False


def assert_train_test_datapoint(bounds, wanted_type="train"):
    """Returns True if the datapoint is of the wanted type (train or test)."""

    # Split bounds:
    min_x, _, max_x, _ = bounds
    # min_x = bounds[0]
    # max_x = bounds[1]

    # Set bounds of test dataset blocks
    #    Note: Blocks are counted from left to right, one count for test and one for train.
    test1_max_x = -58.66
    test1_min_x = -58.71
    test2_max_x = -58.36
    test2_min_x = -58.41

    # These blocks are the test dataset.
    #   All the images have to be inside the test dataset blocks,
    #   so the filter is based on x_min and x_max of the images.
    type = None
    if ((min_x > test1_min_x) & (max_x < test1_max_x)) | (
        (min_x > test2_min_x) & (max_x < test2_max_x)
    ):
        type = "test"

    # These blocks are the train dataset.
    #   The hole image have to be inside the train region
    if max_x < test1_min_x:
        train_block = 1
    elif (min_x > test1_max_x) & (max_x < test2_min_x):
        train_block = 2
    elif min_x > test2_max_x:
        train_block = 3
    else:
        train_block = None

    # Put nans in the overlapping borders
    if (train_block == 1) | (train_block == 2) | (train_block == 3):
        type = "train"

    # Assert type
    if type == wanted_type:
        istype = True
    else:
        istype = False

    return istype


def get_dataset_for_gdf(icpag, datasets, link, year=2013, id_var="link"):
    """Get dataset where the census tract is located.

    Parameters
    ----------
    - icpag: geopandas.GeoDataFrame, shapefile with the census tracts
    - datasets: dict, dictionary with the satellite datasets. Names of the datasets are the keys and xarray.Datasets are the values.
    - link: str, 9 digits that identify the census tract

    Returns
    -------
    - current_ds: xarray.Dataset, dataset where the census tract is located
    """
    current_ds_name = icpag.loc[icpag[id_var] == link, f"dataset_{year}"].squeeze()

    if hasattr(current_ds_name, "__iter__"):
        current_ds = [datasets[ds_name] for ds_name in current_ds_name]
    else:
        if pd.isna(current_ds_name):
            # No dataset for this census tract this year...
            current_ds = None
            return current_ds
        current_ds = datasets[current_ds_name]
    return current_ds


def crop_dataset_to_link(ds, icpag, link):
    # obtengo el poligono correspondiente al link
    gdf_slice = icpag.loc[icpag["link"] == link]
    # Get bounds of the shapefile's polygon
    bbox_img = gdf_slice.bounds

    # Filter dataset based on the bounds of the shapefile's polygon
    image_ds = ds.sel(
        x=slice(float(bbox_img["minx"]), float(bbox_img["maxx"])),
        y=slice(float(bbox_img["maxy"]), float(bbox_img["miny"])),
    )
    return image_ds


def get_gridded_images_for_link(
    ds,
    icpag,
    link,
    tiles,
    size,
    resizing_size,
    sample,
    n_bands=4,
    stacked_images=[1],
):
    """
    Itera sobre el bounding box del poligono del radio censal, tomando imagenes de tamño sizexsize
    Si dicha imagen se encuentra dentro del polinogo, se genera el composite con dicha imagen mas otras tiles**2 -1 imagenes
    Devuelve un array con todas las imagenes generadas, un array con los puntos centrales de cada imagen y un array con los bounding boxes de cada imagen.

    Parameters:
    -----------
    ds: xarray.Dataset, dataset con las imágenes de satélite
    icpag: geopandas.GeoDataFrame, shapefile con los radios censales
    link: str, 9 dígitos que identifican el radio censal
    tiles: int, cantidad de imágenes a generar por lado
    size: int, tamaño de la imagen a generar, en píxeles
    resizing_size: int, tamaño al que se redimensiona la imagen
    bias: int, cantidad de píxeles que se mueve el punto aleatorio de las tiles
    sample: int, cantidad de imágenes a generar por box (util cuando tiles > 1)
    to8bit: bool, si es True, convierte la imagen a 8 bits

    Returns:
    --------
    images: list, lista con las imágenes generadas
    points: list, lista con los puntos centrales de cada imagen
    bounds: list, lista con los bounding boxes de cada imagen
    """
    # FIXME: algunos radios censales no se generan bien. Ejemplo: 065150101. ¿Que pasa ahi?
    images = []
    points = []
    bounds = []
    tile_size = size // tiles
    tiles_generated = 0
    total_bands = len(stacked_images) * n_bands

    link_dataset = crop_dataset_to_link(ds, icpag, link)
    # FIXME: add margin to the bounding box so left and bottom tiles are not cut. Margin should be the size of the tile - 1
    link_geometry = icpag.loc[icpag["link"] == link, "geometry"].values[0]

    # Iterate over the center points of each image:
    # - Start point is the center of the image (tile_size / 2, start_index)
    # - End point is the maximum possible center point (link_dataset.y.size)
    # - Step is the size of each image (tile_size)
    start_index = int(tile_size / 2)
    for idy in range(start_index, link_dataset.y.size, tile_size):
        # Iterate over columns
        for idx in range(start_index, link_dataset.x.size, tile_size):
            # Get the center point of the image
            image_point = (float(link_dataset.x[idx]), float(link_dataset.y[idy]))
            point_geom = sg.Point(image_point)
            point = point_geom.coords[0]

            # Check if the centroid of the image is within the original polygon:
            #   - if it is, then generate the n images
            if link_geometry.contains(point_geom):  # or intersects
                number_imgs = 0
                counter = 0  # Limit the times to try to sample the images
                while (number_imgs < sample) & (counter < sample * 2):
                    polygon = icpag.loc[icpag["link"] == link, "geometry"].item()
                    image, bound = utils.stacked_image_from_census_tract(
                        dataset=ds,
                        polygon=polygon,
                        point=point,
                        img_size=size,
                        n_bands=n_bands,
                        stacked_images=stacked_images,
                    )
                    counter += 1

                    if image.shape == (total_bands, size, size):
                        # TODO: add a check to see if the image is contained in test bounds
                        image = utils.process_image(image, resizing_size)

                        images += [image]
                        bounds += [bound]
                        number_imgs += 1

                    else:
                        print("Image failed")

    return images, points, bounds


def get_gridded_images_for_dataset(
    model, ds, icpag, tiles, size, resizing_size, bias, sample, to8bit
):
    """
    Itera sobre el bounding box de un dataset (raster de imagenes), tomando imagenes de tamño sizexsize
    Asigna el valor "real" del radio censal al que pertenece el centroide de la imagen.
    Devuelve un array con todas las imagenes generadas, un array con los puntos centrales de cada imagen,
    un array con los valores "reales" de los radios censales y un array con los bounding boxes de cada imagen.

    Parameters:
    -----------
    ds: xarray.Dataset, dataset con las imágenes de satélite
    icpag: geopandas.GeoDataFrame, shapefile con los radios censales
    tiles: int, cantidad de imágenes a generar por lado
    size: int, tamaño de la imagen a generar, en píxeles
    resizing_size: int, tamaño al que se redimensiona la imagen
    bias: int, cantidad de píxeles que se mueve el punto aleatorio de las tiles
    sample: int, cantidad de imágenes a generar por box (util cuando tiles > 1)
    to8bit: bool, si es True, convierte la imagen a 8 bits

    Returns:
    --------
    images: list, lista con las imágenes generadas
    points: list, lista con los puntos centrales de cada imagen
    bounds: list, lista con los bounding boxes de cada imagen
    """
    import main
    from shapely.geometry import Polygon

    # FIXME: algunos radios censales no se generan bien. Ejemplo: 065150101. ¿Que pasa ahi?
    # Inicializo arrays
    batch_images = np.empty((0, resizing_size, resizing_size, 4))
    batch_link_names = np.empty((0))
    batch_predictions = np.empty((0))
    batch_real_values = np.empty((0))
    batch_bounds = np.empty((0))
    all_link_names = np.empty((0))
    all_predictions = np.empty((0))
    all_real_values = np.empty((0))
    all_bounds = np.empty((0))

    tile_size = size // tiles
    tiles_generated = 0

    # Iterate over the center points of each image:
    # - Start point is the center of the image (tile_size / 2, start_index)
    # - End point is the maximum possible center point (link_dataset.y.size)
    # - Step is the size of each image (tile_size)

    # FIXME: para mejorar la eficiencia, convendría hacer un dissolve de icpag y verificar que
    # point_geom este en ese polygono y no en todo el df
    start_index = int(tile_size / 2)
    for idy in range(start_index, ds.y.size, tile_size):
        # Iterate over columns
        for idx in range(start_index, ds.x.size, tile_size):
            # Get the center point of the image
            image_point = (float(ds.x[idx]), float(ds.y[idy]))
            point_geom = sg.Point(image_point)

            # Get data for selected point
            radio_censal = icpag.loc[icpag.contains(point_geom)]
            if radio_censal.empty:
                # El radio censal no existe, es el medio del mar...
                continue

            real_value = radio_censal["var"].values[0]
            link_name = radio_censal["link"].values[0]

            # Check if the centroid of the image is within the original polygon:
            #   - if it is, then generate the n images

            image, point, bound, tbound = utils.random_image_from_census_tract(
                ds,
                icpag,
                link_name,
                start_point=image_point,
                tiles=tiles,
                size=size,
                bias=bias,
                to8bit=to8bit,
            )

            if image is not None:
                image = utils.process_image(image, resizing_size)
                geom_bound = Polygon(
                    bound[0]
                )  # Create polygon of the shape of the image

                batch_images = np.concatenate([batch_images, np.array([image])], axis=0)
                batch_link_names = np.concatenate(
                    [batch_link_names, np.array([link_name])], axis=0
                )
                batch_real_values = np.concatenate(
                    [batch_real_values, np.array([real_value])], axis=0
                )
                batch_bounds = np.concatenate(
                    [batch_bounds, np.array([geom_bound])], axis=0
                )

                # predict with the model over the batch
                if batch_images.shape[0] == 128:
                    # predictions
                    batch_predictions = main.get_batch_predictions(
                        model, batch_images
                    )

                    # Store data
                    all_predictions = np.concatenate(
                        [all_predictions, batch_predictions], axis=0
                    )
                    all_link_names = np.concatenate(
                        [all_link_names, batch_link_names], axis=0
                    )
                    all_real_values = np.concatenate(
                        [all_real_values, batch_real_values], axis=0
                    )
                    all_bounds = np.concatenate([all_bounds, batch_bounds], axis=0)

                    # Restore batches to empty
                    batch_images = np.empty((0, resizing_size, resizing_size, 4))
                    batch_predictions = np.empty((0))
                    batch_link_names = np.empty((0))
                    batch_predictions = np.empty((0))
                    batch_real_values = np.empty((0))
                    batch_bounds = np.empty((0))

    # Creo dataframe para exportar:
    d = {
        "link": all_link_names,
        "predictions": all_predictions,
        "real_value": all_real_values,
    }

    df_preds = gpd.GeoDataFrame(d, geometry=all_bounds, crs="epsg:4326")

    return df_preds


def get_random_images_for_link(
    ds, icpag, link, tiles, size, resizing_size, bias, sample, to8bit
):
    """
    Genera n imagenes del poligono del radio censal, tomando imagenes de tamño sizexsize
    Si dicha imagen se encuentra dentro del polinogo, se genera el composite con dicha imagen mas otras tiles**2 -1 imagenes
    Devuelve un array con todas las imagenes generadas, un array con los puntos centrales de cada imagen y un array con los bounding boxes de cada imagen.

    Parameters:
    -----------
    ds: xarray.Dataset, dataset con las imágenes de satélite
    icpag: geopandas.GeoDataFrame, shapefile con los radios censales
    link: str, 9 dígitos que identifican el radio censal
    tiles: int, cantidad de imágenes a generar por lado
    size: int, tamaño de la imagen a generar, en píxeles
    resizing_size: int, tamaño al que se redimensiona la imagen
    bias: int, cantidad de píxeles que se mueve el punto aleatorio de las tiles
    sample: int, cantidad de imágenes a generar por box (util cuando tiles > 1)
    to8bit: bool, si es True, convierte la imagen a 8 bits

    Returns:
    --------
    images: list, lista con las imágenes generadas
    points: list, lista con los puntos centrales de cada imagen
    bounds: list, lista con los bounding boxes de cada imagen
    """
    # FIXME: algunos radios censales no se generan bien. Ejemplo: 065150101. ¿Que pasa ahi?
    images = []
    points = []
    bounds = []
    tile_size = size // tiles
    tiles_generated = 0

    link_dataset = crop_dataset_to_link(ds, icpag, link)
    # FIXME: add margin to the bounding box so left and bottom tiles are not cut. Margin should be the size of the tile - 1
    link_geometry = icpag.loc[icpag["link"] == link, "geometry"].values[0]

    number_imgs = 0
    counter = 0  # Limit the times to try to sample the images
    while (number_imgs < sample) & (counter < sample * 2):
        # Generate a random point
        x_point = np.random.uniform(link_dataset.x.min(), link_dataset.x.max())
        y_point = np.random.uniform(link_dataset.y.min(), link_dataset.y.max())

        # Get the center point of the image
        image_point = (x_point, y_point)
        point_geom = sg.Point(image_point)

        # Check if the centroid of the image is within the original polygon:
        #   - if it is, then generate the n images
        if link_geometry.contains(point_geom):  # or intersects
            img, point, bound, tbound = utils.random_image_from_census_tract(
                ds,
                icpag,
                link,
                start_point=image_point,
                tiles=tiles,
                size=size,
                bias=bias,
                to8bit=to8bit,
            )

            counter += 1

            if img is not None:
                # TODO: add a check to see if the image is contained in test bounds
                img = utils.process_image(img, resizing_size)

                images += [img]
                points += [point]
                bounds += [bound]
                number_imgs += 1

            else:
                print("Image failed")

    return images, points, bounds

    return images, real_values, links, points, bounds


def stretch_dataset(ds, pixel_depth=32_767):
    """Stretch band data from satellite images."""
    minimum = ds.band_data.quantile(0.01).values
    maximum = ds.band_data.quantile(0.99).values
    ds = (ds - minimum) / (maximum - minimum) * pixel_depth
    ds = ds.where(ds.band_data > 0, 0)
    ds = ds.where(ds.band_data < pixel_depth, pixel_depth)
    return ds


def normalize_landsat(ds):
    band_data = ds.band_data.to_numpy()
    for band in range(band_data.shape[0]):
        this_band = band_data[band]

        vmin = np.percentile(this_band, q=2)
        vmax = np.percentile(this_band, q=98)

        # High values
        mask = this_band > vmax
        this_band[mask] = vmax

        # low values
        mask = this_band < vmin
        this_band[mask] = vmin

        # Normalize
        this_band = (this_band - vmin) / (vmax - vmin)

        band_data[band] = this_band * 255

    return ds


def remove_overlapping_pixels(main, to_crop):

    main_extent = utils.get_dataset_extent(main)
    will_be_cropeed_extent = utils.get_dataset_extent(to_crop)
    cropped_extent = will_be_cropeed_extent.difference(main_extent)

    # Crop dataset
    min_lon, min_lat, max_lon, max_lat = cropped_extent.bounds
    cropped = to_crop.sel(x=slice(min_lon, max_lon), y=slice(max_lat, min_lat))

    return cropped


def pickle_xr_dataset(ds, filename):
    import pickle

    pkl = pickle.dumps(ds, protocol=-1)
    with open(filename, "wb") as f:
        f.write(pkl)

    print("Pickled data saved to:", filename)
    return


def add_datasets_combinations(datasets):
    from shapely.geometry import box

    extents = {name: utils.get_dataset_extent(ds) for name, ds in datasets.items()}
    combinations = {}
    to_remove = []

    for ds_name, ds in datasets.items():
        # Construyo lista de datasets que intersectan con ds_name
        capture_ds_name = ds_name.split("_")[1]
        ds_extent = extents[ds_name]
        buffered_extent = ds_extent.buffer(0.005).envelope
        xmin, ymin, xmax, ymax = buffered_extent.bounds

        intersecting = []
        for name, ds_extent in extents.items():
            capture_name = name.split("_")[1]
            if (
                ds_extent.intersects(buffered_extent)
                & (name != ds_name)
                & (capture_ds_name == capture_name)
            ):
                intersecting += [name]

        # Recorto datasets de intersection (buffer de 1080px):
        cropped_datasets = {}
        for intersection in intersecting:
            intersecting_ds = datasets[intersection]
            cropped_datasets[intersection] = intersecting_ds.sel(
                x=slice(xmin, xmax), y=slice(ymax, ymin)
            )

        # Armo xarray con la intersección de a pares
        for cropped_name, cropped_ds in cropped_datasets.items():

            names = [ds_name, cropped_name]
            names = [name.replace("pansharpened_", "") for name in names]
            names.sort()
            combined_name = "comb_" + "_".join(names)

            if combined_name not in combinations:
                polygon = box(
                    cropped_ds.x.min(),
                    cropped_ds.y.min(),
                    cropped_ds.x.max(),
                    cropped_ds.y.max(),
                )
                buffered_extent = polygon.buffer(0.005).envelope
                xmin, ymin, xmax, ymax = buffered_extent.bounds

                cropped_main_ds = ds.sel(x=slice(xmin, xmax), y=slice(ymax, ymin))
                cropped_ds = remove_overlapping_pixels(cropped_main_ds, cropped_ds)

                # print(ds_name, cropped_name)
                # print(cropped_main_ds)
                # print(cropped_ds)

                try:
                    result_ds = xr.combine_by_coords(
                        [cropped_main_ds, cropped_ds], combine_attrs="override"
                    )

                    # Store xarray and reload to remove cross-references across objects and reduce memory usage
                    filename = rf"{path_dataout}/tempfiles/{combined_name}.pkl"
                    pickle_xr_dataset(ds, filename)
                    with open(filename, "rb") as f:
                        result_ds = pickle.load(f)
                    to_remove += [filename]

                    combinations[combined_name] = result_ds
                except Exception as e:
                    print(e)

    all_datasets = combinations | datasets

    return all_datasets


def filter_black_pixels_over_dim(ds, dim="x"):
    if dim == "x":
        other_dim = "y"
    elif dim == "y":
        other_dim = "x"
    else:
        raise ValueError("dim must be 'x' or 'y'")

    # Selecciono la mitad de la imagen
    center = int(ds[dim].size / 2)
    edge_data = ds.isel({dim: center})

    # Busco los pixeles con al menos 50 pixeles sin datos
    has_black_pixels = (edge_data["band_data"] == 0).all(dim="band")
    has_black_pixels_in_row = has_black_pixels.rolling({other_dim: 50}).sum()
    valid_data = (has_black_pixels_in_row == 0) | (has_black_pixels_in_row.isnull())

    # Filtro los datos
    first_valid = valid_data.to_numpy().tolist().index(True)
    last_valid = -valid_data.to_numpy().tolist()[::-1].index(True)

    if first_valid == 0:
        first_valid = None
    if last_valid == 0:
        last_valid = None

    return ds.isel({other_dim: slice(first_valid, last_valid)})


def filter_black_pixels(ds):
    y_filtered = filter_black_pixels_over_dim(ds, "y")
    filtered = filter_black_pixels_over_dim(y_filtered, "x")
    return filtered


def generate_matrix_of_files(files):
    """Create a matrix of files to be loaded by xr.open_mfdataset.

    Files are ordered as the original tiles, where R1C3 is the first tile of the third column.
    Run xr.open_mfdataset(matrix, combine="nested", concat_dim=["x", "y"], engine="rasterio") after this.

    Parameters:
    files (list): List of files to be loaded

    Returns:
    matrix (list): List of lists of files to be loaded by xr.open_mfdataset
    """
    files.sort()

    matrix = []
    for col in range(1, 5):
        cols_files = [f for f in files if f"C{col}.tif" in f]
        if len(cols_files) > 0:
            matrix += [cols_files]
    return matrix

def generate_matrix_of_datasets(datasets):
    """Create a matrix of datasets to be merged by xr.combine_nested.

    Files are ordered as the original tiles, where R1C3 is the first tile of the third column.
    Run xr.open_mfdataset(matrix, combine="nested", concat_dim=["x", "y"], engine="rasterio") after this.

    Parameters:
    files (list): List of files to be loaded

    Returns:
    matrix (list): List of lists of files to be loaded by xr.open_mfdataset
    """
    datasets = sorted(datasets, key=lambda element: sorted(element.encoding["source"]))
    print([ds.encoding["source"] for ds in datasets])
    matrix = []
    for row in range(1, 10):
        rows_ds = [ds for ds in datasets if f"_R{row}C" in ds.encoding["source"]]
        if len(rows_ds) > 0:
            matrix += [rows_ds]
    return matrix

