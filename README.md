# Income Maps Using High-Resolution Satellite Imagery and Machine Learning

## Overview

In this repository, we provide the code and data for our study, forthcoming in *PLOS ONE*. We explored the use of high-resolution satellite imagery and machine learning techniques to create detailed income maps. Specifically, we trained a convolutional neural network (CNN) using satellite images from the Metropolitan Area of Buenos Aires, Argentina, along with 2010 census data to estimate per capita income at a 50x50 meter resolution for the years 2013, 2018, and 2022. Our model, based on the EfficientnetV2 architecture, demonstrated a high accuracy in predicting household incomes, achieving an R2 score of 0.878, and surpassed the spatial resolution and performance of existing methods in the literature.

## Abstract

High-resolution income data is crucial for informing policy decisions as it allows policymakers to better understand the distribution of wealth and poverty. However, this type of information is often cost-prohibitive, especially in developing countries. We evaluate the potential of using high-resolution satellite imagery and machine learning techniques to create income maps with a high level of geographic detail. We train a neural network with satellite images from the Metropolitan Area of Buenos Aires (Argentina) and 2010 census data to estimate per capita income at a 50x50 meter resolution for 2013, 2018 and 2022. The model, based on the EfficientNetV2 architecture, demonstrates strong predictive accuracy for household incomes ($R^2=0.878$), achieving a spatial resolution over 20 times finer than existing methods in the literature. The model also allows estimating income maps for arbitrary images, and can therefore be applied at any point in time. This approach opens up new possibilities for generating highly detailed data, which can be used to assess public policies at a local level, target social programs more effectively, and address information gaps in areas where traditional data collection methods are lacking.


## Data Availability and Restrictions

Unfortunately, the satellite imagery utilized in this study is proprietary and subject to legal restrictions imposed by Airbus DS Geo SA and the Argentine National Commission for Space Activities (CONAE). Under the end-user license agreement, raw satellite imagery cannot be distributed publicly or shared with third parties.

However, to ensure transparency and reproducibility, we provide all derived data and resources permissible under these restrictions:

- Argentina's 2010 Census and Survey Dataset (S1 Dataset): Publicly available via Zenodo at DOI: [Insert your Zenodo DOI for S1 Dataset]. This dataset is used for replicating the small-area estimates employed in model training (the scripts available in `1 - Small Area Estimation`).

- Derived Income Estimates (S2 Dataset): Aggregated per capita income estimates at census tract level and detailed 50x50m gridded income predictions for 2013, 2018, and 2022. Publicly available via Zenodo at DOI: [Insert your Zenodo DOI for S2 Dataset]. These estimates are the result of running `2 - Model Training\main.py`. These results are used for replicating all the figures and tables presented in the Results section of the paper, via running the scripts from `3 - Tables and Figures`.

- Trained Model Weights (S3 Dataset): EfficientNetV2 model weights (for 4-band and 8-band inputs). Available via Zenodo at DOI: [Insert your Zenodo DOI for S3 Dataset]. Although these weights are not essential for replicating the primary findings, they are provided for further model fine-tuning in other contexts.

## Repository Contents

- *`1 - Small Area Estimation`*: All the scripts used for generating the training labels, derived from the methodology depicted in Section 5.1 from the main paper. By running `00_main.do` in STATA, the user should be able to replicate the maps later used by the function `build_dataset.load_icpag_dataset()` from the `2 - Model Training` section.
- *`2 - Model Training`*: Scripts for training the CNN via pairing the satellite images with the resulting SAE. The scripts are built modular, so that the user can modify the CNN architecture from keras (via modifying `custom_models`). Furthermore, the input function from the data could be modified so different satellite imagery is used. These scripts are run in python. GPU accelerated training requires these scripts to be run in Windows WSL or any Linux ditro.
- *`3 - Tables and Figures`*: Scripts for replicating the figures and tables from the Results section of the paper. They can be run by running `00_main.do` in STATA.
- `README.md`: This file provides an overview and instructions for the repository.

## Relevant Links


- [Preprint Paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5026760) - Deep Learning with Satellite Images Enables High-Resolution Income Estimation: A Case Study of Buenos Aires. R&R at PLOS ONE.
- [Visualize the income predictions!](https://ingresoamba.netlify.app) - In this link you can compare the satellite images of 2023 with the income predictions for 2013, 2018, and 2022.
- [Download the data](https://zenodo.org/records/13251268) - Predictions for AMBA region in geoparquet format and model weights at Zenodo repo.


## Examples of the model performance 

![Fig9](https://github.com/user-attachments/assets/9b275556-6446-40a3-bdb2-2ffa0006cb57)

![Fig11](https://github.com/user-attachments/assets/906f8b60-f5dc-4f80-acf6-c177486f88e4)

![Fig14](https://github.com/user-attachments/assets/7832045b-c1f0-4b18-9684-e4f78854275b)

### License

This project is licensed under the MIT License. See the LICENSE file for details.
