#!/usr/bin/env python

## -*-Pyth-*-
 # ###################################################################
 #  FiPy - a finite volume PDE solver in Python
 # 
 #  FILE: "setup.py"
 #
 #  Author: Jonathan Guyer   <guyer@nist.gov>
 #  Author: Daniel Wheeler   <daniel.wheeler@nist.gov>
 #  Author: James Warren     <jwarren@nist.gov>
 #  Author: Andrew Acquaviva <andrewa@nist.gov>
 #    mail: NIST
 #     www: http://www.ctcms.nist.gov/fipy/
 #  
 # ========================================================================
 # This document was prepared at the National Institute of Standards
 # and Technology by employees of the Federal Government in the course
 # of their official duties.  Pursuant to title 17 Section 105 of the
 # United States Code this document is not subject to copyright
 # protection and is in the public domain.  setup.py
 # is an experimental work.  NIST assumes no responsibility whatsoever
 # for its use by other parties, and makes no guarantees, expressed
 # or implied, about its quality, reliability, or any other characteristic.
 # We would appreciate acknowledgement if the document is used.
 # 
 # This document can be redistributed and/or modified freely
 # provided that any derivative works bear some notice that they are
 # derived from it, and any modified versions bear some notice that
 # they have been modified.
 # ========================================================================
 #  
 # ###################################################################
 ##

"""

The `gapFillMesh` function glues 3 meshes together to form a composite
mesh. The first mesh is a `Grid2D` object that is fine and deals with
the area around the trench or via. The second mesh is a `Gmsh2D`
object that forms a transition mesh from a fine to a course
region. The third mesh is another `Grid2D` object that forms the
boundary layer. This region consists of very large elements and is
only used for the diffusion in the boundary layer.

"""

__docformat__ = 'restructuredtext'

from fipy.meshes import Gmsh2D
from fipy.meshes import Grid2D
from fipy.tools import numerix
from fipy.tools import serial
from fipy.variables.distanceVariable import DistanceVariable
from fipy.variables.cellVariable import CellVariable

