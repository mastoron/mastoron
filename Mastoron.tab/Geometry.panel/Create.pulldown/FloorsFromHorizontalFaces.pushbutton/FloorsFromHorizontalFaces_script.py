import sys
import mastoron
import revitron
from pyrevit import forms
from revitron import _

selection = revitron.Selection().get()
if len(selection) < 1:
    sys.exit()

selected_option, switches = \
    forms.CommandSwitchWindow.show(
        ['Top Faces', 'Bottom Faces'],
        switches={
            'Delete Input Geometry': False,
            'Offset Boundary': False,
            'Offset Holes': True,
            'Transfer Parameter Values': False
        },
        message='Select Option:',
        recognize_access_key=True
        )

deleteInput = switches['Delete Input Geometry']
offset = switches['Offset Boundary']
transfer = switches['Transfer Parameter Values']
offsetHoles = switches['Offset Holes']

offsetDistance = 0.0
if offset:
    while True:
        userInput = forms.ask_for_string(
            default='0.0',
            prompt='Enter offset distance:',
            title='Floors from faces')

        try:
            offsetDistance = float(userInput)
            break
        except:
            forms.alert('Invalid input. Use number or integer')
            continue

transferParams = []
if transfer:
    allParams = set()
    for element in selection:
        for param in element.ParametersMap:
            allParams.add(param.Definition.Name)

    transferParams = forms.SelectFromList.show(sorted(allParams),
        button_name='Select Item',
        title='Select Parameters to transfer:',
        multiselect=True)

floorType = revitron.Filter().byCategory('Floors').onlyTypes().getElementIds()[0]
levels = revitron.Filter().byCategory('Levels').noTypes().getElements()
doc = revitron.DOC

floors = []
with revitron.Transaction():
    for element in selection:
        floorCreator =  mastoron.FloorCreator(
                                            levels,
                                            element,
                                            floorType,
                                            offsetDistance,
                                            offsetHoles
                                            )
        elementFloors = None
        if selected_option == 'Top Faces':
            elementFloors = floorCreator.fromTopFaces()
        if selected_option == 'Bottom Faces':
            elementFloors = floorCreator.fromBottomFaces()
        if deleteInput:
            transferData = {}
            for param in transferParams:
                transfervalue = None
                try:
                    transfervalue = _(element).get(param)
                except:
                    pass
                transferData[param] = transfervalue

        if elementFloors:
            for floor in elementFloors:
                floors.append(floor.Id)
                if deleteInput:
                    for param, value in transferData.items():
                        if value:
                            _(floor).set(param, value)

        if deleteInput:
            _(element).delete()

revitron.Selection.set(floors)

