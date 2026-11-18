import {FileText,FileJson2,FileSpreadsheet,FileImage,FileType2,File as FileIcon} from 'lucide-react';
export function FileGlyph({name='',mime='',large=false}:{name?:string;mime?:string;large?:boolean}){
 const extension=name.split('.').pop()?.toLowerCase();
 const Icon=mime.startsWith('image/')||['png','jpg','jpeg'].includes(extension||'')?FileImage:
 extension==='json'?FileJson2:extension==='csv'?FileSpreadsheet:extension==='pdf'?FileType2:
 extension==='txt'?FileText:FileIcon;
 return <span className={'file-icon '+(large?'large':'')} aria-hidden="true"><Icon size={large?25:19} strokeWidth={1.6}/></span>;
}