class GapFillMesh(Gmsh2D):
    """
    The following test case tests for diffusion across the domain.
    >>> domainHeight = 5.        
    >>> mesh = GapFillMesh(transitionRegionHeight = 2.,
    ...                    cellSize = 0.1,
    ...                    desiredFineRegionHeight = 1.,
    ...                    desiredDomainHeight = domainHeight,
    ...                    desiredDomainWidth = 1.) # doctest: +GMSH

    >>> import fipy.tools.dump as dump
    >>> (f, filename) = dump.write(mesh) # doctest: +GMSH
    >>> mesh = dump.read(filename, f) # doctest: +GMSH
    >>> mesh.numberOfCells # doctest: +GMSH
    173

    >>> from fipy.variables.cellVariable import CellVariable
    >>> var = CellVariable(mesh = mesh) # doctest: +GMSH

    >>> from fipy.terms.diffusionTerm import DiffusionTerm
    >>> eq = DiffusionTerm()

    >>> var.constrain(0., mesh.facesBottom) # doctest: +GMSH
    >>> var.constrain(domainHeight, mesh.facesTop) # doctest: +GMSH

    >>> eq.solve(var) # doctest: +GMSH

    Evaluate the result:

    >>> centers = mesh.cellCenters[1].copy() # doctest: +GMSH 

    .. note:: the copy makes the array contiguous for inlining

    >>> localErrors = (centers - var)**2 / centers**2 # doctest: +GMSH 
    >>> globalError = numerix.sqrt(numerix.sum(localErrors) / mesh.numberOfCells) # doctest: +GMSH 
    >>> argmax = numerix.argmax(localErrors) # doctest: +GMSH

    >>> print numerix.sqrt(localErrors[argmax]) < 0.1 # doctest: +GMSH
    1
    >>> print globalError < 0.05 # doctest: +GMSH
    1

    """
    def __init__(self,
                 cellSize=None,
                 desiredDomainWidth=None,
                 desiredDomainHeight=None,
                 desiredFineRegionHeight=None,
                 transitionRegionHeight=None):

        """
        Arguments:

        `cellSize` - The cell size in the fine grid around the trench.

        `desiredDomainWidth` - The desired domain width.

        `desiredDomainHeight` - The total desired height of the
        domain.

        `desiredFineRegionHeight` - The desired height of the in the
        fine region around the trench.

        `transitionRegionHeight` - The height of the transition region.
        """
        # Calculate the fine region cell counts.
        nx = int(desiredDomainWidth / cellSize)
        ny = int(desiredFineRegionHeight / cellSize) 

        # Calculate the actual mesh dimensions
        actualFineRegionHeight = ny * cellSize
        actualDomainWidth = nx * cellSize
        boundaryLayerHeight = desiredDomainHeight - actualFineRegionHeight - transitionRegionHeight
        numberOfBoundaryLayerCells = int(boundaryLayerHeight / actualDomainWidth)

        # Build the fine region mesh.
        self.fineMesh = Grid2D(nx=nx, ny=ny, dx=cellSize, dy=cellSize, communicator=serial)

        eps = cellSize / nx / 10

        super(GapFillMesh, self).__init__("""
        ny       = %(ny)g;
        cellSize = %(cellSize)g - %(eps)g;
        height   = %(actualFineRegionHeight)g;
        width    = %(actualDomainWidth)g;
        boundaryLayerHeight = %(boundaryLayerHeight)g;
        transitionRegionHeight = %(transitionRegionHeight)g;
        numberOfBoundaryLayerCells = %(numberOfBoundaryLayerCells)g;

        Point(1) = {0, 0, 0, cellSize};
        Point(2) = {width, 0, 0, cellSize};
        Line(3) = {1, 2};

        Point(10) = {0, height, 0, cellSize};
        Point(11) = {width, height, 0, cellSize};
        Point(12) = {0, height + transitionRegionHeight, 0, width};
        Point(13) = {width, height + transitionRegionHeight, 0, width};
        Line(14) = {10,11};
        Line(15) = {11,13};
        Line(16) = {13,12};
        Line(17) = {12,10};
        Line Loop(18) = {14, 15, 16, 17};
        Plane Surface(19) = {18};

        Extrude{0, height, 0} {
            Line{3}; Layers{ ny }; Recombine;}

        Line(100) = {12, 13};
        Extrude{0, boundaryLayerHeight, 0} {
            Line{100}; Layers{ numberOfBoundaryLayerCells }; Recombine;}
        """ % locals())

