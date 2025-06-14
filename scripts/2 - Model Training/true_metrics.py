##############      Configuración      ##############
import os
import gc
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict
from dotenv import dotenv_values

pd.set_option("display.max_columns", None)
envpath = "/mnt/d/Maestría/Tesis/Repo/scripts/globals.env"
if os.path.isfile(envpath):
    env = dotenv_values(envpath)
else:
    env = dotenv_values(r"D:/Maestría/Tesis/Repo/scripts/globals_win.env")

path_proyecto = env["PATH_PROYECTO"]
path_datain = env["PATH_DATAIN"]
path_dataout = env["PATH_DATAOUT"]
path_scripts = env["PATH_SCRIPTS"]
path_satelites = env["PATH_SATELITES"]
path_logs = env["PATH_LOGS"]
path_outputs = env["PATH_OUTPUTS"]
path_imgs = env["PATH_IMGS"]
# path_programas  = globales[7]
###############################################
import prediction_tools
import custom_models
import build_dataset
import utils
import main

import sys
import pandas as pd
import os
import xarray as xr
import geopandas as gpd
from typing import Iterator, List, Union, Tuple, Any
from datetime import datetime

import tensorflow as tf
from tensorflow import keras
import tensorflow_datasets as tfds
import tensorflow_addons as tfa

from tensorflow.keras import layers, models, Model
from tensorflow.keras.callbacks import (
    TensorBoard,
    EarlyStopping,
    ModelCheckpoint,
)
from tensorflow.keras.models import Sequential
import cv2
import skimage

# the next 3 lines of code are for my machine and setup due to https://github.com/tensorflow/tensorflow/issues/43174
try:
    physical_devices = tf.config.list_physical_devices("GPU")
    tf.config.experimental.set_memory_growth(physical_devices[0], True)
except:
    print("No GPU set. Is the GPU already initialized?")


# Disable
def blockPrint():
    sys.__stdout__ = sys.stdout
    sys.stdout = open(os.devnull, "w")


# Restore
def enablePrint():
    sys.stdout.close()
    sys.stdout = sys.__stdout__


def generate_gridded_images(
    df_test,
    sat_img_datasets,
    test_folder,
    tiles,
    size,
    resizing_size,
    n_bands,
    stacked_images,
    year=2013,
):
    import geopandas as gpd

    # Filtro Radios demasiado grandes (tardan horas en generar la cuadrícula y es puro campo...)
    df_test = df_test[df_test["AREA"] <= 200000]  # Remove rc that are too big
    links = df_test["link"].unique()
    valid_links = []

    # Loop por radio censal. Si está la imagen la usa, sino la genera.
    os.makedirs(test_folder, exist_ok=True)
    for n, link in enumerate(links):
        # print(f"{link}: {n}/{len_links}")
        # Genera la imagen
        file = rf"{test_folder}/test_{link}.npy"

        link_dataset = build_dataset.get_dataset_for_gdf(
            df_test, sat_img_datasets, link, year=year
        )
        if link_dataset is None:
            continue

        images, points, bounds = build_dataset.get_gridded_images_for_link(
            link_dataset,
            df_test,
            link,
            tiles,
            size,
            resizing_size,
            sample=1,
            n_bands=n_bands,
            stacked_images=stacked_images,
        )
        # print("imagen generada")
        if len(images) == 0:
            # No images where returned from this census tract, so no error to compute...
            print(f"problema con link {link}...")
        else:
            images = np.array(images)
            np.save(file, images)
            valid_links += [link]

    valid_links = np.array(valid_links)
    np.save(rf"{test_folder}/valid_links.npy", valid_links)
    print("Imagenes generadas!")

    return test_folder


