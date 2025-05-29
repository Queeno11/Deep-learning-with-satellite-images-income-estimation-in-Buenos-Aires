
******************************************
****    medidas por radios censales
******************************************
foreach i in mean median{
	use "${path_dataout}\predict_censo.dta", replace
	collapse (`i') pp ln_pp , by(link)
	sort link
	rename pp pred_inc_`i'
	rename ln_pp ln_pred_inc_`i'
	save "${path_dataout}/predict_ingreso_link`i'.dta"
}

* Export dataset
python:
from sfi import Macro
import pandas as pd
import geopandas as gpd

path_datain = Macro.getGlobal('path_datain')
path_dataout = Macro.getGlobal('path_dataout')


df = pd.read_stata(rf"{path_dataout}\predict_ingreso_linkmean.dta")
gdf = gpd.read_file(rf"{path_datain}\radios_eph_with_link.shp") 

df["link_radio"] = df["link_radio"].astype(int)
gdf["link_radio"] = gdf["link_radio"].astype(int)
gdf = gdf.dissolve(by="link_radio", aggfunc="first")

gdf = gdf.merge(df, on="link_radio", validate="1:1", how="right")
gdf = gdf.rename(columns={"link_radio": "link"})
gdf["AMBA_legal"] = gdf["eph_codagl"].isin(["33", "32", "02"])
gdf["Area"] = gdf["geometry"].area  # Convert to square kilometers

gdf.to_parquet(rf"{path_dataout}\small_area_estimates.parquet")
end