class TrenchMesh(GapFillMesh):

    """
    The following test case tests for diffusion across the domain.

    >>> cellSize = 0.05e-6
    >>> trenchDepth = 0.5e-6
    >>> boundaryLayerDepth = 50e-6
    >>> domainHeight = 10 * cellSize + trenchDepth + boundaryLayerDepth

    >>> mesh = TrenchMesh(trenchSpacing = 1e-6,
    ...                   cellSize = cellSize,
    ...                   trenchDepth = trenchDepth,
    ...                   boundaryLayerDepth = boundaryLayerDepth,
    ...                   aspectRatio = 1.) # doctest: +GMSH

    >>> import fipy.tools.dump as dump
    >>> (f, filename) = dump.write((mesh, mesh.electrolyteMask)) # doctest: +GMSH
    >>> mesh, electrolyteMask = dump.read(filename, f) # doctest: +GMSH
    >>> mesh.electrolyteMask = electrolyteMask
    >>> mesh.numberOfCells - len(numerix.nonzero(mesh.electrolyteMask)[0]) # doctest: +GMSH
    150

    >>> from fipy.variables.cellVariable import CellVariable
    >>> var = CellVariable(mesh = mesh, value = 0.) # doctest: +GMSH

    >>> from fipy.terms.diffusionTerm import DiffusionTerm
    >>> eq = DiffusionTerm() # doctest: +GMSH

    >>> var.constrain(0., mesh.facesBottom) # doctest: +GMSH
    >>> var.constrain(domainHeight, mesh.facesTop) # doctest: +GMSH

    >>> eq.solve(var) # doctest: +GMSH

    Evaluate the result:
       
    >>> centers = mesh.cellCenters[1].copy() # doctest: +GMSH

    .. note:: the copy makes the array contiguous for inlining

    >>> localErrors = (centers - var)**2 / centers**2 # doctest: +GMSH
    >>> globalError = numerix.sqrt(numerix.sum(localErrors) / mesh.numberOfCells) # doctest: +GMSH
    >>> argmax = numerix.argmax(localErrors) # doctest: +GMSH
    >>> print numerix.sqrt(localErrors[argmax]) < 0.051 # doctest: +GMSH
    1
    >>> print globalError < 0.02 # doctest: +GMSH
    1

    """

    def __init__(self,
                 trenchDepth=None,
                 trenchSpacing=None,
                 boundaryLayerDepth=None,
                 cellSize=None,
                 aspectRatio=None,
                 angle=0.):
        """

        `trenchDepth` - Depth of the trench.

        `trenchSpacing` - The distance between the trenches.

        `boundaryLayerDepth` - The depth of the hydrodynamic boundary
        layer.

        `cellSize` - The cell Size.

        `aspectRatio` - trenchDepth / trenchWidth

        `angle` - The angle for the taper of the trench.

        The trench mesh takes the parameters generally used to define
        a trench region and recasts then for the general
        `GapFillMesh`.

        """
        heightBelowTrench = cellSize * 10.

        heightAboveTrench = trenchDepth / 1.

        fineRegionHeight = heightBelowTrench + trenchDepth + heightAboveTrench
        transitionHeight = fineRegionHeight * 3.
        domainWidth = trenchSpacing / 2.
        domainHeight = heightBelowTrench + trenchDepth + boundaryLayerDepth

        super(TrenchMesh, self).__init__(cellSize=cellSize,
                                         desiredDomainWidth=domainWidth,
                                         desiredDomainHeight=domainHeight,
                                         desiredFineRegionHeight=fineRegionHeight,
                                         transitionRegionHeight=transitionHeight)

        trenchWidth = trenchDepth / aspectRatio

        x, y = self.cellCenters
        Y = (y - (heightBelowTrench + trenchDepth / 2))
        taper = numerix.tan(angle) * Y
        self.electrolyteMask = numerix.where(y > trenchDepth + heightBelowTrench,
                                             1,
                                             numerix.where(y < heightBelowTrench,
                                                           0,
                                                           numerix.where(x > trenchWidth / 2 + taper,
                                                                         0,
                                                                         1)))

class GapFillDistanceVariable(DistanceVariable):
    
    def extendVariable(self, extensionVariable, order=2):
        if not hasattr(self, 'fineDistanceVariable'):
            self.fineDistanceVariable = DistanceVariable(mesh=self.mesh.fineMesh)
        if not hasattr(self, 'fineExtensionVariable'):
            self.fineExtensionVariable = CellVariable(mesh=self.mesh.fineMesh)
        self.fineDistanceVariable[:] = self(self.mesh.fineMesh.cellCenters)
        self.fineExtensionVariable[:] = extensionVariable(self.mesh.fineMesh.cellCenters)
        self.fineDistanceVariable.extendVariable(self.fineExtensionVariable, order=order)
        extensionVariable[:] = self.fineExtensionVariable(self.mesh.cellCenters)

    def calcDistanceFunction(self, order=2):
        if not hasattr(self, 'fineDistanceVariable'):
            self.fineDistanceVariable = DistanceVariable(mesh=self.mesh.fineMesh)
        self.fineDistanceVariable[:] = self(self.mesh.fineMesh.cellCenters)
        self.fineDistanceVariable.calcDistanceFunction(order=order)
        self[:] = self.fineDistanceVariable(self.mesh.cellCenters)

def _test(): 
    import fipy.tests.doctestPlus
    return fipy.tests.doctestPlus.testmod()
    
if __name__ == "__main__": 
    _test() 

