# sourced from newcheck.sh, and also allows interactive reportline

RED=$(echo -e "\e[31m")
DEF=$(echo -e "\e[39m")

declare -A stunames stusec instsec backsec grades reports
declare -a instructors

if ! [[ -e grades ]]; then
    echo "No grades" >&2
else
while IFS=$'\t' read sid grade; do
    grades[$sid]="$grade"
done < grades
fi

while IFS=$'\t' read sid name sec; do
    stunames[$sid]="$name"
    stusec[$sid]="$sec"
done < ../allnames


while IFS=$'\t' read name secs; do
    instructors+=( "$name" )
    backsec[$name]="$secs"
    for sec in $secs; do
        instsec[$sec]="$name" 
    done
done < ../instructor-sections

namesid() {
    local fn="$1"
    curname="${fn%%_*}"
    fn="${fn#*_}"
    curid="${fn%%_*}"
}

reportline() {
    namesid "$1"
    shift
    if [[ -z "${stunames[$curid]:-}" ]]; then
        echo "Can't find $curid"
        echo "$curname $@"
        return
    fi
    local sect="${stusec[$curid]}"
    local instr="${instsec[$sect]}"
    local sname="${stunames[$curid]}"
    local sgrad="${grades[$curid]}"
    printf "%-20s %-4s %-26s " "$instr" "$sect" "$sname ($sgrad)"
    echo "$@"
    printf -v msg "%-4s %-26s" "$sect" "$sname ($sgrad)"
    reports[$sect]+="$msg $*"$'\n'
}
