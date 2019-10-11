
RED=$(echo -e "\e[31m")
DEF=$(echo -e "\e[39m")

declare -A stunames stusec instsec backsec grades reports
declare -a instructors

if ! [[ -e grades ]]; then
    echo "No grades" >&2
else
while IFS=$'\t' read name grade; do
    grades[$name]="$grade"
done < grades
fi

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
    if [[ -z "${stunames[$nm]:-}" ]]; then
        echo "Can't find $nm"
        echo "$nm $@"
        return
    fi
    local sect="${stusec[$nm]}"
    local instr="${instsec[$sect]}"
    local sname="${stunames[$nm]}"
    local sgrad="${grades[$sname]}"
    printf "%-20s %-4s %-26s" "$instr" "$sect" "$sname ($sgrad)"
    echo "$@"
    printf -v msg "%-4s %-26s" "$sect" "$sname ($sgrad)"
    reports[$sect]+="$msg $*"$'\n'
}
