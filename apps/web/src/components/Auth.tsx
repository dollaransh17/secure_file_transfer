import {useState} from 'react';
import {useForm} from 'react-hook-form';
import {zodResolver} from '@hookform/resolvers/zod';
import {ArrowUpRight,Eye,EyeOff,Files,GitBranch,ShieldCheck} from 'lucide-react';
import {authSchema,type AuthValues} from '../auth-schema';
import {api,setCsrf} from '../api';

export function Auth({onLogin}:{onLogin:(user:any)=>void}){
 const [register,setRegister]=useState(false);
 const [error,setError]=useState('');
 const [showPassword,setShowPassword]=useState(false);
 const form=useForm<AuthValues>({resolver:zodResolver(authSchema)});
 const emailError=form.formState.errors.email;
 const passwordError=form.formState.errors.password;
 return <div className="auth">
  <header className="auth-masthead">
   <a className="auth-brand" href="/" aria-label="Prooflane home"><span className="brand-mark"><ShieldCheck size={27}/></span>prooflane</a>
   <span className="auth-masthead-note"><ShieldCheck size={15}/>Private by default</span>
  </header>
  <main className="auth-layout">
   <section className="auth-story" aria-labelledby="auth-story-title">
    <div className="eyebrow">FILE HANDLING. WITH EVIDENCE.</div>
    <h2 id="auth-story-title">Your private<br/>file workspace<span className="period">.</span></h2>
    <p className="auth-intro">Upload a file, track each version, and inspect the evidence behind every release.</p>
    <div className="auth-principles">
     <div><span className="principle-icon"><Files size={21}/></span><div><h3>Every version accounted for</h3><p>Keep replacements and their verification records together.</p></div></div>
     <div><span className="principle-icon"><ShieldCheck size={21}/></span><div><h3>Evidence before access</h3><p>Downloads check current permission and exact-version evidence.</p></div></div>
     <div><span className="principle-icon"><GitBranch size={21}/></span><div><h3>A history you can inspect</h3><p>Review scans, access changes, and verification jobs.</p></div></div>
    </div>
    <div className="auth-story-foot"><span className="proof-dot"/>Files stay private until you choose to share.</div>
   </section>
   <section className="auth-card" aria-labelledby="auth-title">
    <div className="auth-card-top"><span>{register?'NEW WORKSPACE':'WORKSPACE ACCESS'}</span><ShieldCheck size={20}/></div>
    <form noValidate onSubmit={form.handleSubmit(async values=>{
     setError('');
     try{
      const result=await api('/auth/'+(register?'register':'login'),{method:'POST',body:JSON.stringify(values)});
      setCsrf(result.csrf);onLogin(result.user);
     }catch(caught){setError((caught as Error).message);}
    })}>
     <h1 id="auth-title">{register?'Create your workspace':'Welcome back'}</h1>
     <p className="auth-form-description">{register?'Set up your private file workspace.':'Sign in to your secure file workspace.'}</p>
     <div className="auth-field">
      <label htmlFor="auth-email">Email address <span className="required-mark" aria-hidden="true">*</span></label>
      <input id="auth-email" aria-label="Email address" aria-required="true" aria-invalid={!!emailError} aria-describedby={emailError?'auth-email-error':undefined} autoComplete="email" type="email" placeholder="you@example.com" {...form.register('email')}/>
      {emailError&&<p id="auth-email-error" className="field-error" role="alert">{form.getValues('email')?'Enter a valid email address':'Email address is required'}</p>}
     </div>
     <div className="auth-field">
      <label htmlFor="auth-password">Password <span className="required-mark" aria-hidden="true">*</span></label>
      <div className="password-control">
       <input id="auth-password" aria-label="Password" aria-required="true" aria-invalid={!!passwordError} aria-describedby={passwordError?'auth-password-error':register?'auth-password-hint':undefined} autoComplete={register?'new-password':'current-password'} type={showPassword?'text':'password'} placeholder={register?'Choose a strong password':'Enter your password'} {...form.register('password')}/>
       <button type="button" className="password-toggle" aria-label={showPassword?'Hide password':'Show password'} aria-controls="auth-password" aria-pressed={showPassword} onClick={()=>setShowPassword(value=>!value)}>{showPassword?<EyeOff size={19}/>:<Eye size={19}/>}</button>
      </div>
      {passwordError?<p id="auth-password-error" className="field-error" role="alert">{form.getValues('password')?passwordError.message:'Password is required'}</p>:register&&<p className="field-hint" id="auth-password-hint">Use 12–128 characters.</p>}
     </div>
     {error&&<div role="alert" className="error auth-server-error">{error}</div>}
     <button className="primary full auth-submit" disabled={form.formState.isSubmitting} aria-busy={form.formState.isSubmitting}>{form.formState.isSubmitting?'Connecting…':register?'Create workspace':'Sign in'}<ArrowUpRight size={19}/></button>
     <div className="auth-divider"/>
     <button className="text-button auth-switch" type="button" onClick={()=>{setRegister(value=>!value);setError('');form.clearErrors();}}>{register?'Already have an account? Sign in':'New to Prooflane? Create a workspace'}<ArrowUpRight size={15}/></button>
    </form>
   </section>
  </main>
  <footer className="auth-footer"><span>Prooflane</span><span>Private files. Version-bound verification.</span></footer>
 </div>;
}