def get_gridded_predictions_for_grid(
    model, datasets, extents, icpag, size, resizing_size, n_bands, stacked_images, year
):
    """
    Generate gridded predictions for a given GeoDataFrame grid using a machine learning model.

    Parameters:
    - model (keras.Model): Trained machine learning model for image prediction.
    - datasets (dict): Dictionary containing xarray.Datasets for image generation (the original satellite images).
    - icpag (geopandas.GeoDataFrame): GeoDataFrame with census tract data.
    - size (int): Size of each image.
    - resizing_size (int): Size to which the images will be resized.
    - n_bands (int): Number of bands in the image.
    - tiles (int): Number of tiles. -- deprecated
    - sample: (int): Sample parameter description. -- deprecated

    Returns:
    - gridded_predictions (geopandas.GeoDataFrame): GeoDataFrame containing gridded predictions and data
    from the corresponding census tract.
    """

    import main
    from tqdm import tqdm
    from shapely.geometry import Polygon

    def remove_sea_from_grid(grid):

        # Get the regio of interest
        amba_costa = load_roi_coast_data(grid)
        # Remove non relevant cells from grid
        is_relevant = grid.set_crs(epsg=4326, allow_override=True).within(amba_costa)
        grid = grid[is_relevant]

        return grid

    def load_roi_coast_data(grid):

        from shapely import Polygon

        # Load país
        pais = gpd.read_file(rf"{path_datain}/Limites Argentina/pais.shp")
        # Get grid exterior
        exterior = Polygon(
            [
                grid.total_bounds[[0, 1]],
                grid.total_bounds[[2, 1]],
                grid.total_bounds[[2, 3]],
                grid.total_bounds[[0, 3]],
                grid.total_bounds[[0, 1]],
            ]
        )
        # Clip
        amba_costa = pais.clip(exterior)
        # amba_costa.plot()
        # Simplify
        amba_costa.geometry = amba_costa.geometry.simplify(0.001)

        return amba_costa.geometry.item()  # Polygon with amba bounds

    def restrict_grid_to_ICPAG_area(grid, icpag):

        from shapely import Polygon

        # Get convex hull of icpag
        exterior = icpag.geometry.unary_union.convex_hull

        # Clip
        grid = grid[grid.centroid.within(exterior)]

        return grid  # Polygon with amba bounds

    def procesa_grilla(grid, icpag, extents):
        print("Procesando grilla")
        grid = restrict_grid_to_ICPAG_area(grid, icpag)
        grid = remove_sea_from_grid(grid)
        grid = build_dataset.assign_datasets_to_gdf(
            grid, extents, year=year, select="all_matches", verbose=False
        )
        grid = grid.dropna(subset=[f"dataset_{year}"])
        grid = grid.set_crs(epsg=4326, allow_override=True)
        grid["point"] = grid.centroid
        grid["bounds_geom"] = grid["geometry"]
        grid = grid.set_geometry("point")
        grid = grid.sjoin(icpag[["link", "var", "geometry"]], predicate="intersects")
        grid = grid.reset_index(drop=True)
        gc.collect()
        print("data loaded")

        return grid

    def get_grid_data(i):
        # Decoding from the EagerTensor object. Extracts the number/value from the tensor
        #   example: <tf.Tensor: shape=(), dtype=uint32, numpy=20> -> 20
        i = i.numpy()
        # initialize iterators & params
        image = np.zeros(shape=(n_bands, 0, 0))
        total_bands = n_bands * len(stacked_images)
        img_correct_shape = (total_bands, size, size)

        # Get link, dataset and indicator value of the corresponding index
        id_point, raster_point = grid.loc[i, ["id", "point"]]
        raster_point = (raster_point.x, raster_point.y)
        cell_datasets = build_dataset.get_dataset_for_gdf(
            grid, datasets, id_point, year=year, id_var="id"
        )
        if len(cell_datasets) == 0:
            print(
                f"No datasets for point {raster_point} (id: {id_point}), moving to next image..."
            )
            image = np.zeros(shape=(resizing_size, resizing_size, total_bands))
            return image

        # Generate the image
        image = utils.stacked_image_from_census_tract(
            dataset=cell_datasets,
            polygon=None,
            point=raster_point,
            img_size=size,
            n_bands=n_bands,
            stacked_images=stacked_images,
            bounds=False,
        )
        if image.shape != img_correct_shape:
            # print(
            #     f"Could not retrieve a valid image for point {raster_point} (id: {id_point}), moving to next image..."
            # )
            if id_point == 769303:
                print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
            image = np.zeros(shape=(resizing_size, resizing_size, total_bands))
            return image

        # Reduce quality and process image
        image = utils.process_image(image, resizing_size=resizing_size)
        # np.save(fr"/mnt/d/Maestría/Tesis/Repo/data/data_out/grid_datasets/img_{i}_{id_point}.npy", image)
        # print(f"Se creó /mnt/d/Maestría/Tesis/Repo/data/data_out/grid_datasets/img_{i}_{id_point}.npy")
        return image

    # Open grid of polygons for the corresponding parameters:
    if os.path.exists(rf"{path_dataout}/grid_datasets/grid_{year}_proc.parquet"):
        grid = gpd.read_parquet(
            rf"{path_dataout}/grid_datasets/grid_{year}_proc.parquet"
        )
        # grid = grid.cx[-58.58:-58.52, -34.49:-34.52].reset_index()
    else:
        if size < 128:  # Working with landsat
            grid = gpd.read_parquet(
                rf"{path_datain}/Grillas/grid_size512_tiles1.parquet"
            )
        else:
            grid = gpd.read_parquet(
                rf"{path_datain}/Grillas/grid_size{size}_tiles1.parquet"
            )
        grid = procesa_grilla(grid, icpag, extents)
        grid.to_parquet(rf"{path_dataout}/grid_datasets/grid_{year}_proc.parquet")

    ### TF Datasets
    print("SE VAN A GENERAR:", grid.shape[0], "IMAGENES")
    grid_dataset = tf.data.Dataset.from_generator(
        lambda: list(range(grid.shape[0])),  # The index generator,
        tf.uint32,
    )  # Creates a dataset with only the indexes (0, 1, 2, 3, etc.)

    grid_dataset = grid_dataset.map(
        lambda i: tf.py_function(  # The actual data generator. Passes the index to the function that will process the data.
            func=get_grid_data, inp=[i], Tout=[tf.uint8]
        ),
        num_parallel_calls=1,
        deterministic=True,
    )
    grid_dataset = grid_dataset.batch(128)

    ### Predictions
    predictions = model.predict(grid_dataset)

    # Formateo dataframe para exportar:
    grid = grid.rename(columns={"var": "real_value", "geometry": "link_polygon"})
    grid["prediction"] = predictions
    grid["prediction_error"] = grid["real_value"] - grid["prediction"]
    grid = grid.set_geometry("bounds_geom")

    return grid


