"""Bounded Gemini function-calling agent using the real decorated Python registry."""
import asyncio
import json
import logging
import time
from . import tools  # Registers decorated functions once.
from .context import Context
from .errors import AnalysisError, error_event
from .model import Trace
from .providers import SAFETY_PROMPT
from .tool import REGISTRY

log = logging.getLogger('prescription.events')
TOOL_NAMES = tuple(REGISTRY)


async def run_agent(context: Context, emit):
    async def execute(name, args):
        function = REGISTRY.get(name)
        if function is None or name in context.completed:
            raise AnalysisError('agent_failure', 'tool_selection')
        if not isinstance(args, dict) or args != {'session': 'current'}:
            raise AnalysisError('agent_failure', 'tool_arguments')
        unmet = [dependency for dependency in function.requires if dependency not in context.completed]
        if unmet:
            return {'error': 'Prerequisite unmet. Call next required tool.',
                    'next_required': next(n for n in TOOL_NAMES if n not in context.completed)}
        emit({'type': 'progress', 'tool': name, 'status': 'running'})
        start = time.perf_counter()
        try:
            await function(context, **args)
        except AnalysisError as error:
            if error.code == 'quality_retake' and context.quality:
                emit({'type': 'quality', 'quality': context.quality.model_dump()})
            raise
        elapsed = round((time.perf_counter()-start)*1000)
        context.completed.add(name)
        if context.result:
            context.result.trace = [Trace(**row) for row in trace]
        trace.append({'tool': name, 'duration_ms': elapsed, 'status': 'completed'})
        log.info(json.dumps({'event': 'tool_completed', 'tool': name, 'duration_ms': elapsed}))
        emit({'type': 'progress', 'tool': name, 'status': 'completed'})
        return {'completed': True, 'next_required': next((n for n in TOOL_NAMES if n not in context.completed), None)}

    trace = []
    log.info(json.dumps({'event': 'agent_started', 'mode': 'demo' if context.input.sample else 'live'}))
    if context.input.sample:
        for name in TOOL_NAMES:
            await execute(name, {'session': 'current'})
    else:
        if not context.settings.gemini_key:
            raise AnalysisError('provider_unavailable')
        contents = [{'role': 'user', 'parts': [{'text':
            'Process the prescription using session-bound tools. The image is supplied internally. '
            'All tool results are stored in shared server session state, so downstream tools need no result arguments. '
            'When possible, request all remaining required tools in ONE response, in this prerequisite order: '
            + ', '.join(TOOL_NAMES) + '. Each function must use only session=current. '
            'The server executes calls sequentially and stops immediately if quality or extraction fails. '}]}]
        for _ in range(12):
            if len(context.completed) == len(TOOL_NAMES):
                break
            available = [n for n in TOOL_NAMES if n not in context.completed]
            response = await context.providers.gemini({
                'systemInstruction': {'parts': [{'text': SAFETY_PROMPT}]}, 'contents': contents,
                'tools': [{'functionDeclarations': [REGISTRY[n].declaration for n in available]}],
                'toolConfig': {'functionCallingConfig': {'mode': 'ANY'}},
                'generationConfig': {'temperature': 0}}, 'agent')
            try:
                content = response['candidates'][0]['content']
                calls = [p['functionCall'] for p in content['parts'] if 'functionCall' in p]
                if not calls or len(calls) > len(TOOL_NAMES):
                    raise ValueError()
            except (KeyError, IndexError, TypeError, ValueError):
                raise AnalysisError('agent_failure', 'tool_selection') from None
            # Preserve provider content (including thought signatures) exactly in the history.
            contents.append(content)
            replies = []
            for call in calls:
                if not isinstance(call, dict) or call.get('name') not in available:
                    raise AnalysisError('agent_failure', 'tool_selection')
                reply = {'name': call['name'], 'response': await execute(call['name'], call.get('args', {}))}
                if call.get('id'):
                    reply['id'] = call['id']
                replies.append({'functionResponse': reply})
            contents.append({'role': 'user', 'parts': replies})
        if len(context.completed) != len(TOOL_NAMES):
            raise AnalysisError('agent_incomplete')
    if context.result is None:
        raise AnalysisError('agent_failure')
    context.result.trace = [Trace(**row) for row in trace]
    emit({'type': 'result', 'result': context.result.model_dump(mode='json')})
    log.info(json.dumps({'event': 'analysis_completed', 'tools': len(trace)}))
    return context.result


async def stream_agent(context: Context):
    """NDJSON stream with bounded lifetime and cancellation on client disconnect."""
    queue = asyncio.Queue()
    async def worker():
        try:
            await asyncio.wait_for(run_agent(context, queue.put_nowait), timeout=180)
        except TimeoutError:
            queue.put_nowait(error_event(AnalysisError('provider_timeout')))
        except Exception as error:
            event = error_event(error)
            queue.put_nowait(event)
            log.warning(json.dumps({'event': 'analysis_failed', 'code': event['code'],
                                    **(error.safe_details() if isinstance(error, AnalysisError) else {})}))
        finally:
            queue.put_nowait(None)
    task = asyncio.create_task(worker())
    try:
        while True:
            event = await queue.get()
            if event is None:
                break
            yield json.dumps(event, ensure_ascii=False, allow_nan=False)+'\n'
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)