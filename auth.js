import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.95.3/+esm";
const supabase = createClient("https://hatzdirgwutbdarpgwro.supabase.co", "sb_publishable_FfWSpPjZSer3hnytJ1q9PA_yM6mEORu");
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
      const instructions=document.createElement("p");
      instructions.textContent="Účty, jejich schválení a role spravuj bezpečně v Supabase Authentication → Users. Pro schválení nastav v app_metadata roli viewer; pro správce admin. Role nikdy neměň v user_metadata.";
      const link=document.createElement("a");
      link.href="https://supabase.com/dashboard/project/hatzdirgwutbdarpgwro/auth/users";
      link.target="_blank";link.rel="noopener noreferrer";
      link.textContent="Otevřít uživatele v Supabase ↗";
      link.style.cssText="display:inline-block;color:#83bdff;margin:12px 0";
      const close=document.createElement("button");
      close.type="button";close.textContent="Zavřít";
      close.style.cssText="display:block;margin-top:16px;padding:9px 16px;background:#283b55;color:white;border:1px solid #61728c;border-radius:9px;cursor:pointer";
      close.addEventListener("click",()=>panel.close());
      panel.append(heading,intro,current,instructions,link,close);
      document.body.append(panel,manage);
      manage.addEventListener("click",()=>panel.showModal());
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