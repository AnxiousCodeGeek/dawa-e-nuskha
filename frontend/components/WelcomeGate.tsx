'use client';
import {useEffect,useState,useCallback,useRef,type ReactNode} from 'react';
import {ShieldCheck} from 'lucide-react';
import type {Language} from '../i18n/translations';

const sessionKey='dawa-e-nuskha-welcome-v2';
export default function WelcomeGate({children,language}:{children:ReactNode;language:Language}){
  const timers=useRef<number[]>([]);
  const [visible,setVisible]=useState(true);
  const [leaving,setLeaving]=useState(false);
  const [animate,setAnimate]=useState(false);
  const finish=useCallback(()=>{
    timers.current.forEach(clearTimeout);timers.current=[];
    try{sessionStorage.setItem(sessionKey,'seen');}catch{}
    setVisible(false);
    requestAnimationFrame(()=>document.getElementById('main')?.focus({preventScroll:true}));
  },[]);
  useEffect(()=>{
    let seen=false;try{seen=sessionStorage.getItem(sessionKey)==='seen';}catch{}
    if(seen){setVisible(false);return;}
    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    setAnimate(!reduced);
    const start=window.setTimeout(()=>setLeaving(true),5100);
    const end=window.setTimeout(finish,5400);
    timers.current=[start,end];
    return()=>{timers.current.forEach(clearTimeout);timers.current=[];};
  },[finish]);
  if(!visible)return <div className="entry-ready">{children}</div>;
  const urdu=language==='ur';
  return <section className={`welcome-screen ${animate?'welcome-animated':''} ${leaving?'welcome-leaving':''}`} aria-label={urdu?'خوش آمدید':'Welcome'}>
    <div className="welcome-brand"><img src="/brand/monogram.png" alt="" width={44} height={44}/><span>Dawa-e-Nuskha</span></div>
    <div className="welcome-center"><div className="welcome-aura" aria-hidden="true"/><div className="welcome-message"><span className="welcome-kicker">{urdu?'وضاحت، احتیاط کے ساتھ':'CLARITY, WITH CARE'}</span><h1>{urdu?'خوش آمدید':'Welcome'}</h1>{!urdu&&<p className="welcome-urdu" lang="ur" dir="rtl">خوش آمدید</p>}<p className="welcome-copy">{urdu?'اپنا نسخہ پڑھیں، جانچیں اور سمجھیں':'Read your prescription. Review it. Understand it.'}</p></div></div>
    <div className="welcome-bottom"><span><ShieldCheck size={17} aria-hidden="true"/>{urdu?'آپ کی معلومات، آپ کے اختیار میں':'Your information, your control'}</span><button onClick={finish}>{urdu?'جاری رکھیں':'Continue'}<span className="sr-only">{urdu?' — نسخے کی جگہ کھولیں':' — open prescription workspace'}</span></button></div>
  </section>;
}
