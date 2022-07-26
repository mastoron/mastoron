import mastoron
import revitron
import Autodesk.Revit.Creation as Creation
from revitron import _
from mastoron.variables import *
from System.Collections.Generic import List


class Creator(object):
    """
    Base class for creating Revit elements.
    """
    def __init__(self, docLevels, element, elementType):
        """
        Inits a new Creator instance.

        Args:
            docLevels (object): A list of Revit levels
            element (object): A Revit element
            elementType (object): A Revit element type
        """
        self.docLevels = docLevels
        self.element = element
        self.elementType = elementType


class FloorCreator(Creator):
    """
    Inits a new FloorCreator instance.
    """
    def __init__(self, docLevels, element, floorType, loopOffset=0.0, offsetHoles=True):
        super(FloorCreator, self).__init__(docLevels, element, floorType)
        self.loopOffset = loopOffset
        self.offsetHoles = offsetHoles
    
    def fromBottomFaces(self):
        """
        Creates Revit floor objects from all downward facing faces of given element.

        Returns:
            object: A list of Revit floors
        """
        faces = mastoron.FaceExtractor(self.element).getBottomFaces()
        self.level = mastoron.Level.getLevel(
                                            self.element,
                                            self.docLevels,
                                            min=True
                                            )
        levelElevation = self.level.Elevation
        uv = revitron.DB.UV(0.5, 0.5)
        floors = []
        for face in faces:
            faceZ = face.Evaluate(uv).Z
            self.offset = faceZ - levelElevation
            self.curveLoops = mastoron.BorderExtractor(face).getBorder()
            floor = self._create()
            if floor:
                floors.append(floor)

        return floors

    def fromFamilyModelLines(self, subcategory):
        """
        Create a Revit floor object from model lines of a subcategory for given element.

        Args:
            subcategory (string): The name of a subcategory

        Returns:
            object: A Revit floor
        """
        self.curveLoop = mastoron.LineExtractor(self.element).bySubcategory(subcategory)
        self.level = mastoron.Level.getLevel(
                                            self.element,
                                            self.docLevels,
                                            min=True
                                            )
        levelElevation = self.level.Elevation
        if not self.curveLoop:
            return None
        if self.curveLoop.HasPlane:
            loopZ = self.curveLoop.GetPlane().Origin.Z
        else:
            print('Cannot create floor from non-planar lines.')
        self.offset = loopZ - levelElevation
        floor = self._create()
        if floor:
            return floor
    
    def fromTopFaces(self):
        """
        Create a Revit floor object from all upward facing faces of given element.

        Args:
            offset (float, optional): The offset distance. Defaults to 0.0.

        Returns:
            object: A list of Revit floor objects
        """
        faces = mastoron.FaceExtractor(self.element).getTopFaces()
        self.level = mastoron.Level.getLevel(
                                            self.element,
                                            self.docLevels,
                                            min=False
                                            )
        levelElevation = self.level.Elevation
        uv = revitron.DB.UV(0.5, 0.5)
        floors = []
        for face in faces:
            faceZ = face.Evaluate(uv).Z
            self.offset = faceZ - levelElevation
            self.curveLoops = mastoron.BorderExtractor(face).getBorder()
            floor = self._create()
            if floor:
                floors.append(floor)

        return floors


    def _create(self):
        """
        Internal function for creating a Revit floor.

        Returns:
            object: A Revit floor
        """
        self.curveLoops = self._sanitizeLoops()
        if not self.loopOffset == 0.0:
            self.curveLoops = self._offsetLoops()
        
        try:
            floor = revitron.DB.Floor.Create(
                                        revitron.DOC,
                                        self.curveLoops,
                                        self.elementType,
                                        self.level.Id
                                        )
        except:
            print('Cannot create floor: Offset distance probably resulted in overlapping loops.')
            return None

        _(floor).set(FLOOR_OFFSET, self.offset)

        return floor

    def _offsetLoops(self):
        offsetLoops = []
        for index, curveLoop in enumerate(self.curveLoops):
            if index >= 1 and self.offsetHoles == False:
                offsetLoops.append(curveLoop)
                continue
                
            try:
                offsetLoop = revitron.DB.CurveLoop.CreateViaOffset(
                                                        curveLoop,
                                                        self.loopOffset,
                                                        revitron.DB.XYZ(0, 0, 1))
                offsetLoops.append(offsetLoop)
            except:
                print('Cannot create floor: Offset distance too large. Revit cannot handle self intersections')
        
        return offsetLoops

    def _sanitizeLoops(self):
        sanitizedLoops = []
        outerLoop = self.curveLoops[0]
        if not outerLoop.IsCounterclockwise(revitron.DB.XYZ(0,0,1)):
            outerLoop.Flip()
        sanitizedLoops.append(outerLoop)

        for curveLoop in self.curveLoops[1:]:
            if curveLoop.IsCounterclockwise(revitron.DB.XYZ(0,0,1)):
                curveLoop.Flip()
            sanitizedLoops.append(curveLoop)
        return sanitizedLoops


