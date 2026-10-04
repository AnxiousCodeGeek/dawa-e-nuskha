import {ArrowUpRight,ScanLine,Sun,Focus,Maximize,Check} from 'lucide-react';
import {translations,type Language} from '../i18n/translations';

const samples=['easy','handwritten','difficult'] as const;
export default function GuidanceSection({language,onSample}:{language:Language;onSample:(id:string)=>void}){
  const t=translations[language],urdu=language==='ur';
  const tips=[{Icon:Maximize,label:t.tip1},{Icon:Sun,label:t.tip2},{Icon:ScanLine,label:t.tip3},{Icon:Focus,label:t.tip4}];
  return <section className="guidance-layout" aria-label={urdu?'تصویر کی رہنمائی اور نمونے':'Photo guidance and sample prescriptions'}>
    <aside className="photo-tips">
      <div className="tips-head"><span className="tips-icon"><ScanLine size={23}/></span><h2>{t.tips}</h2></div>
      <ul>{tips.map(({Icon,label})=><li key={label}><span><Icon size={19}/></span>{label}</li>)}</ul>
      <div className="tip-bottom"><Check size={16}/><span>{urdu?'غیر واضح ہے؟ دوبارہ تصویر لینا ٹھیک ہے۔':'Not quite clear? It’s always okay to retake.'}</span></div>
    </aside>
    <section className="demo-section" aria-labelledby="sample-heading">
      <div className="demo-heading"><div><h2 id="sample-heading">{t.sample}</h2><p>{t.sampleSub}</p></div><span className="sample-eyebrow">{t.sampleLabel}</span></div>
      <div className="demo-grid">{samples.map((id,i)=><button className={`demo-card demo-${id}`} key={id} onClick={()=>onSample(id)}>
        <div className="sample-card-top"><span className="sample-number">{urdu?'نمونہ':'SAMPLE'} 0{i+1}</span><ArrowUpRight size={19} className="sample-arrow" aria-hidden="true"/></div>
        <div className={`sample-thumb sample-${id}`}><img src={`/samples/${id}.png`} alt="" loading="lazy"/></div>
        <div className="sample-card-copy"><h3>{i===0?t.easy:i===1?t.handwritten:t.difficult}</h3><p>{urdu?['صاف متن','غیر واضح طاقت','غیر واضح دوا'][i]:['An easy first look','A few details to check','See uncertainty handled'][i]}</p></div>
      </button>)}</div>
    </section>
  </section>;
}
