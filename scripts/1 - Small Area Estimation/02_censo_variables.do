noi include "${path_scripts}\02a_prepara_censo.doi"
keep if jefe==1
save "${prepara_censo}", replace
 
estimates use "${path_dataout}\ster\MCO_ingreso_`i'"
predict pp`i'
gen ln_pp`i' = .
replace ln_pp`i' = pp`i'
replace pp`i' = exp(pp`i')

save "${path_dataout}\predict_censo.dta", replace
