"""Pydantic models and conservative provider normalization."""
import math
import re
from typing import Literal
from pydantic import BaseModel, Field as PField, ConfigDict, model_validator

FIELDS = ('medicine_name', 'strength', 'form', 'dose', 'frequency', 'timing', 'duration', 'instructions')
FieldName = Literal['medicine_name', 'strength', 'form', 'dose', 'frequency', 'timing', 'duration', 'instructions']
Status = Literal['readable', 'uncertain', 'missing', 'crossed_out']

class Model(BaseModel):
    model_config = ConfigDict(extra='ignore', allow_inf_nan=False)

class Reading(Model):
    value: str | None = PField(default=None, max_length=500)
    raw: str = PField(default='', max_length=500)
    confidence: float = PField(default=0, ge=0, le=1)
    status: Status = 'missing'

class Candidate(Model):
    name: str = PField(max_length=200)
    source: str = PField(max_length=200)
    id: str | None = PField(default=None, max_length=80)
    url: str | None = PField(default=None, max_length=2000)
    manufacturer: str | None = PField(default=None, max_length=300)
    pack: str | None = PField(default=None, max_length=300)
    country: str | None = PField(default=None, max_length=50)
    review_status: Literal['unverified', 'verified_reference'] | None = None
    match_method: Literal['exact_name', 'similar_spelling'] | None = None

class Evidence(Model):
    title: str = PField(max_length=250)
    url: str = PField(max_length=2000)
    source_type: Literal['regulator', 'manufacturer', 'retailer']
    excerpt: str = PField(max_length=500)
    retrieved_at: str = PField(max_length=100)

class Verification(Model):
    verified: bool
    reason: str = PField(max_length=500)
    source: str = PField(max_length=200)

class Medication(Model):
    id: str = PField(max_length=80)
    raw_text: str = PField(default='', max_length=2000)
    region: tuple[float, float, float, float] | None = None
    fields: dict[FieldName, Reading]
    candidates: list[Candidate] = PField(default_factory=list, max_length=8)
    catalog_status: Literal['matched', 'multiple', 'unavailable', 'unmatched'] = 'unavailable'
    verification_status: Literal['pending', 'confirmed', 'unresolved'] = 'pending'
    web_status: Literal['matched', 'unmatched', 'unavailable', 'not_configured', 'skipped', 'quota'] | None = None
    web_evidence: list[Evidence] = PField(default_factory=list, max_length=5)
    catalog_verification: Verification | None = None

    @model_validator(mode='after')
    def complete_fields(self):
        if set(self.fields) != set(FIELDS):
            raise ValueError('All prescription fields are required')
        if self.region and (not all(0 <= x <= 1 for x in self.region) or
                            self.region[2] <= self.region[0] or self.region[3] <= self.region[1]):
            raise ValueError('Invalid source region')
        return self

class Extraction(Model):
    is_prescription: bool
    patient_name: str | None = PField(default=None, max_length=200)
    doctor_name: str | None = PField(default=None, max_length=200)
    date: str | None = PField(default=None, max_length=100)
    medications: list[Medication] = PField(max_length=20)
    additional_instructions: list[Reading] = PField(default_factory=list, max_length=20)
    follow_up: Reading | None = None

    @model_validator(mode='after')
    def unique_ids(self):
        if len({m.id for m in self.medications}) != len(self.medications):
            raise ValueError('Duplicate medicine identifiers')
        return self

class Metrics(Model):
    width: int = PField(ge=1, le=30000)
    height: int = PField(ge=1, le=30000)
    brightness: float = PField(ge=0, le=255)
    sharpness: float = PField(ge=0, le=100000)

class Quality(Model):
    quality_score: float
    is_readable: bool
    blur_detected: bool
    lighting_quality: str
    perspective_issue: bool | None = None
    cropped_content: bool | None = None
    recommendation: Literal['proceed', 'retake']
    warnings: list[str]
    method: str

class Correction(Model):
    medication_id: str = PField(max_length=80)
    field: FieldName
    ai_value: str | None = PField(max_length=500)
    user_value: str = PField(max_length=500)
    created_at: str = PField(max_length=100)
    source: Literal['user'] = 'user'
    confirmed: bool = False

class Issue(Model):
    medication_id: str
    field: FieldName
    message: str

class Trace(Model):
    tool: str
    duration_ms: int
    status: str

class Result(Extraction):
    prescription_id: str = PField(max_length=100)
    created_at: str = PField(max_length=100)
    mode: Literal['demo', 'live']
    quality: Quality
    issues: list[Issue] = PField(default_factory=list)
    user_corrections: list[Correction] = PField(default_factory=list, max_length=300)
    trace: list[Trace] = PField(default_factory=list)
    summary: str = ''
    source_label: str

