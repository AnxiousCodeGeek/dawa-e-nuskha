import type {Field} from '../shared/schema';

export function displayReading(field:Field,language:'en'|'ur'){
  if(field.status==='crossed_out')return language==='ur'?'ممکنہ طور پر کاٹا گیا':'Possibly crossed out';
  if(field.status==='missing'&&!field.raw.trim())return language==='ur'?'لکھا نہیں گیا':'Not written';
  if(field.status==='uncertain'||field.status==='missing')return field.value
    ?`${field.value} — ${language==='ur'?'تصدیق کریں':'please verify'}`
    :language==='ur'?'واضح طور پر پڑھا نہیں جا سکا':'Not clearly readable';
  return field.value??(language==='ur'?'واضح طور پر پڑھا نہیں جا سکا':'Not clearly readable');
}

export function combinedDoseFrequency(dose:Field,frequency:Field,language:'en'|'ur'){
  if(dose.status==='missing'&&frequency.status==='missing')return displayReading(frequency,language);
  const parts=[];
  if(dose.status!=='missing')parts.push(displayReading(dose,language));
  if(frequency.status!=='missing')parts.push(displayReading(frequency,language));
  else parts.push(language==='ur'?'کتنی بار: لکھا نہیں گیا':'Frequency: not written');
  return parts.join(' · ');
}