def get_batch_predictions(model, batch_images):
    """Computa las predicciones del batch

    Parameters:
    -----------
    model: tf.keras.Model, modelo entrenado
    images: np.array con las imágenes a predecir (batch_size, img_size, img_size, bands)
    batch_real_value: np.array con el valor real del radio censal correspondiente (batch_size)
    metric: function, función que computa el error de predicción. Por defecto es np.mean
    """
    to_predict = tf.data.Dataset.from_tensor_slices(batch_images)

    to_predict = to_predict.batch(8)
    predictions = model.predict(to_predict)
    predictions = predictions.flatten()

    return predictions


def compute_custom_loss_all_epochs(
    models_dir,
    savename,
    datasets,
    tiles,
    size,
    resizing_size,
    subset="val",  # "test" or "val"
    n_epochs=20,
    n_bands=4,
    stacked_images=[1],
    generate=False,
    verbose=False,
    kind="reg",
):
    """
    Calcula el ECM del conjunto de predicción.

    Carga las bases necesarias, itera sobre los radios censales, genera las imágenes
    en forma de grilla y compara las predicciones de esas imágenes con el valor real
    del radio censal.

    Parameters:
    -----------
    tiles: int, cantidad de imágenes a generar por lado
    size: int, tamaño de la imagen a generar, en píxeles
    resizing_size: int, tamaño al que se redimensiona la imagen
    bias: int, cantidad de píxeles que se mueve el punto aleatorio de las tiles
    to8bit: bool, si es True, convierte la imagen a 8 bits

    Returns:
    --------
    mse: float, error cuadrático medio del conjunto de predicción

    """
    import geopandas as gpd
    from tqdm import tqdm

    mse_epochs = {epoch: None for epoch in range(n_epochs)}
    if verbose == False:
        blockPrint()

    if subset not in ["test", "val"]:
        raise ValueError("subset must be either 'test' or 'val'")

    print("Loading data...")
    if subset == "test":
        df = gpd.read_feather(
            rf"{path_dataout}/test_datasets/{savename}_test_dataframe.feather"
        )
    elif subset == "val":
        df_not_test = gpd.read_feather(
            rf"{path_dataout}/train_datasets/{savename}_train_dataframe.feather"
        )
        df = df_not_test.sample(frac=0.066667, random_state=200)
        df = df.reset_index()
        df.to_feather(rf"{path_dataout}/val_datasets/{savename}_val_dataframe.feather")
    print("Data loaded!")

    # dir of the images
    stacked_names = "-".join(
        str(x) for x in stacked_images
    )  # Transforms list [1,2] to string like "1-2"
    folder = rf"{path_satelites}/{subset}_datasets/{subset}_size{size}_tiles{tiles}_stacked{stacked_names}"

    # Genero las imágenes
    if generate or ~os.path.isfile(rf"{folder}/valid_links.npy"):
        print("Generando imágenes en grilla...")
        folder = generate_gridded_images(
            df,
            datasets,
            folder,
            tiles,
            size,
            resizing_size,
            n_bands,
            stacked_images,
            year=2013,
        )

    links = np.load(rf"{folder}/valid_links.npy")

    # Cargo todas las imágenes en memoria
    print("Cargando arrays en memoria...")
    # blockPrint()
    link_names = []
    real_values = []
    images = []

    for link in tqdm(links):
        # Obtener las imágenes del radio censal
        link_real_value = df.loc[df["link"] == link, "var"].values[0]
        link_images = np.load(rf"{folder}/test_{link}.npy")
        q_images = link_images.shape[0]

        link_names += [link] * q_images
        real_values += [link_real_value] * q_images
        images += [link_images]

    # Agrega al batch de valores reales / imagenes para la prediccion
    images = np.concatenate(images, axis=0)
    link_names = np.array(link_names)
    real_values = np.array(real_values)
    print("Arrays cargados!")

    model_name = savename.split("_")[0] + "_" + savename.split("_")[1]
    model, _, _ = main.set_model_and_loss_function(
        model_name=model_name,
        kind=kind,
        bands=n_bands * len(stacked_images),
        resizing_size=resizing_size,
        weights=None,
    )

    for epoch in range(0, n_epochs):
        filename = (
            f"{path_dataout}/models_by_epoch/{savename}/{savename}_{subset}_{epoch}.csv"
        )

        if os.path.exists(filename):
            df_preds = pd.read_csv(filename)
            df_preds["mean_prediction"] = df_preds.groupby(
                by="link"
            ).predictions.transform("mean")
            df_preds["error"] = df_preds["mean_prediction"] - df_preds["real_value"]
            df_preds["sq_error"] = df_preds["error"] ** 2
            mse = df_preds.drop_duplicates(subset=["link"]).sq_error.mean()

            print(f"Epoch {epoch}/{n_epochs}: True Mean Squared Error: {mse}")

            # Store MSE value in dict and full predictions
            mse_epochs[epoch] = mse

            continue

        try:
            model.load_weights(
                f"{models_dir}/{savename}_{epoch}/variables/variables"
            ).expect_partial()

            # model = tf.keras.models.load_model(
            #     f"{models_dir}/{savename}_{epoch}", compile=True
            # )
            predictions = get_batch_predictions(model, images)
        except Exception as error:
            print("Error en epoca:", epoch, error)
            predictions = real_values

        # Creo dataframe para exportar:
        d = {
            "link": link_names,
            "predictions": predictions,
            "real_value": real_values,
        }
        df_preds = pd.DataFrame(data=d)

        df_preds["mean_prediction"] = df_preds.groupby(by="link").predictions.transform(
            "mean"
        )
        df_preds["error"] = df_preds["mean_prediction"] - df_preds["real_value"]
        df_preds["sq_error"] = df_preds["error"] ** 2
        mse = df_preds.drop_duplicates(subset=["link"]).sq_error.mean()

        # enablePrint()
        print(f"Epoch {epoch}/{n_epochs}: True Mean Squared Error: {mse}")

        # Store MSE value in dict and full predictions
        mse_epochs[epoch] = mse
        df_preds.to_csv(filename)

    # Export csv with all MSE
    mse_test = pd.DataFrame().from_dict(
        mse_epochs, orient="index", columns=["mse_test_rc"]
    )
    mse_train = pd.read_csv(
        f"{path_dataout}/models_by_epoch/{savename}/{savename}_history.csv"
    )[["loss", "val_loss"]]
    metrics_epochs = (
        mse_train.join(mse_test, how="outer")
        .reset_index()
        .rename(
            columns={"index": "epoch", "loss": "mse_train", "val_loss": "mse_test_img"}
        )
    )
    metrics_epochs.to_csv(
        f"{path_dataout}/models_by_epoch/{savename}/{savename}_{subset}_metrics_over_epochs.csv"
    )
    print(
        "Se creo el archivo:",
        f"{path_dataout}/models_by_epoch/{savename}/{savename}_{subset}_metrics_over_epochs.csv",
    )

    return metrics_epochs


