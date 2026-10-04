"""Server-only configuration. Empty .env is supplied; no keys are bundled."""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'), override=False)

@dataclass(frozen=True)
class Settings:
    gemini_key: str = field(default='', repr=False)
    gemini_model: str = 'gemini-3.5-flash-lite'
    tavily_key: str = field(default='', repr=False)
    # Reserved; the current reading adapter is Gemini.
    openai_key: str = field(default='', repr=False)
    httpx_trust_env: bool = True
    allowed_origins: tuple[str, ...] = ('http://localhost:3000', 'http://127.0.0.1:3000')

    def __post_init__(self):
        if not re.fullmatch(r'gemini-[A-Za-z0-9.\-]{1,80}', self.gemini_model):
            raise ValueError('GEMINI_MODEL must be a Gemini model identifier')

    @classmethod
    def from_env(cls):
        trust_env = os.getenv('HTTPX_TRUST_ENV', 'true').strip().lower()
        if trust_env not in ('true', 'false'):
            raise ValueError('HTTPX_TRUST_ENV must be true or false')
        return cls(httpx_trust_env=trust_env == 'true', gemini_key=os.getenv('GEMINI_API_KEY', ''),
                   gemini_model=os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite'),
                   tavily_key=os.getenv('TAVILY_API_KEY', ''),
                   openai_key=os.getenv('OPENAI_API_KEY', ''),
                   allowed_origins=tuple(s.strip() for s in os.getenv(
                       'ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000'
                   ).split(',') if s.strip()))
