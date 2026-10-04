import {Camera,LockKeyhole,BookOpen} from 'lucide-react';
import type {ReactNode} from 'react';
import type {Language} from '../i18n/translations';

export default function PrescriptionHero({language,onSample,children}:{language:Language;onSample:()=>void;children:ReactNode}){
  const urdu=language==='ur';
  return <section className="prescription-hero" aria-labelledby="prescription-hero-title"><div className="hero-copy"><div className="hero-kicker"><span/>{urdu?'پڑھیں۔ جانچیں۔ سمجھیں۔':'READ. REVIEW. UNDERSTAND.'}</div><h1 id="prescription-hero-title">{urdu?'اپنا نسخہ سمجھیں':<>A clearer view of<br/><span>your prescription.</span></>}</h1><p className="hero-description">{urdu?'نسخے کی تصویر دیں اور پڑھی گئی معلومات کا اصل نسخے سے موازنہ کریں۔ غیر واضح تحریر کی تصدیق آپ کے اختیار میں ہے۔':'Turn difficult handwriting into a reading you can review. Upload a photo, then check each entry beside the original.'}</p><div className="hero-reassurance"><span><Camera size={17}/>{urdu?'کیمرہ اختیاری ہے':'Camera optional'}</span><span><LockKeyhole size={17}/>{urdu?'خودکار طور پر محفوظ نہیں':'Never saved automatically'}</span></div><button className="hero-demo" onClick={onSample}><BookOpen size={18}/>{urdu?'پہلے ایک نمونہ آزمائیں':'Try a sample first'}</button></div><div className="hero-upload">{children}</div></section>;
}