class RoofCreator(Creator):
    """
    Inits a new RoofCreator instance.
    """
    def __init__(self, docLevels, element, roofType):
        super(RoofCreator, self).__init__(docLevels, element, roofType)

    def fromTopFaces(self):
        """
        Creates Revit roof objects from all upward facing faces of given element.

        Returns:
            object: A list of Revit roofs
        """
        faces = mastoron.FaceExtractor(self.element).getTopFaces()
        self.level = mastoron.Level.getLevel(
                                            self.element,
                                            self.docLevels,
                                            min=False
                                            )
        levelElevation = self.level.Elevation
        uv = revitron.DB.UV(0.5, 0.5)
        roofs = []
        for face in faces:
            faceZ = face.Evaluate(uv).Z
            self.offset = faceZ - levelElevation
            self.curveLoops = mastoron.BorderExtractor(face).getBorder()
            roof = self._create()
            roofs.append(roof)
        return roofs

    def _create(self):
        """
        Internal function for creating a Revit roof.

        Returns:
            object: A Revit roof
        """
        import clr
        self.curveArray = revitron.DB.CurveArray()
        self.curveLoops = self._sanitizeLoops()
        for curve in self.curveLoops[0]:
            self.curveArray.Append(curve)
        self.elementType = revitron.DOC.GetElement(self.elementType)
        ModelCurveArray = revitron.DB.ModelCurveArray
        self.modelCurveArray = clr.StrongBox[ModelCurveArray](ModelCurveArray())
        roof = revitron.DOC.Create.NewFootPrintRoof(
                                        self.curveArray,
                                        self.level,
                                        self.elementType,
                                        self.modelCurveArray
                                        )
        _(roof).set(ROOF_OFFSET, self.offset)
        return roof

    def _offsetLoops(self):
        offsetLoops = []
        for index, curveLoop in enumerate(self.curveLoops):
            if index >= 1 and self.offsetHoles == False:
                offsetLoops.append(curveLoop)
                continue
                
            try:
                offsetLoop = revitron.DB.CurveLoop.CreateViaOffset(
                                                        curveLoop,
                                                        self.loopOffset,
                                                        revitron.DB.XYZ(0, 0, 1))
                offsetLoops.append(offsetLoop)
            except:
                print('Cannot create floor: Offset distance too large. Revit cannot handle self intersections')
        
        return offsetLoops

    def _sanitizeLoops(self):
        sanitizedLoops = []
        outerLoop = self.curveLoops[0]
        if not outerLoop.IsCounterclockwise(revitron.DB.XYZ(0,0,1)):
            outerLoop.Flip()
        sanitizedLoops.append(outerLoop)

        for curveLoop in self.curveLoops[1:]:
            if curveLoop.IsCounterclockwise(revitron.DB.XYZ(0,0,1)):
                curveLoop.Flip()
            sanitizedLoops.append(curveLoop)
        return sanitizedLoops


class WallCreator(Creator):
    """
    Inits a new WallCreator instance.
    """
    def __init__(self, docLevels, element, wallType):
        super(WallCreator, self).__init__(docLevels, element, wallType)

    def fromVerticalFaces(self):
        """
        Creates Revit wall objects from all vertical faces of given element.

        Returns:
            object: A list of Revit walls
        """
        faces = mastoron.FaceExtractor(self.element).getVeticalFaces()
        self.level = mastoron.Level.getLevel(
                                            self.element,
                                            self.docLevels,
                                            min=True
                                            )
        levelElevation = self.level.Elevation
        walls = []
        for face in faces:
            self.baseCurve = mastoron.BorderExtractor(face).getLowestEdge()
            self.topCurve = mastoron.BorderExtractor(face).getHighestEdge()
            faceMin = self.baseCurve.GetEndPoint(0)[2]
            if not round(faceMin, 5) == round(self.baseCurve.GetEndPoint(1)[2], 5):
                continue
            faceMax = self.topCurve.GetEndPoint(0)[2]
            offset = faceMin - levelElevation
            height = faceMax - faceMin
            wall = revitron.DB.Wall.Create(
                                        revitron.DOC,
                                        self.baseCurve,
                                        self.elementType,
                                        self.level.Id,
                                        height,
                                        offset,
                                        True,
                                        False
                                        )
            walls.append(wall)

        return walls


class RailingCreator(Creator):
    """
    Inits a new RailingCreator instance.
    """
    def __init__(self, docLevels, element, railingType):
        super(RailingCreator, self).__init__(docLevels, element, railingType)

    def fromTopFaces(self, includeInnerLoops):
        """
        Creates a Revit railing objects from the boundaries of all upward facing faces of given element.

        Returns:
            object: A list of Revit railings
        """
        faces = mastoron.FaceExtractor(self.element).getTopFaces()
        self.level = mastoron.Level.getLevel(
                                            self.element,
                                            self.docLevels,
                                            min=False
                                            )
        levelElevation = self.level.Elevation
        uv = revitron.DB.UV(0.5, 0.5)
        railings = []
        for face in faces:
            faceZ = face.Evaluate(uv).Z
            self.offset = faceZ - levelElevation
            curveLoops = mastoron.BorderExtractor(face).getBorder()
            innerLoops = []
            for curveLoop in curveLoops:
                if curveLoop.IsCounterclockwise(revitron.DB.XYZ(0,0,1)):
                    outerLoop = curveLoop
                else:
                    innerLoops.append(curveLoop)
                    
            railing = revitron.DB.Architecture.Railing.Create(
                                            document=revitron.DOC,
                                            curveLoop=outerLoop,
                                            railingTypeId=self.elementType,
                                            baseLevelId=self.level.Id
                                            )
            if railing:
                _(railing).set(BASE_OFFSET, self.offset)
                railings.append(railing)

            if includeInnerLoops:
                for loop in innerLoops:
                    railing = revitron.DB.Architecture.Railing.Create(
                                                    document=revitron.DOC,
                                                    curveLoop=loop,
                                                    railingTypeId=self.elementType,
                                                    baseLevelId=self.level.Id
                                                    )
                    if railing:
                        _(railing).set(BASE_OFFSET, self.offset)
                        railings.append(railing)
        return railings