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

    ineqdeco `varlist' [w`exp']
    local gini = r(gini)
	local p90_50 = r(p90p50)
    local p10_50 = r(p10p50)
    local p90_10 = r(p90p10)
	local atk1 = r(a1)
	local atk2 = r(a2)
	local theil = r(ge1)
    
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
		`p90_10' \  ///
		`p90_50' \ ///
		`p10_50' \ ///
		`gini' 	 \ ///
		`atk1' 	 \ ///
		`atk2' 	 \ ///
		`theil'  \ ///
		`fgt0_nac' \ ///
		`fgt1_nac' \ ///
		`fgt2_nac' ///
	)

	// Create a variable list with local names
	matrix rownames results = "Número de observaciones" "Media" "Mediana" "Ratio 90-10" "Ratio 90-50" "Ratio 10-50" "Gini" "Atkinson (1)" "Atkinson (2)" "Theil" "FGT(0) Nac 2010ppp" "FGT(1) Nac 2010ppp" "FGT(2) Nac 2010ppp"
	matrix colnames results = "`name'"

    // Return the matrix as a result
    return matrix results = results
end



*#############################*
*######### 2010/13 ###########*
*#############################*
*** DATOS EPH - 2do semestre 2010
use "${PATH_DATAOUT}/ARG_2010_EPHC-S2_v03_M_v06_A_SEDLAC-03_all_proc.dta", replace
keep if gba == 1

compute_table ipcf_ppp11 [w=pondera], name("Observado EPH")
matrix define eph2010 = r(results)

compute_table pred_ipcf_ppp11 [w=pondera], name("Predicción EPH")
matrix define eph2010_pred = r(results)

*** DATOS EPH - 2do semestre 2013
use "${PATH_DATAOUT}/ARG_2013_EPHC-S2_v03_M_v06_A_SEDLAC-03_all_proc.dta", replace
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
use "${PATH_DATAOUT}/proc_gridded_data_2013.dta", replace
compute_table predicted_income [w=personas], name("Prediccion Satélites")
matrix define grid_pred = r(results)

*#############################*
*#########   2018  ###########*
*#############################*

*** DATOS EPH - 1er semestre 2018
use "${PATH_DATAOUT}/ARG_2018_EPHC-S2_v01_M_v05_A_SEDLAC-03_all_proc.dta", replace
keep if gba == 1

compute_table ipcf_ppp11 [w=pondera]
matrix define eph2018 = r(results)
matrix colnames eph2018 = "Observado EPH"
compute_table pred_ipcf_ppp11 [w=pondera], name("Predicción EPH")
matrix define eph2018_pred = r(results)

*** DATOS GRILLA
use "${PATH_DATAOUT}/proc_gridded_data_2018.dta", replace
compute_table predicted_income [w=personas], name("Prediccion Satélites")
matrix define grid_pred_2018 = r(results)

*#############################*
*#########   2022  ###########*
*#############################*
*** DATOS EPH - 2do semestre 2022 
use "${PATH_DATAOUT}/ARG_2022_EPHC-S2_v01_M_v01_A_SEDLAC-03_all_proc.dta", replace
keep if gba == 1

compute_table ipcf_ppp11 [w=pondera]
matrix define eph2022 = r(results)
compute_table pred_ipcf_ppp11 [w=pondera]
matrix define eph2022_pred = r(results)

*** DATOS GRILLA
use "${PATH_DATAOUT}/proc_gridded_data_2022.dta", replace
compute_table predicted_income [w=personas]
matrix define grid_pred_2022 = r(results)


*########################################*
*######### Municipios 2010/13 ###########*
*########################################*


*# CENSO
capture frame create censo
capture frame create grilla
frame change censo
use "${PATH_DATAOUT}/census_data_amba.dta", replace

frame change grilla
use "${PATH_DATAOUT}/proc_gridded_data_2013.dta", replace

putexcel set "${PATH_OUTPUTS}\municipios.xlsx", modify
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
putexcel set "${PATH_OUTPUTS}/2010_results.xlsx", modify
putexcel A2 = matrix(eph2010), names
putexcel C2 = matrix(eph2010_pred), colnames
putexcel D2 = matrix(census), colnames
putexcel E2 = matrix(grid_pred), colnames
putexcel B1 = "2010"
putexcel C1 = "2010"
putexcel D1 = "2010"
putexcel E1 = "2013"
putexcel close

// Matriz evolución tiempo
putexcel set "${PATH_OUTPUTS}\results_over_time.xlsx", modify
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
