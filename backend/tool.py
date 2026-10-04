"""A real @tool decorator: registers Python functions and provider schemas.

The LLM can pass only session='current'; uploaded documents and keys stay in
server-side context. No arbitrary Python, URLs or tool arguments are executed.
"""
import inspect
from functools import wraps

REGISTRY = {}


def tool(*, requires=()):
    def decorate(function):
        if function.__name__ in REGISTRY:
            raise ValueError('Duplicate tool name')
        @wraps(function)
        async def wrapped(context, *, session='current'):
            if session != 'current':
                raise ValueError('Invalid session')
            result = function(context)
            return await result if inspect.isawaitable(result) else result
        wrapped.requires = tuple(requires)
        wrapped.declaration = {
            'name': function.__name__, 'description': (inspect.getdoc(function) or function.__name__) + (' Prerequisites: ' + ', '.join(requires) + '.' if requires else ''),
            'parameters': {'type': 'OBJECT', 'properties': {'session': {
                'type': 'STRING', 'enum': ['current'], 'description': 'Current prescription session'}},
                'required': ['session']}}
        REGISTRY[function.__name__] = wrapped
        return wrapped
    return decorate