def compute_custom_loss_for_epoch(
    models_dir,
    savename,
    datasets,
    tiles,
    size,
    resizing_size,
    subset="val",  # "test" or "val"
    n_epochs=20,
    n_bands=4,
    stacked_images=[1],
    generate=False,
    verbose=False,
    kind="reg",
    epoch=100,
):
    """
    Calcula el ECM del conjunto de predicción en una sola epoca.

    Carga las bases necesarias, itera sobre los radios censales, genera las imágenes
    en forma de grilla y compara las predicciones de esas imágenes con el valor real
    del radio censal.

    Parameters:
    -----------
    tiles: int, cantidad de imágenes a generar por lado
    size: int, tamaño de la imagen a generar, en píxeles
    resizing_size: int, tamaño al que se redimensiona la imagen
    bias: int, cantidad de píxeles que se mueve el punto aleatorio de las tiles
    to8bit: bool, si es True, convierte la imagen a 8 bits

    Returns:
    --------
    mse: float, error cuadrático medio del conjunto de predicción

    """
    import geopandas as gpd
    from tqdm import tqdm

    if verbose == False:
        blockPrint()

    if subset not in ["test", "val"]:
        raise ValueError("subset must be either 'test' or 'val'")

    print("Loading data...")
    if subset == "test":
        df = gpd.read_feather(
            rf"{path_dataout}/test_datasets/{savename}_test_dataframe.feather"
        )
    elif subset == "val":
        df_not_test = gpd.read_feather(
            rf"{path_dataout}/train_datasets/{savename}_train_dataframe.feather"
        )
        df = df_not_test.sample(frac=0.066667, random_state=200)
        df = df.reset_index()
        df.to_csv(rf"{path_dataout}/val_datasets/{savename}_val_dataframe.feather")
    print("Data loaded!")

    # dir of the images
    stacked_names = "-".join(
        str(x) for x in stacked_images
    )  # Transforms list [1,2] to string like "1-2"
    folder = rf"{path_satelites}/{subset}_datasets/{subset}_size{size}_tiles{tiles}_stacked{stacked_names}"

    # Genero las imágenes
    if generate or ~os.path.isfile(rf"{folder}/valid_links.npy"):
        print("Generando imágenes en grilla...")
        folder = generate_gridded_images(
            df,
            datasets,
            folder,
            tiles,
            size,
            resizing_size,
            n_bands,
            stacked_images,
            year=2013,
        )

    links = np.load(rf"{folder}/valid_links.npy")

    # Cargo todas las imágenes en memoria
    print("Cargando arrays en memoria...")
    # blockPrint()
    link_names = []
    real_values = []
    images = []

    for link in tqdm(links):
        # Obtener las imágenes del radio censal
        link_real_value = df.loc[df["link"] == link, "var"].values[0]
        link_images = np.load(rf"{folder}/test_{link}.npy")
        q_images = link_images.shape[0]

        link_names += [link] * q_images
        real_values += [link_real_value] * q_images
        images += [link_images]

    # Agrega al batch de valores reales / imagenes para la prediccion
    images = np.concatenate(images, axis=0)
    link_names = np.array(link_names)
    real_values = np.array(real_values)
    print("Arrays cargados!")

    model_name = savename.split("_")[0] + "_" + savename.split("_")[1]
    model, _, _ = main.set_model_and_loss_function(
        model_name=model_name,
        kind=kind,
        bands=n_bands * len(stacked_images),
        resizing_size=resizing_size,
        weights=None,
    )

    model.load_weights(
        f"{models_dir}/{savename}_{epoch}/variables/variables"
    ).expect_partial()

    # model = tf.keras.models.load_model(
    #     f"{models_dir}/{savename}_{epoch}", compile=True
    # )
    predictions = get_batch_predictions(model, images)

    # Creo dataframe para exportar:
    d = {
        "link": link_names,
        "predictions": predictions,
        "real_value": real_values,
    }
    df_preds = pd.DataFrame(data=d)

    df_preds["mean_prediction"] = df_preds.groupby(by="link").predictions.transform(
        "mean"
    )
    df_preds["error"] = df_preds["mean_prediction"] - df_preds["real_value"]
    df_preds["sq_error"] = df_preds["error"] ** 2
    mse = df_preds.drop_duplicates(subset=["link"]).sq_error.mean()
    variance = df_preds.drop_duplicates(subset=["link"]).real_value.var()
    r2 = 1 - mse / variance
    # enablePrint()
    print(f"TEST Mean Squared Error: {mse} (Epoch {epoch}/{n_epochs})")
    print(f"TEST R Squared: {r2} (Epoch {epoch}/{n_epochs})")

    # Store MSE value in dict and full predictions
    results = {"mse": mse, "variance": variance, "Rsquared": r2}
    with open(
        f"{path_dataout}/models_by_epoch/{savename}/{savename}_{subset}_results.txt",
        "w",
    ) as file:
        # Write each key-value pair in the dictionary to the file
        for key, value in results.items():
            file.write(f"{key}: {value}\n")

    # Store full df for scatterplots and analysis
    df_preds.to_csv(
        f"{path_dataout}/models_by_epoch/{savename}/{savename}_{subset}_{epoch}.csv"
    )

    return df_preds


