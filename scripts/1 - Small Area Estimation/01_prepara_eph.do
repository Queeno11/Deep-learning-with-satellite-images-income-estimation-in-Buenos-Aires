drop _all
loc base_1 "ARG_2010_EPHC-S2_v03_M_v06_A_SEDLAC-03_all"
loc base_2 "ARG_2013_EPHC-S2_v03_M_v06_A_SEDLAC-03_all"
loc base_3 "ARG_2018_EPHC-S2_v01_M_v05_A_SEDLAC-03_all"
loc base_4 "ARG_2022_EPHC-S2_v01_M_v01_A_SEDLAC-03_all"

* variables independientes
loc vjefe "c.hombre c.edad c.edad2 c.pric c.seci c.secc c.supi c.supc"
loc vviv "c.hv_precaria c.hv_matpreca c.hv_agua c.hv_banio c.hv_cloacas c.hv_propieta "
loc vhog "c.hv_miemhabi c.miembros " 
loc vreg "reg3 reg4 reg5 reg6 reg7 reg8 reg9 reg10 reg12 reg13 reg14 reg15 reg17 reg18 reg19 reg20 reg22 reg23 reg25 reg26 reg27 reg29 reg30 reg31 reg32 reg33 reg34 reg36 "


foreach i in "1" "2" "3" {

	drop _all
	est clear
	noi di "i: `i'"
	noi use "${path_datain}\\`base_`i''.dta"
	noi include "${path_scripts}\01a_variables_censo.doi"
	if "`i'"=="${eph_estimacion}" {
		noi include "${path_scripts}\01b_estima_modelo.doi"
	}
	predict ln_pred_ipcf_ppp11
	gen pred_ipcf_ppp11 = exp(ln_pred_ipcf_ppp11)	
	save "${path_dataout}\\`base_`i''_proc.dta", replace
}
use "${path_dataout}\\`base_${eph_estimacion}'_proc.dta", replace
 