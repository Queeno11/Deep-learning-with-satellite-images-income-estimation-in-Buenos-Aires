drop _all
set trace off
set graph off 
set more off 
*set scheme economist
timer clear 
// set python_exec "C:\Users\ofici\AppData\Local\Programs\Python\Python311\python.exe"

*##########################################################*
*##############       01 MASTER      ###################*
*##########################################################*

*##############      Configuración    #####################*

clear all
cls
capture set python_exec "C:\Users\ofici\AppData\Local\Programs\Python\Python311\python.exe"

global PATH_PROYECTO = "D:\Papers\Tesis - Imagenes Satelitales AMBA" 
global PATH_SCRIPTS = "${PATH_PROYECTO}\scripts\3 - Tables and Figures" 
global PATH_DATAIN 	= "${PATH_PROYECTO}\data\data_in" 
global PATH_DATAOUT = "${PATH_PROYECTO}\data\data_out" 
global PATH_OUTPUTS = "${PATH_PROYECTO}\outputs" 

// global CENSUS_DATA = r(CENSUS_DATA)
// global SAE_DATA = r(SAE_DATA)
// global SAE_SCRIPTS = r(SAE_SCRIPTS)
// global GRID_PREDS_FOLDER = r(GRID_PREDS_FOLDER)
// global EPH_PROC_DATA = r(EPH_PROC_DATA)

/* Globales de las rutas definidas de forma automática:
$PATH_PROYECTO	- Ubicación de la carpeta donde se contiene el proyecto
$PATH_SCRIPTS 	- Ubicacion de dofiles, py, ipynb, etc.
$PATH_DATAIN 	- Datos crudos
$PATH_DATAOUT	- Bases procesadas por los scripts
$PATH_OUTPUTS 	- Outputs como tablas, figuras, etc.
*/
qui do "D:\Papers\Tesis - Imagenes Satelitales AMBA\scripts\1 - Small Area Estimation\fgt.do" 


*##########################################################*
// ****** Preprocesa grilla (limpia areas donde no hay gente)
// timer on 1
// python script "${PATH_SCRIPTS}\01_preprocesa_grilla.py"
// dis "Terminó: 01_preprocesa_grilla"
// timer off 1
//
// // // ****** Busca las bases en otros repositorios y pasa a dta
// timer on 1
// python script "${PATH_SCRIPTS}\02_query_data.py"
// dis "Terminó: 02_query_data"
// timer off 1
//
// // ****** Emprolija las bases
// timer on 2
// do "${PATH_SCRIPTS}\03_prepara_bases.do"
// dis "Terminó: 03_prepara_bases"
// timer off 2

// ****** Corre tablas y graficos
timer on 3
do "${PATH_SCRIPTS}\04_calcula_tablas.do"
dis "Terminó: 04_calcula_tablas"
timer off 3


timer list 
