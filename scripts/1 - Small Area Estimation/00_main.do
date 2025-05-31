drop _all
set trace off
set graph off 
set more off 
*set scheme economist
timer clear 
*##########################################################*
*##############       01 MASTER      ###################*
*##########################################################*

*##############      Configuración    #####################*

clear all
cls

global path_compu "D:/Papers"
global proyecto "Tesis - Imagenes Satelitales AMBA"
global subproyecto "1 - Small Area Estimation"

qui do "${path_compu}/${proyecto}/scripts/${subproyecto}/plantilla.do" 
qui do "${path_compu}/${proyecto}/scripts/${subproyecto}/fgt.do" 
*fix me pla

/* Globales de las rutas definidas de forma automática:

$path_user 		- Ubicación de la carpeta del Proyecto
$path_datain	- Bases de datos inputs (raw y que recibis procesadas)
$path_dataout	- Bases procesadas por tus scripts
$path_scripts	- Ubicacion de dofiles, py, ipynb, etc.
$path_figures	- Output para las figuras/gráficos
$path_maps		- Output para los mapas (html o imagen)
$path_tables	- Output para las tablas (imagen o excel)
$path_programas	- Programas (fgt, gini, cuantiles, etc.)
*/

global path_ster "${path_dataout}\ster" 
capture mkdir "${path_dataout}\ster"

*############      Creo globales bases     ##############*
global prepara_censo     "${path_dataout}\prepara_censo"
global censo             "${path_dataout}\predict_censo"
global censo_analisis    "${path_dataout}\predict_ingreso_analisis" 
global collapse    		 "${path_dataout}\predict_ingreso_collapse" 

*global total_bases 30
global eph_estimacion "1"


*##########################################################*
****** crea variables en EPH y regresiona por MCO el ingreso percápita de pobreza moderada
timer on 1
do "${path_scripts}\01_prepara_eph.do"
dis "Terminó: 01_prepara_eph"
timer off 1

****** crea variables en Censo 2010 y arma los predict
timer on 2
do "${path_scripts}\02_censo_variables.do"
dis "Terminó: 02_censo_variables"
timer off 2
stop

****** Agrega preedicciones por radio censal
timer on 4
do "${path_scripts}\03_collapse_link.do"
dis "Terminó: 03_collapse_link"
timer off 4

display "Small Area estimates created correctly! Available in {path_dataout}/small_area_estimates.parquet"

