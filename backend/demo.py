"""Explicit synthetic samples, never a fallback for real images."""
from .model import FIELDS, normalize_extraction


def demo_extraction(sample):
    def med(name, strength, dose, frequency, timing, duration, y, uncertain=False):
        values = dict(zip(FIELDS, (name, strength, 'Tablet', dose, frequency, timing, duration, None)))
        return {'raw_text': ' · '.join(v for v in values.values() if v),
                'region': [.09, y, .91, y+.12],
                'fields': {f: {'value': value, 'raw': value or '',
                              'confidence': .52 if uncertain and f == 'medicine_name' else .97 if value else 0,
                              'status': 'uncertain' if uncertain and f == 'medicine_name' else 'readable' if value else 'missing'}
                           for f, value in values.items()}}
    panadol = med('Panadol', '500 mg', '1 tablet', 'Twice daily', None, '5 days', .35)
    cetirizine = med('Cetirizine', None if sample == 'handwritten' else '10 mg', '1 tablet', 'Once daily', 'At night', '3 days', .55)
    unclear = med('Amlo…', None, None, None, None, None, .35 if sample == 'difficult' else .75, True)
    medicines = [unclear, cetirizine] if sample == 'difficult' else [panadol, cetirizine, unclear] if sample == 'handwritten' else [panadol, cetirizine]
    return normalize_extraction({'is_prescription': True, 'patient_name': 'Sample patient',
                                 'doctor_name': 'Dr. A. Khan (fictional)', 'date': '01 Oct 2026',
                                 'medications': medicines, 'additional_instructions': [], 'follow_up': None})
