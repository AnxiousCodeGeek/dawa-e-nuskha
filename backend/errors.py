"""Fixed public errors; never expose upstream payloads, keys or medical text."""
class AnalysisError(Exception):
    def __init__(self, code: str, stage: str = 'analysis', *, http_status=None, attempts=None, network_kind=None):
        super().__init__(code)
        self.code, self.stage = code, stage
        self.http_status, self.attempts, self.network_kind = http_status, attempts, network_kind

    def safe_details(self):
        allowed_stages = {'analysis', 'provider', 'agent', 'handwriting', 'quality', 'tool_selection', 'tool_arguments'}
        details = {'stage': self.stage if self.stage in allowed_stages else 'analysis'}
        if type(self.http_status) is int and 100 <= self.http_status <= 599:
            details['http_status'] = self.http_status
        if type(self.attempts) is int and 1 <= self.attempts <= 3:
            details['attempts'] = self.attempts
        if self.network_kind in {'dns', 'tls', 'proxy', 'connect', 'connect_timeout', 'read_timeout', 'timeout', 'protocol', 'connection_reset', 'transport'}:
            details['network_kind'] = self.network_kind
        return details

MESSAGES = {
    'quality_retake': 'The image may be hard to read. Retake it or choose Analyze anyway.',
    'not_prescription': 'We could not identify a prescription. Please upload a clearer photo.',
    'unreadable': 'The handwriting could not be read reliably. Please check with your doctor or pharmacist.',
    'provider_unavailable': 'Configure GEMINI_API_KEY in backend/.env and restart the Python backend to read personal images.',
    'provider_quota': 'Gemini has reached its available quota. Please check quota and billing before retrying.',
    'provider_access': 'Gemini rejected the connection. Check the server API key and model access.',
    'provider_model': 'The selected Gemini model is unavailable. Check GEMINI_MODEL in backend/.env.',
    'provider_timeout': 'The reading service took too long to respond. Please try again.',
    'provider_network': 'The Python backend could not connect to Gemini. Check its internet connection, DNS, firewall or proxy, then run the connection check in the README.',
    'provider_tls': 'The Gemini connection failed its security certificate check. Check the backend’s trusted certificates or network inspection settings. Run the connection check in the README.',
    'provider_proxy': 'The backend’s configured proxy could not reach Gemini. Check proxy environment settings. Run the connection check in the README.',
    'provider_busy': 'The reading service is temporarily busy. Please try again shortly.',
    'provider_request': 'The reading service could not accept this request. Please check the server configuration.',
    'invalid_extraction': 'The reading service returned an incomplete transcription. Please try again. No uncertain reading has been filled in.',
    'agent_failure': 'The reading service could not complete its processing steps. Please try again.',
    'agent_incomplete': 'The reading service could not complete its processing steps. Please try again.',
}

def error_event(error: Exception) -> dict:
    code = error.code if isinstance(error, AnalysisError) else 'tool_failure'
    return {'type': 'error', 'code': code, 'message': MESSAGES.get(
        code, 'We could not complete the analysis right now. Please try again.')}
