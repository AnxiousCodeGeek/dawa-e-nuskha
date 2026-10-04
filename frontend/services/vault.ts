import type {Result} from '@/shared/schema';
export type Saved={result:Result;image:string;label:string};
const keyName='scriptly-encrypted-history-v1';
const b64=(a:Uint8Array)=>btoa(String.fromCharCode(...a));
const decode=(s:string)=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function key(password:string,salt:Uint8Array){const raw=await crypto.subtle.importKey('raw',new TextEncoder().encode(password),'PBKDF2',false,['deriveKey']);return crypto.subtle.deriveKey({name:'PBKDF2',salt:salt as BufferSource,iterations:250000,hash:'SHA-256'},raw,{name:'AES-GCM',length:256},false,['encrypt','decrypt']);}
export async function loadVault(password:string):Promise<Saved[]>{const item=localStorage.getItem(keyName);if(!item)return [];const {salt,iv,data}=JSON.parse(item);const decrypted=await crypto.subtle.decrypt({name:'AES-GCM',iv:decode(iv)},await key(password,decode(salt)),decode(data));return JSON.parse(new TextDecoder().decode(decrypted));}
export async function saveVault(password:string,items:Saved[]){if(password.length<10)throw new Error('Use a passphrase of at least 10 characters.');const salt=crypto.getRandomValues(new Uint8Array(16)),iv=crypto.getRandomValues(new Uint8Array(12));const encrypted=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv},await key(password,salt),new TextEncoder().encode(JSON.stringify(items))));let binary='';for(let i=0;i<encrypted.length;i+=8192)binary+=String.fromCharCode(...encrypted.subarray(i,i+8192));localStorage.setItem(keyName,JSON.stringify({salt:b64(salt),iv:b64(iv),data:btoa(binary)}));}
export function deleteVault(){localStorage.removeItem(keyName);}

export function hasSavedHistory(){try{return !!localStorage.getItem(keyName);}catch{return false;}}
