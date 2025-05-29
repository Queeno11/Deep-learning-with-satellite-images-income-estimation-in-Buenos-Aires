***** Datos Censo y grilla predicciones a .dta

// python script "D:\Maestría\Tesis\3. Resultados post estimacion\scripts\01_prepara_bases.py"

****** CREATE A SINGLE CENSUS DATASET (icpag+predict_sae)

** ICPAG data
use "${PATH_DATAIN}/census_data.dta", clear
keep link AREA departamento provincia eph_codagl eph_aglome codaglo aglomerado aglo_eph AMBA_legal rmin rmax rminp50 rminp25 rminp75 rmaxp50 rmaxp25 rmaxp75 p_usd pm2 obs_pm2 pm2_2019 obs_pm2_19 p_usd_2019 personas viv_part den_p totalpobl icv2010 tasa_activ tasa_emple tasa_desoc total total_val con_nbi sin_nbi nbi_rc nbi_rc_val icpagNabs
keep if eph_codagl == 1 // Solo AMBA (CABA + Partidos GBA)

** Add SAE data
merge 1:1 link using "${SAE_DATA}", keep(3) nogen

save "${PATH_DATAOUT}/census_data_amba.dta", replace

****** FORMAT GRID PREDICTIONS

** Get locals to destandarize values
import delimited using "D:\Maestría\Tesis\Repo\data\data_out\scalars_ln_pred_inc_mean_trimTrue.csv", clear
local var_mean = ln_pred_inc_mean[1]
local var_std = ln_pred_inc_mean[2]

** Grid data 
foreach year in 2013 2018 {

	use "${PATH_DATAOUT}/gridded_data_`year'_${SAVENAME}.dta", replace

	gen ln_predicted_income = prediction * `var_std' + `var_mean'
	gen predicted_income = exp(ln_predicted_income )
	egen repetitions = count(link), by(link)
	replace personas = round(personas / repetitions)
	save "${PATH_DATAOUT}/proc_gridded_data_`year'_${SAVENAME}.dta", replace
}

****** DATA FROM EPH PROCESSED
local n_bases = 37

// forvalues i = 1/`n_bases' {
// 	use "$EPH_PROC_DATA/base_`i'_proc.dta"
// 	if `i'==2 {
// 		break
// 	}
// }



