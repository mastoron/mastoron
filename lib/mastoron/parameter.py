import revitron

def ProcessOptions(elements, staticParams=None):
    """
    Generates a list of all shared paramters from a given set of elements.
    The output of this function is intended to be used with the CommandSwitchWindow from pyRevit forms.

    Args:
        elements (object): A list of Revit elements

    Returns:
        dict: A list of strings 
    """
    from collections import namedtuple
    ParamDef = namedtuple('ParamDef', ['name', 'type', 'isInstance'])

    paramSets = []

    for el in elements:
        typeId = el.GetTypeId()
            
        sharedParams = set()
        for param in el.ParametersMap:
            pdef = param.Definition
            sharedParams.add(ParamDef(pdef.Name, pdef.ParameterType, True))

        elType = revitron.DOC.GetElement(typeId)
        if elType:
            for param in elType.ParametersMap:
                pdef = param.Definition
                sharedParams.add(ParamDef(pdef.Name, pdef.ParameterType, False))

        paramSets.append(sharedParams)

    if paramSets:
        allSharedParams = paramSets[0]
        for paramSet in paramSets[1:]:
            allSharedParams = allSharedParams.intersection(paramSet)

        if staticParams:
            allStaticParams = set()
            for paramSet in paramSets:
                for param in paramSet:
                    if param.name in staticParams:
                        allStaticParams.add(param)
            allSharedParams = allSharedParams | allStaticParams
        
        return {'{}'.format(x.name): x for x in allSharedParams}