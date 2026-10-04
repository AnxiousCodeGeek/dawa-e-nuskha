import {ImagePlus,ScanLine,BadgeCheck,ShieldCheck} from 'lucide-react';
import type {Language} from '../i18n/translations';

export default function HowItWorks({language}:{language:Language}){
  const urdu=language==='ur';
  const steps=urdu?[
    ['نسخے کی تصویر شامل کریں','تصویر اپ لوڈ کریں یا گیلری سے منتخب کریں۔ کیمرے کی اجازت ضروری نہیں۔ پورا صفحہ صاف اور اچھی روشنی میں ہونا چاہیے۔'],
    ['اصل نسخے سے موازنہ کریں','ہر دوا کے ساتھ «اصل دیکھیں» پر کلک کریں۔ آپ کو پڑھی گئی تحریر اور ممکنہ نام نظر آئیں گے۔ غیر واضح معلومات کی نشاندہی کی جاتی ہے۔'],
    ['معلومات کی تصدیق کریں','غیر واضح لکھائی کے بارے میں ڈاکٹر یا فارماسسٹ سے پوچھیں۔ صرف جانچی ہوئی معلومات کی تصدیق کریں، پھر اپنی نقل محفوظ کریں۔']
  ]:[
    ['Add your prescription','Upload a photo or choose one from your gallery. Camera access is optional. Keep the whole page in view, with good lighting and clear focus.'],
    ['Compare with the original','Choose View source on a medicine to see the reading and possible matches. Unclear information stays marked for your review.'],
    ['Check, then keep your copy','Ask your doctor or pharmacist about unclear writing. Confirm only details you have checked, then save or export your transcription.']
  ];
  const icons=[ImagePlus,ScanLine,BadgeCheck];
  return <div className="how-guide"><ol>{steps.map(([title,description],index)=>{const Icon=icons[index];return <li key={title} className={`guide-step guide-step-${index+1}`}><div className="guide-icon"><Icon size={24} aria-hidden="true"/></div><div><span className="guide-number">{urdu?'مرحلہ':'STEP'} {index+1}</span><h3>{title}</h3><p>{description}</p></div></li>;})}</ol><div className="guide-safety"><ShieldCheck size={20} aria-hidden="true"/><p>{urdu?'یہ سہولت نسخہ پڑھنے میں مدد کرتی ہے۔ غیر واضح نام یا خوراک کی تصدیق ڈاکٹر یا فارماسسٹ سے کروائیں۔':'A reading aid, with you in control. Verify unclear medicine names and doses with your doctor or pharmacist.'}</p></div></div>;
}
