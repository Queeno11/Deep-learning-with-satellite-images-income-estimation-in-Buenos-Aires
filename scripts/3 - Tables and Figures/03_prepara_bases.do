***** Datos Censo y grilla predicciones a .dta

// python script "D:\Maestría\Tesis\3. Resultados post estimacion\scripts\01_prepara_bases.py"

****** CREATE A SINGLE CENSUS DATASET (icpag+predict_sae)

** ICPAG data
use "${PATH_DATAIN}/census_data.dta", clear
keep link Area departamento eph_codagl aglomerado AMBA_legal
keep if AMBA_legal == 1 // Solo AMBA (CABA + Partidos GBA)

** Add SAE data
duplicates drop link, force
merge 1:1 link using "${PATH_DATAOUT}/small_area_estimates.dta", keep(3) nogen

save "${PATH_DATAOUT}/census_data_amba.dta", replace

****** FORMAT GRID PREDICTIONS

** Get locals to destandarize values
import delimited using "${PATH_DATAOUT}/scalars_ln_pred_inc_mean_trimTrue.csv", clear
local var_mean = ln_pred_inc_mean[1]
local var_std = ln_pred_inc_mean[2]

** Grid data 
foreach year in 2013 2018 2022 {

	use "${PATH_DATAOUT}/gridded_data_`year'.dta", replace

	gen ln_predicted_income = prediction * `var_std' + `var_mean'
	gen predicted_income = exp(ln_predicted_income )
	egen repetitions = count(link), by(link)
	replace personas = round(personas / repetitions)
	sum ln_predicted_income
	display r(mean)
	sum predicted_income
	display r(mean)
	save "${PATH_DATAOUT}/proc_gridded_data_`year'.dta", replace
}


