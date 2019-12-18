#!/bin/bash
# For any students with multiple files, delete the one which seems to be part 2

shopt -s extglob
shopt -s nullglob
shopt -s nocaseglob

for student in $(ls *.xls* | sed 's/_.*//' | uniq -d)
do
    didit=0
    fils=("$student"*.xls*)
    twofils=("$student"_?(LATE_)+([0-9])_+([0-9])_*@(Part|P|pt|_|11)*(_|\ |-|.)2*.xls*)
    if [[ ${#twofils[@]} -gt 0 && ${#twofils[@]} -lt ${#fils[@]} ]]
    then
        echo "Deleting ${twofils[@]}"
        rm "${twofils[@]}"
        didit=1
    fi
    fils=("$student"*.xls*)
    mfils=("$student"*@(Module|Mod|M)*(_|\ |-)@(1_|1\ |1-|1.|[23456789]|10)*xls*)
    if [[ ${#mfils[@]} -gt 0 && ${#mfils[@]} -lt ${#fils[@]} ]]
    then
        echo "Deleting ${mfils[@]}"
        rm "${mfils[@]}"
        didit=1
    fi
    if [[ didit -ne 0 ]]; then
        echo "Left " $student*.xls*
    fi
done

