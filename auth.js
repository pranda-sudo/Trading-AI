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
    if(data.user.app_metadata?.role !== "admin") {await supabase.auth.signOut();showLogin("Tento účet nemá schválený přístup.");return;}
    document.documentElement.classList.add("auth-allowed");
    gate.remove();
    const btn=document.createElement("button");
    btn.type="button";btn.textContent="Odhlásit se";btn.id="auth-logout";
    btn.addEventListener("click",async()=>{await supabase.auth.signOut();location.reload();});
    document.body.append(btn);
  } catch(e){showLogin("Nepodařilo se ověřit přihlášení. Zkontroluj připojení.");}
}
form.addEventListener("submit",async e=>{
 e.preventDefault();const btn=form.querySelector("button");btn.disabled=true;status.textContent="Přihlašuji…";
 try {const {error}=await supabase.auth.signInWithPassword({email:form.querySelector("#auth-email").value.trim(),password:form.querySelector("#auth-password").value});if(error){showLogin("Přihlášení se nezdařilo. Zkontroluj e-mail a heslo.");}else await check();}
 catch(e){showLogin("Přihlášení se nezdařilo. Zkus to znovu.");}
 finally{btn.disabled=false;}
});
await check();