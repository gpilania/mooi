# /bin/bash

path=../mocde/results/history/$1
name=mocde
main=$name
#functions="zdt* dtlz*"
functions="zdt1"

./src/analyze.py -R report-internal-$1 --results $path/$name-L10 $path/$name-L20 $path/$name-L50 $path/$main --functions $functions #-hl $main
