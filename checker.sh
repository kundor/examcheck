#!/bin/bash

CDATE='2018:07:13 03:12:05Z'
CREATR='Elizabeth L. Grulke'
STAMP=1531451525
# Tuesday October 9, 00:00 MDT

RED="\e[31m"
DEF="\e[39m"

creatorcf() {
    local tstamp=$(exiftool -d '%s' -p '$CreateDate' "$1")
    local nm=${1%%_*}
    local creator=$(exiftool -p '$Creator' "$1")
    local modder=$(exiftool -p '$LastModifiedBy' "$1")
    if ((tstamp < STAMP)) || [[ $creator != $modder ]]
    then echo '**' $1 
        awk -F'\t' '/^'$nm'\t/ {print $2 " (" $3 ")"}' ../allnames
        exiftool -Creator -CreateDate -LastModifiedBy -ModifyDate "$1"
    fi
}

creatchk() {
    local creator=$(exiftool -Creator "$1")
    creator=${creator#*: }
    if [[ $creator != $CREATR ]]
    then echo $1: Creator $creator
    fi
    local cdate=$(exiftool -CreateDate "$1")
    cdate=${cdate#*: }
    if [[ $cdate != $CDATE ]]
    then echo $1: Create Date $cdate
    fi
}

modchk() {
    exiftool "$1" | grep --color=never 'Modified By\|^Modify Date'
}

isregular() {
    local siz=$(stat -c%s "$1")
    local typ=$(file --brief "$1")
    local nm=${1%%_*}
    if ((siz<500)) && [[ $typ == "data" && $1 == *\~\$* ]]
    then echo "Temp file: $1"
         awk -F'\t' '/^'$nm'\t/ {print $2 " (" $3 ")"}' ../allnames
         return 1
    elif [[ $typ == "data" && $1 == *\~\$* ]]
    then echo "Big temp file? $1"
         return 1
    elif ((siz<500)) && [[ $typ == "data" ]]
    then echo "Misnamed temp file? $1"
         return 1
    elif ((siz<500)) && [[ $1 == *\~\$* ]]
    then echo "Temp file?? $1"
         return 1
    elif ((siz<500))
    then echo "Tiny file: $1"
         return 1
    elif [[ $typ == "data" ]]
    then echo "Not an Excel file? $1"
         return 1
    elif [[ $1 == *\~\$* ]]
    then echo "Bad name, but apparently okay: $1"
         return 0
    else
         return 0
    fi
}

sectionchk() {
    while IFS=$'\t' read last first
    do  echo $first $last
        nam="${last,,}${first,,}"
        nam=${nam// /}
        fn=("$nam"*)
        if [[ ${#fn[@]} -ne 1 ]]
        then echo '**' ${#fn[@]} files
             fn=${fn[-1]}
        fi
        [[ -e "$fn" ]] || { echo '**' No file; continue; }
        if isregular "$fn"
        then creatchk "$fn"
             modchk "$fn"
        fi
    done < $1
}

checkall() {
    for f in *xlsx
    do isregular "$f" || rm "$f"
    done
    exiftool -p '$CreateDate'$'\t''$Creator'$'\t''$FileName' *xlsx | grep -v "^$CDATE"$'\t'"$CREATR" | while IFS=$'\t' read cdate creatr fn
    do nm="${fn%%_*}"
       awk -F'\t' '/^'$nm'\t/ {print $2 " (" $3 ")"}' ../allnames
       echo -e "     File $fn created on $RED$cdate$DEF by $RED$creatr$DEF"
   done
}

hasher() {
    for f in *xlsx
    do  md=$(../xlsx2csv.py "$f" 2>/dev/null | md5sum)
        echo ${md% -} "$f"
    done > hash
    for md in $(cut -d' ' -f1 hash | sort | uniq -d)
    do  grep $md hash | while read sum fn
        do  nm=${fn%%_*}
            printf "%s %s\t" $sum "$fn"
            awk -F'\t' '/^'$nm'\t/ {print $2 " (" $3 ")"}' ../allnames
        done
        echo ------------
    done
}
