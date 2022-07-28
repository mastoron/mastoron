import mastoron
import revitron
from revitron import _
from variables import *
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
    def __init__(self, docLevels, element, floorType):
        super(FloorCreator, self).__init__(docLevels, element, floorType)
    
    def fromBottomFaces(self):
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
            self.curveLoop = mastoron.BorderExtractor(face).getBorder()
            floor = self._create()
            floors.append(floor)
        return floors

    def fromFamilyModelLines(self, subcategory):
        self.curveLoop = mastoron.LineExtractor(self.element).bySubcategory(subcategory)
        self.level = mastoron.Level.getLevel(
                                            self.element,
                                            self.docLevels,
                                            min=True
                                            )
        levelElevation = self.level.Elevation
        if self.curveLoop.HasPlane:
            loopZ = self.curveLoop.GetPlane().Origin.Z
        else:
            print('Cannot create floor from non-planar lines.')
        self.offset = loopZ - levelElevation
        floor = self._create()
        return floor
    
    def _create(self):
        self.curveLoop = List[revitron.DB.CurveLoop]([self.curveLoop])
        floor = revitron.DB.Floor.Create(
                                        revitron.DOC,
                                        self.curveLoop,
                                        self.elementType,
                                        self.level.Id
                                        )
        _(floor).set(FLOOR_OFFSET, self.offset)
        return floor