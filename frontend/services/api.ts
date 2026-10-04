export class PrescriptionAPIError extends Error {
  constructor(public code:'sign_in_required'|'unavailable'|'invalid_response',message:string){super(message);this.name='PrescriptionAPIError';}
}
const retryMessage='We could not complete the request right now. Please try again.';
function responseError(response:Response):never {

  throw new PrescriptionAPIError('unavailable',retryMessage);
}
export async function readJSONResponse<T>(response:Response):Promise<T>{
  if(!response.headers.get('content-type')?.toLowerCase().includes('application/json'))responseError(response);
  let data:unknown;try{data=await response.json();}catch{throw new PrescriptionAPIError('invalid_response',retryMessage);}
  if(!response.ok){const message=data&&typeof data==='object'&&'error' in data&&typeof data.error==='string'?data.error:retryMessage;throw new PrescriptionAPIError('unavailable',message);}
  return data as T;
}
export async function readAnalysisResponse(response:Response,emit:(event:any)=>void):Promise<void>{
  const type=response.headers.get('content-type')?.toLowerCase()??'';
  if(!response.ok){await readJSONResponse(response);return;}
  if(!type.includes('application/x-ndjson')||!response.body)responseError(response);
  const reader=response.body.getReader();const decoder=new TextDecoder();let buffer='';let finished=false;
  const line=(s:string)=>{if(!s.trim())return;let event:any;try{event=JSON.parse(s);}catch{throw new PrescriptionAPIError('invalid_response',retryMessage);}
    if(!event||typeof event!=='object'||!['progress','quality','error','result'].includes(event.type))throw new PrescriptionAPIError('invalid_response',retryMessage);
    if(event.type==='error')throw new PrescriptionAPIError('unavailable',typeof event.message==='string'?event.message:retryMessage);
    if(event.type==='result'){if(!event.result||!Array.isArray(event.result.medications))throw new PrescriptionAPIError('invalid_response',retryMessage);finished=true;}
    emit(event);
  };
  try{while(true){const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});const lines=buffer.split('\n');buffer=lines.pop()??'';for(const value of lines)line(value);if(done){line(buffer);break;}}if(!finished)throw new PrescriptionAPIError('invalid_response',retryMessage);}finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
}