class AnalyzeInput(Model):
    sample: Literal['easy', 'handwritten', 'difficult'] | None = None
    image: str | None = PField(default=None, max_length=4200000)
    metrics: Metrics
    allowPoor: bool = False

    @model_validator(mode='after')
    def one_source(self):
        if bool(self.sample) == bool(self.image):
            raise ValueError('Supply exactly one image or sample')
        return self

class CorrectInput(Model):
    prescription: Result
    medication_id: str = PField(max_length=80)
    values: dict[FieldName, str]
    confirm: bool

    @model_validator(mode='after')
    def bounded_changes(self):
        if any(len(v) > 500 for v in self.values.values()):
            raise ValueError('Correction too long')
        return self


def _text(value, limit=500):
    return value if isinstance(value, str) and len(value) <= limit else None


def normalize_reading(value) -> Reading:
    data = value if isinstance(value, dict) else {}
    raw, text = _text(data.get('raw')) or '', _text(data.get('value'))
    confidence = data.get('confidence', 0)
    valid = type(confidence) in (int, float) and math.isfinite(confidence) and 0 <= confidence <= 1
    confidence = float(confidence) if valid else 0
    status = data.get('status', 'missing')
    if status == 'crossed_out':
        pass
    elif text and confidence >= .85 and status == 'readable':
        status = 'readable'
    else:
        status = 'uncertain' if text or raw.strip() or status == 'uncertain' else 'missing'
    return Reading(value=text, raw=raw, confidence=confidence, status=status)


def normalize_extraction(value) -> Extraction:
    if not isinstance(value, dict) or type(value.get('is_prescription')) is not bool:
        raise ValueError('Invalid prescription document')
    meds = value.get('medications')
    if not isinstance(meds, list) or len(meds) > 20:
        raise ValueError('Invalid medication list')
    normalized = []
    for i, med in enumerate(meds):
        med = med if isinstance(med, dict) else {}
        source = med.get('fields') if isinstance(med.get('fields'), dict) else {}
        fields = {name: normalize_reading(source.get(name)) for name in FIELDS}
        strength = fields['strength']
        visible = strength.raw or strength.value or ''
        if (strength.status != 'crossed_out' and re.search(r'\b(?:mg|mcg|µg|g|ml|iu)\b|%', visible, re.I)
                and not re.search(r'\d', visible)):
            strength.value, strength.status = None, 'uncertain'
            strength.confidence = min(strength.confidence, .5)
        box = med.get('region')
        if not (isinstance(box, (list, tuple)) and len(box) == 4 and
                all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1 for x in box)
                and box[2] > box[0] and box[3] > box[1]):
            box = None
        normalized.append(Medication(id=f'm{i+1}', raw_text=_text(med.get('raw_text'), 2000) or '',
                                     region=box, fields=fields))
    return Extraction(is_prescription=value['is_prescription'],
                      patient_name=_text(value.get('patient_name'), 200),
                      doctor_name=_text(value.get('doctor_name'), 200), date=_text(value.get('date'), 100),
                      medications=normalized,
                      additional_instructions=[normalize_reading(x) for x in value.get('additional_instructions', [])[:20]]
                      if isinstance(value.get('additional_instructions'), list) else [],
                      follow_up=normalize_reading(value['follow_up']) if value.get('follow_up') is not None else None)


def effective_field(result: Result, medication: Medication, name: FieldName) -> Reading:
    for c in reversed(result.user_corrections):
        if c.medication_id == medication.id and c.field == name:
            return Reading(value=c.user_value or None, raw=medication.fields[name].raw,
                           confidence=1 if c.confirmed else 0,
                           status=('readable' if c.confirmed else 'uncertain') if c.user_value else 'missing')
    return medication.fields[name]


def export_text(result: Result) -> str:
    lines = ['AI-assisted transcription — verify against the original prescription.']
    if result.mode == 'demo':
        lines.append('DEMO SAMPLE — not a personal prescription.')
    for i, med in enumerate(result.medications):
        lines.append(f'\nMedicine {i+1} ({"user confirmed" if med.verification_status == "confirmed" else "not fully confirmed"})')
        for name in FIELDS:
            reading = effective_field(result, med, name)
            if reading.status == 'readable' and reading.value:
                lines.append(f'{name.replace("_", " ")}: {reading.value}')
    lines.append('\nUnclear and crossed-out fields are omitted. This is a transcription, not treatment advice.')
    return '\n'.join(lines)
