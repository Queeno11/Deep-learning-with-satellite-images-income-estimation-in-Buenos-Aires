capture mkdir "${PATH_OUTPUTS}/${SAVENAME}"
capture program drop compute_table
program define compute_table, rclass
	syntax varlist(max=1) [aweight] [, Name(string)]
    // Calculate summary statistics
	display "`varlist' `weight' `exp'"
    sum `varlist' [`weight' `exp'], detail

    // Store local macros
	local obs =  r(N)
    local mean = r(mean)
    local median = r(p50)
    local r90_10 = r(p90) / r(p10)
    local r50_10 = r(p50) / r(p10)

    gini `varlist' [w`exp']
    local gini = r(gini)

    // LP 6.85
	fgt `varlist' [w`exp'], alfa(0) zeta(15*30) 
    local fgt0_a = r(fgt)
    fgt `varlist' [w`exp'], alfa(1) zeta(15*30)
    local fgt1_a = r(fgt)
    fgt `varlist' [w`exp'], alfa(2) zeta(15*30)
    local fgt2_a = r(fgt)

	// LP 3.65
	fgt `varlist' [w`exp'], alfa(0) zeta(3.65*30) 
    local fgt0_m = r(fgt)
    fgt `varlist' [w`exp'], alfa(1) zeta(3.65*30)
    local fgt1_m = r(fgt)
    fgt `varlist' [w`exp'], alfa(2) zeta(3.65*30)
    local fgt2_m = r(fgt)
	
	// LP 434.204521 -- canasta a julio 2016 ajustada por ppp 2016 (4033.76 / 9.29)
	fgt `varlist' [w`exp'], alfa(0) zeta(434.204521) 
    local fgt0_nac = r(fgt)
    fgt `varlist' [w`exp'], alfa(1) zeta(434.204521)
    local fgt1_nac = r(fgt)
    fgt `varlist' [w`exp'], alfa(2) zeta(434.204521)
    local fgt2_nac = r(fgt)

	// Create a matrix with local names and their values
	matrix input results = ( ///
		`obs'	 \ ///
		`mean'   \ ///
		`median' \ ///
		`r90_10' \  ///
		`r50_10' \ ///
		`gini' 	 \ ///
		`fgt0_a' \ ///
		`fgt1_a' \ ///
		`fgt2_a' \ ///
		`fgt0_m' \ ///
		`fgt1_m' \ ///
		`fgt2_m' \ ///
		`fgt0_nac' \ ///
		`fgt1_nac' \ ///
		`fgt2_nac' ///
	)

	// Create a variable list with local names
	matrix rownames results = "Número de observaciones" "Media" "Mediana" "Ratio 90-10" "Ratio 50-10" "Gini" "FGT(0) 6.85USD/dia" "FGT(1) 6.85USD/dia" "FGT(2) 6.85USD/dia" "FGT(0) 3.65USD/dia" "FGT(1) 3.65USD/dia" "FGT(2) 3.65USD/dia" "FGT(0) Nac 2010ppp" "FGT(1) Nac 2010ppp" "FGT(2) Nac 2010ppp"
	matrix colnames results = "`name'"

    // Return the matrix as a result
    return matrix results = results
end



*#############################*
*######### 2010/13 ###########*
*#############################*
*** DATOS EPH - 2do semestre 2010
use "${EPH_PROC_DATA}/base_15_proc.dta", replace
keep if gba == 1

compute_table ipcf_ppp11 [w=pondera], name("Observado EPH")
matrix define eph2010 = r(results)

compute_table pred_ipcf_ppp11 [w=pondera], name("Predicción EPH")
matrix define eph2010_pred = r(results)

*** DATOS EPH - 1er semestre 2013
use "${EPH_PROC_DATA}/base_20_proc.dta", replace
keep if gba == 1

compute_table ipcf_ppp11 [w=pondera], name("Observado EPH")
matrix define eph2013 = r(results)

compute_table pred_ipcf_ppp11 [w=pondera], name("Predicción EPH")
matrix define eph2013_pred = r(results)

*** DATOS CENSO
use "${PATH_DATAOUT}/census_data_amba.dta", replace
compute_table pred_inc_mean [w=personas], name("Censo SAE")
matrix define census = r(results)

*** DATOS GRILLA
use "${PATH_DATAOUT}/proc_gridded_data_2013_${SAVENAME}.dta", replace
compute_table predicted_income [w=personas], name("Prediccion Satélites")
matrix define grid_pred = r(results)

*#############################*
*#########   2018  ###########*
*#############################*

*** DATOS EPH - 1er semestre 2018
use "${EPH_PROC_DATA}/base_27_proc.dta", replace
keep if gba == 1

compute_table ipcf_ppp11 [w=pondera]
matrix define eph2018 = r(results)
matrix colnames eph2018 = "Observado EPH"
compute_table pred_ipcf_ppp11 [w=pondera], name("Predicción EPH")
matrix define eph2018_pred = r(results)

*** DATOS GRILLA
use "${PATH_DATAOUT}/proc_gridded_data_2018_${SAVENAME}.dta", replace
compute_table predicted_income [w=personas], name("Prediccion Satélites")
matrix define grid_pred_2018 = r(results)

*#############################*
*#########   2022  ###########*
*#############################*
* FIXME: Agregar cuando funcione 2022
// *** DATOS EPH - 2do semestre 2022 
// use "${EPH_PROC_DATA}/base_37_proc.dta", replace
// keep if gba == 1
//
// compute_table ipcf_ppp11 [w=pondera]
// matrix define eph2022 = r(results)
// compute_table pred_ipcf_ppp11 [w=pondera]
// matrix define eph2022_pred = r(results)
//
// *** DATOS GRILLA
// use "${PATH_DATAOUT}/predictions_amba_2022_${SAVENAME}.dta", replace
// compute_table predicted_income [w=personas]
// matrix define grid_pred_2022 = r(results)


*########################################*
*######### Municipios 2010/13 ###########*
*########################################*


*# CENSO
capture frame create censo
capture frame create grilla
frame change censo
use "${PATH_DATAOUT}/census_data_amba.dta", replace

frame change grilla
use "${PATH_DATAOUT}/proc_gridded_data_2013_${SAVENAME}.dta", replace

putexcel set "${PATH_OUTPUTS}/${SAVENAME}\municipios_${SAVENAME}.xlsx", modify
putexcel B1:P1 = "Censo SAE"
putexcel Q1:AF1 = "Prediccion Satélites"

frame change censo
levelsof departamento, local(deptos)
local i = 3
foreach depto in `deptos' {

	frame change censo
	preserve
	keep if departamento == "`depto'"
	compute_table pred_inc_mean [w=personas], name("`depto'")
	matrix define current_depto = r(results)	
	matrix define current_depto = current_depto'	
	if `i'==3 {
		putexcel A2 = matrix(current_depto), names
	}
	else {
		putexcel A`i' = matrix(current_depto), rownames		
	}
	restore

 	frame change grilla
	preserve
	keep if departamento == "`depto'"
	qui count
	if r(N)>0 {
		compute_table predicted_income [w=personas], name("`depto'")
		matrix define current_depto = r(results)	
		matrix define current_depto = current_depto'	
		if `i'==3 {
			putexcel Q2 = matrix(current_depto), colnames		
		}
		else {
			putexcel Q`i' = matrix(current_depto)		
		}
	}
	restore
	
	local ++i
}


