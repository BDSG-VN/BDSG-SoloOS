import { t as uiText, localeTag } from "../i18n/runtime.js";
import React, {useEffect, useState} from 'react';
import {useUnsaved} from './use_unsaved.js';
const h=React.createElement;
export default function Profile({api,post,onUpdate,onLogout,onDirtyChange}) {
 const [profile,setProfile]=useState(null),[saved,setSaved]=useState(''),[error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false);
 const [current,setCurrent]=useState(''),[password,setPassword]=useState(''),[confirm,setConfirm]=useState('');
 useEffect(()=>{api('/profile').then(p=>{setProfile(p);setSaved(JSON.stringify(p));}).catch(e=>setError(e.message));},[]);
 useUnsaved(Boolean(profile && JSON.stringify(profile)!==saved)||Boolean(current||password||confirm),onDirtyChange);
 async function run(fn){setBusy(true);setError('');setNotice('');try{await fn();}catch(e){setError(e.message);}finally{setBusy(false);}}
 function field(label,name,type='text'){return h('label',null,label,h('input',{type,value:profile[name],maxLength:name==='bio'?1000:name==='email'?254:120,onChange:e=>setProfile({...profile,[name]:e.target.value}),required:name==='display_name'}));}
 return h('section',{className:'panel',style:{padding:24,maxWidth:800}},
 error&&h('p',{role:'alert',className:'error'},error),notice&&h('p',{role:'status'},notice),
 profile&&h(React.Fragment,null,
 h('h2',null,uiText("Thông tin cá nhân")),h('p',null,uiText("Tên đăng nhập: {0}", [profile.username])),
 h('form',{onSubmit:e=>{e.preventDefault();run(async()=>{const {username,...body}=profile;const next=await post('/profile',body,'PUT');setProfile(next);setSaved(JSON.stringify(next));onUpdate(next);setNotice(uiText("Đã lưu thông tin tài khoản."));});}},
 h('fieldset',{disabled:busy},field(uiText("Tên hiển thị"),'display_name'),field(uiText("Email liên hệ"),'email','email'),field(uiText("Giới thiệu"),'bio'),h('p',{className:'muted'},uiText("Email dùng để liên hệ; chưa dùng để khôi phục mật khẩu.")),h('button',{className:'primary'},uiText("Lưu thông tin")))),
 h('h2',null,uiText("Đổi mật khẩu")),h('p',null,uiText("Tối thiểu 12 ký tự. Sau khi đổi, các phiên đăng nhập quản trị trên web sẽ đăng xuất.")),
 h('form',{onSubmit:e=>{e.preventDefault();if(password!==confirm){setError(uiText("Mật khẩu xác nhận không khớp."));return;}run(async()=>{await post('/profile/password',{current_password:current,new_password:password});setCurrent('');setPassword('');setConfirm('');onDirtyChange(false);onLogout();});}},h('fieldset',{disabled:busy},
 ...[[uiText("Mật khẩu hiện tại"),current,setCurrent,'current-password'],[uiText("Mật khẩu mới"),password,setPassword,'new-password'],[uiText("Nhập lại mật khẩu mới"),confirm,setConfirm,'new-password']].map(([label,value,set,auto])=>h('label',{key:label},label,h('input',{type:'password',value,autoComplete:auto,required:true,minLength:auto==='new-password'?12:1,maxLength:128,onChange:e=>set(e.target.value)}))),h('button',null,uiText("Đổi mật khẩu và đăng xuất"))))));
}