def plot_mse_over_epochs(mse_df, modelname, metric="mse", save=False):
    import plotly.express as px
    from plotly import graph_objects as go

    plot_df = mse_df.melt(
        id_vars="epoch", value_vars=["mse_test_img", "mse_test_rc", "mse_train"]
    )

    # Plot
    fig = px.line(
        plot_df,
        x="epoch",
        y="value",
        color="variable",
        title="True Mean Squared Error over epochs",
    )
    fig.update_yaxes(range=[0, 1])

    fig.update_layout(
        autosize=False,
        width=1280,
        height=720,
    )

    if save:
        fig.write_image(
            f"{path_outputs}/{modelname}/mse_best_prediction_{modelname}.png"
        )


def plot_predictions_vs_real(
    modelname, selected_epoch, quantiles=False, last_training=False, save=False
):
    import plotly.express as px
    from plotly import graph_objects as go

    folder = f"{path_dataout}/models_by_epoch/{modelname}"

    # Open dataset
    best_case = pd.read_csv(rf"{folder}/{modelname}_test_{selected_epoch}.csv")
    best_case = (
        best_case.groupby("link")[["real_value", "mean_prediction"]]
        .mean()
        .reset_index()
    )
    if quantiles:
        best_case["real_value"] = pd.qcut(best_case["real_value"], 100, labels=False)
        best_case["mean_prediction"] = pd.qcut(
            best_case["mean_prediction"], 100, labels=False
        )
        axis_range = [0, 100]
        title = f"{modelname} - cuantiles"
    else:
        axis_range = [-2, 2]
        title = f"{modelname} - niveles"

    import seaborn as sns

    fig = px.scatter(
        best_case, x="real_value", y="mean_prediction", hover_data=["link"], title=title
    )
    fig.update_yaxes(range=axis_range)
    fig.update_xaxes(range=axis_range)
    fig.update_layout(
        autosize=False,
        width=800,
        height=800,
    )

    # Add 45° line
    line_fig = go.Figure(
        data=go.Scatter(
            x=best_case["real_value"],
            y=best_case["real_value"],
            mode="lines",
            name="45°",
        )
    )
    fig.add_trace(line_fig.data[0])

    if save:
        if quantiles:
            fig.write_image(
                f"{path_outputs}/{modelname}/prediction_vs_real_best_prediction_{modelname}_q.png"
            )
        else:
            fig.write_image(
                f"{path_outputs}/{modelname}/prediction_vs_real_best_prediction_{modelname}.png"
            )

    return fig


