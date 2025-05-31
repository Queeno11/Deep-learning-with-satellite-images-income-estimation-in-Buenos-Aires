# 🧩 Replication Package

Thanks for downloading this replication package!  
We hope it helps with your research 😊

Below is a quick breakdown of what each file in the package contains and how it's used:

---

## 📂 DATA – Replicating Small Area Estimation

### 🇦🇷 Argentina Household Survey Data (Encuesta Permanente de Hogares – EPH)
- `ARG_2010_EPHC-S2_v03_M_v06_A_SEDLAC-03_all.dta`  
- `ARG_2013_EPHC-S2_v03_M_v06_A_SEDLAC-03_all.dta`  
- `ARG_2018_EPHC-S2_v01_M_v05_A_SEDLAC-03_all.dta`  
- `ARG_2022_EPHC-S2_v01_M_v01_A_SEDLAC-03_all.dta`  

These are processed microdata files from Argentina’s household survey.  
Processing was done by **SEDLAC** — [More info here](https://www.cedlas.econo.unlp.edu.ar/wp/en/estadisticas/sedlac/)

---

### 🧾 Argentina Census Microdata  
- `censo2010_fullraw_p.dta`  

Raw census microdata from 2010. You can access the original dataset via **REDATAM**.

---

### 🗺️ Census Tract Map  
- `radios_eph_with_link.shp`  

Shapefile of Argentina’s 2010 census tracts, with linkage info for merging.

---

### 📊 Small Area Estimates Output  
- `small_area_estimates.parquet`  

This is the final output of the Small Area Estimation (SAE) process. It includes census tracts along with population data and estimated income levels.

---

## 📂 DATA – Replicating Paper Results (CNN-based Predictions)

### 🧠 CNN Model Income Predictions (Buenos Aires)
- `income_estimates_2013.shp`  
- `income_estimates_2018.shp`  
- `income_estimates_2022.shp`  

Gridded predictions (~50x50m resolution) for the City of Buenos Aires from the CNN model.

---

### 📐 Scalars to Normalize Model Outputs  
- `scalars_ln_pred_inc_mean_trimTrue.csv`  

The CNN model outputs are standardized (log-scale). Use these scalars to convert them into real income values in **2010 PPP-adjusted Argentinian pesos**.

---

### 🛰️ World Settlement Footprint (WSF)  
- `WSF2015_v2_-60_-36.tif`  

Satellite-based data identifying human settlements. Used to mask out model predictions in uninhabited areas. Source: [DLR WSF2015](https://download.geoservice.dlr.de/WSF2015/)

---

If you have questions or need help replicating any of the results, feel free to reach out at abbatenicolas@gmail.com!
