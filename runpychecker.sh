#!/bin/bash

pychecker --only --limit 1000 \
	--maxlines 500 --maxargs 20 --maxbranches 80 --maxlocals 60 --maxreturns 20 \
	--no-callinit --no-local --no-shadow --no-shadowbuiltin \
	--no-import --no-miximport --no-pkgimport --no-reimport \
	--no-argsused --no-varargsused --no-override \
	$(find pakfire -name "*.py" )
