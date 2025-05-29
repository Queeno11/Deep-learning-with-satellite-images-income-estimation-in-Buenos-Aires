* Read the file list in Stata
capture file close _myfile
file open _myfile using "${EPH_DATA}\EPH_paths.csv", read
file read _myfile line

* Initialize a local macro to store file paths
local file_paths ""
local n_bases = 0

* Loop through each line in the file
while r(eof) == 0 {
	* Split the line into local name and value
	tokenize `line', parse(";")
	
	* Save as locals
	local base_name = "`1'"
	macro shift
	local base_path = "`2'"
	local `base_name' = "`base_path'"
	local ++n_bases

    file read _myfile line
}
* Close the file
file close _myfile
display `n_bases'

