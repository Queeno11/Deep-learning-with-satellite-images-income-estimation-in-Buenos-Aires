drop _all
loc base_15 "ARG_2010_EPHC-S2"

* variables independientes
loc vjefe "c.hombre c.edad c.edad2 c.pric c.seci c.secc c.supi c.supc"
loc vviv "c.hv_precaria c.hv_matpreca c.hv_agua c.hv_banio c.hv_cloacas c.hv_propieta "
loc vhog "c.hv_miemhabi c.miembros " 
loc vreg "reg3 reg4 reg5 reg6 reg7 reg8 reg9 reg10 reg12 reg13 reg14 reg15 reg17 reg18 reg19 reg20 reg22 reg23 reg25 reg26 reg27 reg29 reg30 reg31 reg32 reg33 reg34 reg36 "

loc i = $eph_seleccionada

drop _all
est clear
noi di "i: `i'"
noi use "${path_datain}\\`base_`i''_v03_M_v06_A_SEDLAC-03_all.dta"
noi include "${path_scripts}\01a_variables_censo.doi"
noi include "${path_scripts}\01b_estima_modelo.doi"
save "${path_dataout}\\`base_`i''_v03_M_v01_A_SEDLAC-03_proc.dta", replace
exit

// capture erase  "${path_tables}\modelos_`i'.xlsx"
//
// ******************
// *MCO Ingreso
// eststo: noi reg ln_ipcf_ppp11 `vjefe' `vviv' `vhog' `vreg'
// *esttab, b(3) not noobs mtitle("Ingreso Esperado")
// esttab using "${path_tables}\\regresion_`i'", replace b(3) se(3) noobs not mtitle("Ingreso Esperado")	 ///
// booktabs long alignment(D{.}{.}{-1}) 																		///
// title("Tabla `i'") addnotes("Elaboración propia en base a EPH")
// noi estimates save "${path_dataout}\ster\MCO_ingreso_`i'", replace
// capture erase  "${path_dataout}\ster\MCO_ingreso_`i'.txt"
// outreg2 using  "${path_dataout}\ster\MCO_ingreso_`i'.txt", append ctitle("`EPH_`i''")
// outreg2 using  "${path_tables}\modelos_`i'.xlsx", append ctitle("MCO")
//
// * exporto outreg a excel
// preserve
// drop _all
// import delimited using "${path_dataout}\ster\MCO_ingreso_`i'.txt", clear
// export excel using "${path_tables}\MCO_ingreso.xlsx", cell(a1) sheetmodify sheet("MCO_ingreso`i'")
// restore
// ******************