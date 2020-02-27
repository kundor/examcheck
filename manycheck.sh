#!/bin/bash

# # to get lists: something like
# ls *_+([0-9])_+([0-9])_*[_\ DEdeMm#-]4* > list-4
# # Find those listed twice:
# cat list-* | sort | uniq -cd
# # Find those not listed:
# for f in *.xlsx; do grep -q "$f" list-* || echo "$f not found"; done
# 

if [[ $# -ne 1 ]]; then
    echo "One argument: Semester (e.g. S19)" >&2
    exit 1
fi
if ! [[ -e ../allnames && -e ../instructor-sections && -e ../all-modder ]]; then
    echo "In the wrong place?" >&2
    exit 2
fi
for k in {2..10}
do
    if ! [[ -e list-$k ]]; then
        echo "Please make lists of spreadsheets for each module, named list-2 to list-10" >&2
        exit 2
    fi
    orgfile="../original/Module_${k}_$1.xlsx" 
    if ! [[ -e $orgfile ]]; then
        echo "Please put original file at $orgfile" >&2
        exit 2
    fi
done

RED=$(echo -e "\e[31m")
DEF=$(echo -e "\e[39m")

declare -A stunames stusec instsec backsec reports # grades
declare -a instructors

# dunno how to get grades
#if ! [[ -e grades ]]; then
#    echo "No grades" >&2
#else
#while IFS=$'\t' read name grade; do
#    grades[$name]="$grade"
#done < grades
#fi

while IFS=$'\t' read code name sec; do
    stunames[$code]="$name"
    stusec[$code]="$sec"
done < ../allnames


while IFS=$'\t' read name secs; do
    instructors+=( "$name" )
    backsec[$name]="$secs"
    for sec in $secs; do
        instsec[$sec]="$name" 
    done
done < ../instructor-sections

reportline() {
    nm="${1%%[._]*}"
    shift
    local sect="${stusec[$nm]}"
    local instr="${instsec[$sect]}"
    local sname="${stunames[$nm]}"
#    local sgrad="${grades[$sname]}"
    printf "%-20s %-4s %-25s" "$instr" "$sect" "$sname"
    echo "$@"
    printf -v msg "%-4s %-24s" "$sect" "$sname"
    reports[$sect]+="$msg $*"$'\n'
}

istempfile() {
    tempmsg=''
    local siz=$(stat -c%s "$1")
    local typ=$(file --brief "$1")
    local nm=${1%%_*} 
    if ((siz<500)) && [[ $typ == "data" && $1 == *\~\$* ]]; then
        tempmsg="Temp file: $1"
    elif [[ $typ == "data" && $1 == *\~\$* ]]; then
        tempmsg="Big temp file? $1"
    elif ((siz<500)) && [[ $typ == "data" ]]; then
        tempmsg="Misnamed temp file? $1"
    elif ((siz<500)) && [[ $1 == *\~\$* ]]; then
        tempmsg="Temp file?? $1"
    elif ((siz<500)); then
        tempmsg="Tiny file: $1"
    elif [[ $typ == "data" ]]; then
        tempmsg="Not an Excel file? $1"
    elif [[ $1 == *\~\$* ]]; then
        echo "Bad name, but apparently okay: $1" >&2
    fi 
    [[ -n $tempmsg ]] # return value
}

for f in *xlsx; do
    if istempfile "$f"; then
        reportline "$f" "$tempmsg"
        rm "$f"
    fi
done

EFMT='$FileName'$'\t''${CreateDate#;DateFmt("%x %X")}'$'\t''${CreateDate#;DateFmt("%s")}'$'\t''$Creator'$'\t''${ModifyDate#;DateFmt("%x %X")}'$'\t''${ModifyDate#;DateFmt("%s")}'$'\t''$LastModifiedBy' 

now=$(date +'%s')

for k in {2..10}; do
    orgfile="../original/Module_${k}_$1.xlsx" 
    readarray -t files < list-$k
    exiftool -f -p "$EFMT" "${files[@]}" > info-$k

    IFS=$'\t' read CSTAMP CREATR OMSTAMP OMODDR <<<$(exiftool -d '%s' -p '$CreateDate'$'\t''$Creator'$'\t''$ModifyDate'$'\t''$LastModifiedBy' "$orgfile")

    while IFS=$'\t' read fn cdate cstamp creatr mdate mstamp moddr; do
        nm="${fn%%_*}"
        msg1=0
        msg2=0
        if [[ $cstamp != $CSTAMP ]]; then
    #        if ((cstamp < now-7*60*60*24)); then
                msg1=1
                cdate="$RED$cdate$DEF"
    #        fi
        fi
        if [[ $creatr != $CREATR ]]; then
    #        if [[ $creatr != $moddr ]]; then
                msg1=1
                creatr="$RED$creatr$DEF"
    #        fi
        fi
        if ((mstamp > now || mstamp < now-90*60*60*24)); then # 16 days earlier for module 7 - march 17
            msg2=1
            mdate="$RED$mdate$DEF"
        fi
        if ! grep -q "^$nm.*"$'\t'"$moddr\("$'\t'"\|$\)" ../all-modder; then
            msg2=1
            cmoddr="$RED$moddr$DEF"
        else
            cmoddr="$moddr"
        fi
        if ((msg1 + msg2)); then
            #msg="File $fn "
            if ((msg1)); then
                msg="Created on $cdate by $creatr"
                if ((msg2)); then
                    msg+=', '
                fi
            fi
            if ((msg2)); then
                if [[ $moddr == $OMODDR && $mstamp == $OMSTAMP ]] && cmp -s "$fn" "$orgfile"; then
                    msg="Unmodified"
                else
                    msg="Last modified on $mdate by $cmoddr"
                fi
            fi
            reportline "$nm" "$msg"
    fi
    done < info-$k
done

for f in *xlsx; do
    if zipinfo "$f" xl/externalLinks/externalLink1.xml >/dev/null 2>&1; then
        reportline "$f" Links to $(../wherelink.py "$f")
    fi
done

# alphabetize output up to here
echo --------------------

for instr in "${instructors[@]}"; do
    echo "$instr"
    for sec in ${backsec[$instr]}; do
        [[ -v reports[$sec] ]] && echo "${reports[$sec]}"
    done
done

echo --------------------

#exit

for fn in *xlsx
do nm="${fn%%_*}"
    if [[ ! -e $nm.csv ]]; then
#        echo "Converting $fn to $nm.csv"
       ../xlsx2csv.py "$fn" "$nm.csv"
   fi
done

if [[ ! -e simhashmatch ]] || [[ -n $(find -name '*csv' -newer simhashmatch -print -quit) ]]; then
    simhash -m *.csv > simhashmatch
fi

../clusterfy.py simhashmatch # 0.98

exit

for f in *xlsx; do
    read -srn1 -p "Open $f..."
    libreoffice "$f"
    echo
done