*#############################*
*########   Tablas  ##########*
*#############################*
// Matriz comparación estática 2010/13
putexcel set "${PATH_OUTPUTS}/${SAVENAME}\2010_results_${SAVENAME}.xlsx", modify
putexcel A2 = matrix(eph2010), names
putexcel C2 = matrix(eph2010_pred), colnames
putexcel D2 = matrix(eph2013), colnames
putexcel E2 = matrix(eph2013_pred), colnames
putexcel F2 = matrix(census), colnames
putexcel G2 = matrix(grid_pred), colnames
putexcel B1 = "2010"
putexcel C1 = "2010"
putexcel D1 = "2013"
putexcel E1 = "2013"
putexcel F1 = "2010"
putexcel G1 = "2013"
putexcel close

// Matriz evolución tiempo
putexcel set "${PATH_OUTPUTS}/${SAVENAME}\results_over_time_${SAVENAME}.xlsx", modify
putexcel A2 = matrix(eph2013), names
putexcel C2 = matrix(eph2013_pred), colnames
putexcel D2 = matrix(grid_pred), colnames
putexcel E2 = matrix(eph2018), colnames
putexcel F2 = matrix(eph2018_pred), colnames
putexcel G2 = matrix(grid_pred_2018), colnames
putexcel B1 = "2013"
putexcel C1 = "2013"
putexcel D1 = "2013"
putexcel E1 = "2018"
putexcel F1 = "2018"
putexcel G1 = "2018"
putexcel close


**** Plot del ingreso estático
use "${PATH_DATAOUT}/census_data_amba.dta", replace
append using "${EPH_PROC_DATA}/base_15_proc.dta", force
*pais==. son los datos del censo!
keep if gba == 1 | pais=="" 
append using "${PATH_DATAOUT}/predictions_amba_2013_${SAVENAME}.dta", force

set graph on
twoway ///
	(kdensity ipcf_ppp11 [w=pondera] if ipcf_ppp11<2000) ///
	(kdensity pred_ipcf_ppp11 [w=pondera] if pred_ipcf_ppp11<2000) ///
	(kdensity pred_inc_mean [w=personas] if pred_inc_mean<2000) ///
	(kdensity predicted_income [w=personas] if predicted_income<2000), ///
	title($SAVENAME) legend(order(1 "Ingreso EPH 2S2010" 2 "Predicción ingreso EPH 2S2010" 3 "Predicción ingreso Censo 2010" 4 "Predicción imágenes satelitales 1S2013"))

graph export  "${PATH_OUTPUTS}/${SAVENAME}\distribucion_ingresos_${SAVENAME}.png", replace


**** Plot evolución del ingreso
// use "${PATH_DATAOUT}/census_data_amba.dta", replace
// append using "${EPH_PROC_DATA}/base_15_proc.dta", force
// append using "${PATH_DATAOUT}/predictions_amba_2013_${SAVENAME}.dta", force
//
// set graph on
// twoway ///
// 	(kdensity ipcf_ppp11 [w=pondera] if ipcf_ppp11<2000) ///
// 	(kdensity pred_ipcf_ppp11 [w=pondera] if pred_ipcf_ppp11<2000) ///
// 	(kdensity pred_inc_mean [w=personas] if pred_inc_mean<2000) ///
// 	(kdensity predicted_income [w=personas] if predicted_income<2000), ///
// 	title($SAVENAME) legend(order(1 "Ingreso EPH 2S2010" 2 "Predicción ingreso EPH 2S2010" 3 "Predicción ingreso Censo 2010" 4 "Predicción imágenes satelitales 1S2013"))
//
// graph export  "${PATH_OUTPUTS}\distribucion_ingresos_${SAVENAME}.png", replace