def compute_loss(
    models_dir,
    savename,
    datasets,  # Only for 2013!! all_years_datasets have to be filtered before
    tiles=1,
    size=128,
    resizing_size=128,
    n_epochs=2,
    n_bands=4,
    stacked_images=[1],
    generate=False,
    subset="val",
):
    # Computo val_loss por RC
    metrics_epochs = compute_custom_loss_all_epochs(
        models_dir=models_dir,
        savename=savename,
        datasets=datasets,
        tiles=tiles,
        size=size,
        resizing_size=resizing_size,
        n_epochs=n_epochs,
        n_bands=n_bands,
        stacked_images=stacked_images,
        verbose=True,
        generate=generate,
        subset="val",
    )
    optimal_epoch = metrics_epochs.loc[
        metrics_epochs["mse_test_rc"] == metrics_epochs["mse_test_rc"].min()
    ].index.values[0]

    # Computo test_loss por RC
    metrics_epochs = compute_custom_loss_for_epoch(
        models_dir=models_dir,
        savename=savename,
        datasets=datasets,
        tiles=tiles,
        size=size,
        resizing_size=resizing_size,
        n_epochs=n_epochs,
        n_bands=n_bands,
        stacked_images=stacked_images,
        verbose=True,
        generate=generate,
        subset=subset,
        epoch=optimal_epoch,
    )

    metrics_epochs = pd.read_csv(
        f"{path_dataout}/models_by_epoch/{savename}/{savename}_val_metrics_over_epochs.csv"
    )

    plot_mse_over_epochs(metrics_epochs, savename, metric="mse", save=True)
    plot_predictions_vs_real(
        savename, selected_epoch=optimal_epoch, quantiles=False, save=True
    )
    plot_predictions_vs_real(
        savename, selected_epoch=optimal_epoch, quantiles=True, save=True
    )


