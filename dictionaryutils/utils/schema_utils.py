from math import isnan
def sortdictionary(dic):
    """Returns a dictionary sorted on keys"""

    keys = sorted(dic)
    sorteddict = {}
    for k in keys:
        sorteddict[k] = dic[k]
    return sorteddict

def stripper(string):
    
    if isinstance(string, str):
        string = string.strip()
        string = string.strip('|"\',')
    elif isinstance(string, float):
        if isnan(string):       
            return None
    return string