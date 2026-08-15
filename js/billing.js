/* BetStats BETA billing + access gate.
   Requires Supabase Edge Functions:
   - create-checkout-session
   - stripe-webhook
   See README_ADMIN.md.
*/
(function () {
  const PRICE_PLN = 29.99;
  const WEEKLY_LABEL = '29,99 zł / tydzień';

  function getBillingFunctionUrl(name) {
    return `${SUPABASE_URL}/functions/v1/${name}`;
  }

  async function fetchSubscription() {
    if (!window.currentUser && !currentUser) return null;
    const uid = (window.currentUser || currentUser).id;
    const { data, error } = await sb.from('subscriptions')
      .select('id,status,current_period_end,cancel_at_period_end,plan_name,amount_pln')
      .eq('user_id', uid)
      .maybeSingle();
    if (error) {
      console.warn('Subscription check failed:', error);
      return null;
    }
    return data || null;
  }

  function isSubscriptionActive(sub) {
    if (!sub) return false;
    const active = ['active','trialing'].includes(sub.status);
    if (!active) return false;
    if (!sub.current_period_end) return true;
    return new Date(sub.current_period_end).getTime() > Date.now();
  }

  function showSubscriptionRequired() {
    const gate = document.getElementById('auth-gate');
    if (!gate) return;
    const box = gate.querySelector('.max-w-md') || gate.firstElementChild;
    if (box) {
      const old = box.querySelector('#subscription-gate-extra');
      if (old) old.remove();
      const extra = document.createElement('div');
      extra.id = 'subscription-gate-extra';
      extra.className = 'mt-4';
      extra.innerHTML = `
        <div class="rounded-xl border border-white/10 bg-white/5 p-4 text-left">
          <div class="text-white font-black mb-1">Dostęp nieaktywny</div>
          <div class="text-sm text-slate-400">Konto jest gotowe, ale aplikacja wymaga aktywnego dostępu.</div>
          <div class="text-red-400 font-black mt-2">${WEEKLY_LABEL}</div>
        </div>
        <button onclick="openPricingModal()" class="w-full mt-3 bg-red-600 hover:bg-red-500 text-white font-black py-3.5 rounded-xl transition">Aktywuj dostęp</button>
        <button onclick="openProfile()" class="w-full mt-2 bg-white/10 hover:bg-white/20 text-white font-bold py-3 rounded-xl transition">Moje konto</button>
      `;
      box.appendChild(extra);
    }
  }

  window.checkSubscription = async function () {
    if (!currentUser) {
      setAuthGate(true);
      return false;
    }
    const sub = await fetchSubscription();
    window.currentSubscription = sub;
    if (isSubscriptionActive(sub)) {
      setAuthGate(false);
      removeSubscriptionRequired();
      return true;
    }
    setAuthGate(true);
    showSubscriptionRequired();
    return false;
  };

  function removeSubscriptionRequired() {
    document.getElementById('subscription-gate-extra')?.remove();
  }

  window.openPricingModal = function () {
    const modal = document.getElementById('pricing-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    modal.style.display = 'flex';
    const input = document.getElementById('partner-code-input');
    if (input) input.focus();
  };

  window.closePricingModal = function () {
    const modal = document.getElementById('pricing-modal');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.style.display = '';
  };

  window.startCheckout = async function () {
    if (!currentUser) {
      closePricingModal();
      openAuthModal('register');
      return;
    }
    const activeSub = await fetchSubscription();
    window.currentSubscription = activeSub;
    if (isSubscriptionActive(activeSub)) {
      showToast('Masz już aktywny dostęp. Subskrypcja odnawia się automatycznie co tydzień.', 'info');
      return;
    }
    const btn = document.getElementById('buy-access-btn');
    const msg = document.getElementById('partner-code-message');
    const code = (document.getElementById('partner-code-input')?.value || '').trim().toUpperCase();
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Przekierowanie do płatności…';
    }
    if (msg) msg.classList.add('hidden');

    try {
      const { data, error } = await sb.functions.invoke('create-checkout-session', {
        body: {
          partner_code: code || null,
          success_url: `${window.location.origin}${window.location.pathname}?checkout=success`,
          cancel_url: `${window.location.origin}${window.location.pathname}?checkout=cancelled`
        }
      });
      if (error) throw error;
      if (!data?.url) throw new Error('Brak adresu płatności. Sprawdź konfigurację Stripe.');
      window.location.href = data.url;
    } catch (e) {
      console.error(e);
      if (msg) {
        msg.textContent = e?.message || 'Nie udało się rozpocząć płatności.';
        msg.className = 'text-xs mt-2 text-red-600';
      } else showToast('Nie udało się rozpocząć płatności.', 'error');
      if (btn) {
        btn.disabled = false;
        btn.textContent = `Kup dostęp — ${WEEKLY_LABEL}`;
      }
    }
  };

  async function handleCheckoutReturn() {
    const p = new URLSearchParams(location.search);
    const result = p.get('checkout');
    if (!result) return;
    history.replaceState({}, '', location.pathname + location.hash);
    if (result === 'cancelled') {
      showToast('Płatność została anulowana.', 'info');
      return;
    }
    if (result === 'success') {
      showToast('Płatność otrzymana. Sprawdzam aktywację dostępu…', 'info');
      for (let i = 0; i < 8; i++) {
        const ok = await window.checkSubscription();
        if (ok) {
          closePricingModal();
          showToast('Dostęp BetStats został aktywowany! ', 'success');
          return;
        }
        await new Promise(r => setTimeout(r, 1500));
      }
      showToast('Płatność jest weryfikowana. Odśwież stronę za chwilę.', 'info');
    }
  }

  function appendAccountSubscriptionUI() {
    const profile = document.getElementById('profile-modal');
    if (!profile || document.getElementById('subscription-account-box')) return;
    const anchor = profile.querySelector('#profile-nickname-section');
    if (!anchor) return;
    const box = document.createElement('div');
    box.id = 'subscription-account-box';
    box.className = 'rounded-xl border border-gray-200 p-4 mb-4';
    anchor.insertAdjacentElement('afterend', box);
    renderAccountSubscriptionUI();
  }

  function renderAccountSubscriptionUI() {
    const box = document.getElementById('subscription-account-box');
    if (!box) return;
    const sub = window.currentSubscription;
    const active = isSubscriptionActive(sub);
    box.innerHTML = `
      <div class="text-xs text-gray-500 mb-1">Dostęp BetStats</div>
      <div class="font-black ${active ? 'text-green-600' : 'text-red-600'}">${active ? 'AKTYWNY' : 'NIEAKTYWNY'}</div>
      ${active && sub.current_period_end ? `<div class="text-xs text-gray-500 mt-1">Ważny do: ${new Date(sub.current_period_end).toLocaleString('pl-PL')}</div>` : ''}
      <button onclick="openPricingModal()" class="w-full mt-3 bg-red-600 hover:bg-red-700 text-white font-bold py-2 rounded-lg">${active ? 'Przedłuż dostęp' : 'Kup dostęp'}</button>
    `;
  }

  // Minimal admin partner panel. Admin status is controlled in Supabase profiles.is_admin.
  window.openPartnerAdmin = async function () {
    if (!currentUser || !currentProfile?.is_admin) {
      showToast('Brak uprawnień administratora.', 'error');
      return;
    }
    let modal = document.getElementById('partner-admin-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'partner-admin-modal';
      modal.className = 'modal-overlay';
      modal.innerHTML = `
        <div class="bg-white rounded-2xl p-6 max-w-3xl w-full shadow-2xl max-h-[90vh] overflow-y-auto">
          <div class="flex justify-between items-center mb-4">
            <h3 class="font-black text-lg text-[#1e3a5f]">Program partnerski</h3>
            <button onclick="document.getElementById('partner-admin-modal').remove()" class="text-gray-500 text-2xl">×</button>
          </div>
          <div class="grid md:grid-cols-4 gap-2 mb-4">
            <input id="pa-name" placeholder="Nazwa partnera" class="px-3 py-2 border rounded-lg">
            <input id="pa-code" placeholder="Kod np. ALAN10" class="px-3 py-2 border rounded-lg uppercase">
            <input id="pa-commission" type="number" min="0" max="100" step="0.1" value="20" placeholder="Prowizja %" class="px-3 py-2 border rounded-lg">
            <button onclick="createPartnerCode()" class="bg-red-600 text-white rounded-lg font-bold px-3">Dodaj</button>
          </div>
          <div id="partner-admin-list" class="space-y-2"></div>
        </div>`;
      document.body.appendChild(modal);
    }
    modal.classList.add('flex');
    await renderPartnerAdmin();
  };

  window.createPartnerCode = async function () {
    const name = document.getElementById('pa-name')?.value.trim();
    const code = document.getElementById('pa-code')?.value.trim().toUpperCase();
    const commission = Number(document.getElementById('pa-commission')?.value);
    if (!name || !/^[A-Z0-9_-]{3,32}$/.test(code) || !Number.isFinite(commission) || commission < 0 || commission > 100) {
      showToast('Sprawdź nazwę, kod i prowizję.', 'warning'); return;
    }
    const { error } = await sb.from('partner_codes').insert({ partner_name: name, code, commission_percent: commission, active: true });
    if (error) { showToast(error.message, 'error'); return; }
    document.getElementById('pa-name').value = '';
    document.getElementById('pa-code').value = '';
    await renderPartnerAdmin();
    showToast('Kod partnera dodany.', 'success');
  };

  window.renderPartnerAdmin = async function () {
    const list = document.getElementById('partner-admin-list');
    if (!list) return;
    const { data, error } = await sb.from('partner_codes').select('*').order('created_at', { ascending: false });
    if (error) { list.innerHTML = `<div class="text-red-600 text-sm">${error.message}</div>`; return; }
    list.innerHTML = (data || []).map(p => `
      <div class="border rounded-xl p-3 flex flex-wrap gap-3 items-center justify-between">
        <div><b>${p.code}</b> · ${p.partner_name}<div class="text-xs text-gray-500">Prowizja ${p.commission_percent}% · użycia ${p.uses_count || 0}</div></div>
        <button onclick="togglePartnerCode('${p.id}', ${!p.active})" class="px-3 py-2 rounded-lg ${p.active ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-600'}">${p.active ? 'Aktywny' : 'Wyłączony'}</button>
      </div>`).join('') || '<div class="text-gray-500">Brak kodów.</div>';
  };

  window.togglePartnerCode = async function (id, active) {
    const { error } = await sb.from('partner_codes').update({ active }).eq('id', id);
    if (error) showToast(error.message, 'error');
    else renderPartnerAdmin();
  };

  // Add admin button to profile when applicable.
  const originalOpenProfile = window.openProfile;
  window.openProfile = async function () {
    await originalOpenProfile();
    appendAccountSubscriptionUI();
    renderAccountSubscriptionUI();
    if (currentProfile?.is_admin && !document.getElementById('open-partner-admin-btn')) {
      const p = document.getElementById('profile-modal')?.querySelector('.bg-white');
      if (p) {
        const b = document.createElement('button');
        b.id = 'open-partner-admin-btn';
        b.className = 'w-full bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 rounded-lg mb-2';
        b.textContent = 'Program partnerski (ADMIN)';
        b.onclick = window.openPartnerAdmin;
        p.querySelector('button[onclick="doLogout()"]')?.before(b);
      }
    }
  };

  window.addEventListener('load', async () => {
    setTimeout(handleCheckoutReturn, 1200);
  });
})();