def rerun_train_val_metrics(
    model_name: str,
    pred_variable: str,
    kind: str,
    weights=None,
    image_size=512,
    resizing_size=200,
    tiles=1,
    n_bands=4,
    stacked_images=[1],
    sample_size=1,
    small_sample=False,
    n_epochs=100,
    initial_epoch=0,
    model_path=None,
    extra="",
):
    import main
    from keras.metrics import MeanSquaredError

    savename = f"{model_name}_size{image_size}_tiles{tiles}_sample{sample_size}{extra}"
    batch_size = 64

    ### Create train and test dataframes from ICPAG
    df_train, df_test, sat_img_dataset = main.create_train_test_dataframes(
        savename, small_sample=small_sample
    )

    ## Transform dataframes into datagenerators:
    #    instead of iterating over census tracts (dataframes), we will generate one (or more) images per census tract
    print("Setting up data generators...")
    train_dataset, test_dataset = main.create_datasets(
        df_train=df_train,
        df_test=df_test,
        sat_img_dataset=sat_img_dataset,
        image_size=image_size,
        resizing_size=resizing_size,
        n_bands=n_bands,
        stacked_images=stacked_images,
        tiles=tiles,
        sample=sample_size,
        batch_size=batch_size,
        savename=savename,
        save_examples=True,
    )

    # Compute metrics
    # Check if the CSV file exists, if not, create it with the column names
    csv_history_path = (
        f"{path_dataout}/models_by_epoch/{savename}/{savename}_history.csv"
    )
    store_dict = {
        "epoch": [],
        "loss": [],
        "mean_absolute_error": [],
        "mean_squared_error": [],
        "val_loss": [],
        "val_mean_absolute_error": [],
        "val_mean_squared_error": [],
    }
    pd.DataFrame(columns=store_dict.keys()).to_csv(csv_history_path, index=False)

    for epoch in range(0, n_epochs, 5):
        print("Epoch", epoch + 1)
        store_dict["epoch"] = epoch
        model = keras.models.load_model(
            f"{path_dataout}/models_by_epoch/{savename}/{savename}_{epoch}"
        )  # load the model from file

        losses = model.evaluate(train_dataset, steps=10_000 * sample_size / batch_size)
        store_dict["loss"] += [losses[0]]
        store_dict["mean_absolute_error"] += [losses[1]]
        store_dict["mean_squared_error"] += [losses[2]]

        losses = model.evaluate(test_dataset)
        store_dict["val_loss"] += [losses[0]]
        store_dict["val_mean_absolute_error"] += [losses[1]]
        store_dict["val_mean_squared_error"] += [losses[2]]

        history = pd.DataFrame().from_dict(store_dict)
        history.to_csv(csv_history_path, mode="a", header=False, index=False)
        store_dict = {
            "epoch": [],
            "loss": [],
            "mean_absolute_error": [],
            "mean_squared_error": [],
            "val_loss": [],
            "val_mean_absolute_error": [],
            "val_mean_squared_error": [],
        }

    # Plot metrics - Seteo bien el indice
    hist_df = pd.read_csv(
        rf"{path_dataout}/models_by_epoch/{savename}/{savename}_history.csv"
    ).set_index("epoch")
    hist_df.to_csv(rf"{path_dataout}/models_by_epoch/{savename}/{savename}_history.csv")

    plot_results(
        models_dir=rf"{path_dataout}/models_by_epoch/{savename}",
        savename=savename,
        tiles=tiles,
        size=image_size,
        resizing_size=resizing_size,
        n_epochs=hist_df.index.max(),
        n_bands=n_bands,
        stacked_images=stacked_images,
        generate=True,
    )

    return


