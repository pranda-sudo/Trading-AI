import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.95.3/+esm";
export const supabase = createClient("https://hatzdirgwutbdarpgwro.supabase.co", "sb_publishable_FfWSpPjZSer3hnytJ1q9PA_yM6mEORu");
const gate = document.createElement("div");
gate.id = "auth-gate";
gate.innerHTML = `<div class="auth-panel"><div class="auth-mark">◈ Trading AI</div><h1>Zabezpečený přístup</h1><p id="auth-status">Ověřuji přihlášení…</p><form id="auth-form" hidden><label for="auth-email">E-mail</label><input id="auth-email" type="email" autocomplete="username" required placeholder="vas@email.cz"><label for="auth-password">Heslo</label><input id="auth-password" type="password" autocomplete="current-password" required placeholder="Vaše heslo"><button type="submit">Přihlásit se</button></form><p class="auth-foot">Přístup pouze pro schválené uživatele.</p></div>`;
document.body.prepend(gate);
const status = gate.querySelector("#auth-status"), form = gate.querySelector("#auth-form");
const showLogin = (msg) => { document.documentElement.classList.remove("auth-allowed"); form.hidden=false; status.textContent=msg||"Přihlas se ke svému účtu."; };
async function check() {
  try {
    const {data,error}=await supabase.auth.getUser();
    if(error || !data.user) {showLogin();return;}
    if(!["admin","viewer"].includes(data.user.app_metadata?.role)) {await supabase.auth.signOut();showLogin("Tento účet nemá schválený přístup.");return;}
    document.documentElement.classList.add("auth-allowed");
    gate.remove();
    window.dispatchEvent(new CustomEvent("trading-ai-auth-ready", {detail:{role:data.user.app_metadata?.role}}));
    const btn=document.createElement("button");
    btn.type="button";btn.textContent="Odhlásit se";btn.id="auth-logout";
    btn.addEventListener("click",async()=>{await supabase.auth.signOut();location.reload();});
    document.body.append(btn);
    if(data.user.app_metadata?.role==="admin"){
      const manage=document.createElement("button");
      manage.type="button";
      manage.id="auth-manage-users";
      manage.textContent="⚙ Správa uživatelů";
      manage.style.cssText="position:fixed;right:130px;top:14px;z-index:1000;padding:9px 13px;background:#1757a6;color:#fff;border:1px solid #4b9cf0;border-radius:9px;cursor:pointer";
      const panel=document.createElement("dialog");
      panel.id="auth-users-dialog";
      panel.setAttribute("aria-label","Správa uživatelů");
      panel.style.cssText="width:min(94vw,560px);max-height:85vh;overflow:auto;background:#142239;color:#eaf1fc;border:1px solid #50617c;border-radius:16px;padding:25px;box-shadow:0 25px 75px #0009";
      const heading=document.createElement("h2");
      heading.textContent="Správa uživatelů";
      const intro=document.createElement("p");
      intro.textContent="Přístup do Trading AI je řízen rolí v Supabase Auth. Pouze administrátor smí schvalovat a měnit oprávnění.";
      const current=document.createElement("p");
      current.textContent="Přihlášený administrátor: "+(data.user.email||"—");
      const help=document.createElement("p");
      help.textContent="Uživatelé se načítají přímo ze Supabase. Role viewer = přístup do aplikace, admin = správa účtů, bez přístupu = zamítnuto.";
      const feedback=document.createElement("p");feedback.setAttribute("role","status");feedback.style.color="#9fdbbf";
      const users=document.createElement("div");users.style.cssText="display:grid;gap:10px;margin:16px 0";
      const invite=document.createElement("form");invite.style.cssText="display:flex;flex-wrap:wrap;gap:8px;margin:14px 0";
      const email=document.createElement("input");email.type="email";email.placeholder="E-mail nového uživatele";email.required=true;email.style.cssText="flex:1;min-width:190px;padding:10px;background:#0c1729;color:#fff;border:1px solid #50617c;border-radius:8px";
      const inviteButton=document.createElement("button");inviteButton.type="submit";inviteButton.textContent="Odeslat pozvánku";inviteButton.style.cssText="padding:10px;background:#1757a6;color:white;border:0;border-radius:8px;cursor:pointer";
      invite.append(email,inviteButton);
      async function api(payload){
        const {data:session,error:sessionError}=await supabase.auth.getSession();
        if(sessionError||!session.session?.access_token)throw new Error("Přihlas se znovu.");
        const res=await fetch("https://hatzdirgwutbdarpgwro.supabase.co/functions/v1/trading-user-admin",{
          method:"POST",headers:{"Content-Type":"application/json","apikey":"sb_publishable_FfWSpPjZSer3hnytJ1q9PA_yM6mEORu","Authorization":"Bearer "+session.session.access_token},body:JSON.stringify(payload)
        });
        const json=await res.json();if(!res.ok)throw new Error(json.error||"Server odmítl požadavek");return json;
      }
      async function refreshUsers(){
        users.textContent="Načítám uživatele…";feedback.textContent="";
        try{
          const result=await api({action:"list"});users.replaceChildren();
          for(const u of result.users){
            const row=document.createElement("div");row.style.cssText="padding:12px;background:#202f46;border:1px solid #34465f;border-radius:10px;display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap";
            const info=document.createElement("div");info.style.cssText="min-width:0;overflow-wrap:anywhere";
            const name=document.createElement("strong");name.textContent=u.email||u.id;
            const details=document.createElement("div");details.style.cssText="font-size:12px;color:#b8cce5;margin-top:4px";details.textContent=(u.confirmed?"E-mail ověřen":"E-mail neověřen")+" · "+(u.role==="admin"?"Administrátor":u.role==="viewer"?"Uživatel":"Bez přístupu");
            info.append(name,details);
            const select=document.createElement("select");select.style.cssText="padding:9px;background:#0c1729;color:white;border:1px solid #50617c;border-radius:8px";
            for(const [value,label] of [["none","Bez přístupu"],["viewer","Uživatel"],["admin","Administrátor"]]){const opt=document.createElement("option");opt.value=value;opt.textContent=label;select.append(opt)}
            select.value=["admin","viewer"].includes(u.role)?u.role:"none";
            if(u.id===data.user.id){select.disabled=true;select.title="Vlastní roli nelze změnit"}
            select.addEventListener("change",async()=>{
              const previous=u.role==="admin"||u.role==="viewer"?u.role:"none";
              if(!confirm("Změnit oprávnění uživatele "+u.email+" na "+select.selectedOptions[0].text+"?")){select.value=previous;return}
              select.disabled=true;
              try{await api({action:"role",userId:u.id,role:select.value});feedback.textContent="Oprávnění aktualizováno.";await refreshUsers()}
              catch(e){select.value=previous;feedback.textContent="Chyba: "+e.message;select.disabled=false}
            });
            row.append(info,select);users.append(row);
          }
        }catch(e){users.textContent="Nepodařilo se načíst uživatele: "+e.message}
      }
      invite.addEventListener("submit",async(e)=>{
        e.preventDefault();inviteButton.disabled=true;feedback.textContent="Odesílám pozvánku…";
        try{const result=await api({action:"invite",email:email.value});feedback.textContent=result.message;email.value="";await refreshUsers();feedback.textContent=result.message}
        catch(err){feedback.textContent="Chyba: "+err.message}
        finally{inviteButton.disabled=false}
      });
      const reload=document.createElement("button");reload.type="button";reload.textContent="↻ Obnovit seznam";reload.style.cssText="padding:9px 12px;background:#283b55;color:#fff;border:1px solid #61728c;border-radius:9px;cursor:pointer";reload.addEventListener("click",refreshUsers);
      const close=document.createElement("button");close.type="button";close.textContent="Zavřít";
      close.style.cssText="padding:9px 16px;background:#283b55;color:white;border:1px solid #61728c;border-radius:9px;cursor:pointer";
      close.addEventListener("click",()=>panel.close());
      const actions=document.createElement("div");actions.style.cssText="display:flex;gap:8px;flex-wrap:wrap";actions.append(reload,close);
      panel.append(heading,intro,current,help,invite,feedback,users,actions);
      document.body.append(panel,manage);
      manage.addEventListener("click",()=>{panel.showModal();refreshUsers()});
    }
  } catch(e){showLogin("Nepodařilo se ověřit přihlášení. Zkontroluj připojení.");}
}
form.addEventListener("submit",async e=>{
 e.preventDefault();const btn=form.querySelector("button");btn.disabled=true;status.textContent="Přihlašuji…";
 try {const {error}=await supabase.auth.signInWithPassword({email:form.querySelector("#auth-email").value.trim(),password:form.querySelector("#auth-password").value});if(error){showLogin("Přihlášení se nezdařilo. Zkontroluj e-mail a heslo.");}else await check();}
 catch(e){showLogin("Přihlášení se nezdařilo. Zkus to znovu.");}
 finally{btn.disabled=false;}
});
await check();