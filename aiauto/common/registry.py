REGISTRY = {}
def register(name: str):
    def deco(obj):
        REGISTRY[name] = obj
        return obj
    return deco