if __name__ == "__main__":
    # size = 256
    # tiles = 1
    # sample = 10
    # extra ="_nostack"
    # savename = f"mobnet_v3_size{size}_tiles{tiles}_sample{sample}{extra}"
    # plot_results(
    #     models_dir=rf"/mnt/d/Maestría/Tesis/Repo/data/data_out/models_by_epoch/{savename}",
    #     savename=savename,
    #     tiles=tiles,
    #     size=size,
    #     resizing_size=128,
    #     n_epochs=80,
    #     n_bands=4,
    #     stacked_images=[1],
    #     generate=True,
    # )
    image_size = (
        128 * 2
    )  # FIXME: Creo que solo anda con numeros pares, alguna vez estaría bueno arreglarlo...
    sample_size = 5
    resizing_size = 128
    tiles = 1

    variable = "ln_pred_inc_mean"
    kind = "reg"
    model = "mobnet_v3"
    path_repo = r"/mnt/d/Maestría/Tesis/Repo/"
    extra = "_nostack"

    initial_epoch = 141
    rerun_train_val_metrics(
        model_name=model,
        pred_variable=variable,
        kind=kind,
        small_sample=False,
        weights=None,
        image_size=image_size,
        sample_size=sample_size,
        resizing_size=resizing_size,
        n_bands=4,
        tiles=tiles,
        stacked_images=[1],
        n_epochs=99,
        initial_epoch=initial_epoch,
        model_path=f"{path_repo}/data/data_out/models_by_epoch/{model}_size{image_size}_tiles{tiles}_sample{sample_size}{extra}/{model}_size{image_size}_tiles{tiles}_sample{sample_size}{extra}_{initial_epoch}",
        extra="_nostack",
    )
