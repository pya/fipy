#!/usr/bin/env python

## -*-Pyth-*-
 # ###################################################################
 #  PyFiVol - Python-based finite volume PDE solver
 # 
 #  FILE: "modCellGradVariable.py"
 #                                    created: 12/18/03 {2:28:00 PM} 
 #                                last update: 2/20/04 {2:20:18 PM} 
 #  Author: Jonathan Guyer
 #  E-mail: guyer@nist.gov
 #  Author: Daniel Wheeler
 #  E-mail: daniel.wheeler@nist.gov
 #    mail: NIST
 #     www: http://ctcms.nist.gov
 #  
 # ========================================================================
 # This software was developed at the National Institute of Standards
 # and Technology by employees of the Federal Government in the course
 # of their official duties.  Pursuant to title 17 Section 105 of the
 # United States Code this software is not subject to copyright
 # protection and is in the public domain.  PFM is an experimental
 # system.  NIST assumes no responsibility whatsoever for its use by
 # other parties, and makes no guarantees, expressed or implied, about
 # its quality, reliability, or any other characteristic.  We would
 # appreciate acknowledgement if the software is used.
 # 
 # This software can be redistributed and/or modified freely
 # provided that any derivative works bear some notice that they are
 # derived from it, and any modified versions bear some notice that
 # they have been modified.
 # ========================================================================
 #  See the file "license.terms" for information on usage and  redistribution
 #  of this file, and for a DISCLAIMER OF ALL WARRANTIES.
 #  
 # ###################################################################
 ##
 
import Numeric

from fipy.variables.cellGradVariable import CellGradVariable
from fipy.tools.inline import inline
import fipy.tools.array

class ModCellGradVariable(CellGradVariable):
    def __init__(self, var, modIn, modPy):
        CellGradVariable.__init__(self, var)
        self.modIn = modIn
        self.modPy = modPy
        
    def _calcValueIn(self, N, M, ids, orientations, volumes):
        
	inline.runInlineLoop2(self.modIn + """
	    val(i,j) = 0.;
	    
	    int k;
            
	    for (k = 0; k < nk; k++) {
		val(i, j) += orientations(i, k) * areaProj(ids(i, k), j) * faceValues(ids(i, k));
	    }
		
	    val(i, j) /= volumes(i);
            val(i, j) = mod(val(i,j) * gridSpacing(j)) /  gridSpacing(j);
	""",
	val = self.value.value,
        ids = fipy.tools.array.convertNumeric(ids),
        orientations = fipy.tools.array.convertNumeric(orientations),
        volumes = fipy.tools.array.convertNumeric(volumes),
        areaProj = fipy.tools.array.convertNumeric(self.mesh.getAreaProjections()),
        faceValues = fipy.tools.array.convertNumeric(self.var.getArithmeticFaceValue()),
	ni = N, nj = self.mesh.getDim(), nk = M,
        gridSpacing = fipy.tools.array.convertNumeric(self.mesh.getMeshSpacing()))

    def _calcValuePy(self, N, M, ids, orientations, volumes):
        CellGradVariable._calcValuePy(self, N, M, ids, orientations, volumes)
        gridSpacing = self.mesh.getMeshSpacing()
        self.value = self.modPy(self.value * gridSpacing) / gridSpacing 
