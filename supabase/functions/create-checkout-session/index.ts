// BetStats BETA — Stripe Checkout
// Deploy with: supabase functions deploy create-checkout-session
// Secrets: STRIPE_SECRET_KEY
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  try {
    const authHeader = req.headers.get("Authorization");
    if (!authHeader) throw new Error("Brak autoryzacji.");

    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const anonKey = Deno.env.get("SUPABASE_ANON_KEY")!;
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const stripeKey = Deno.env.get("STRIPE_SECRET_KEY")!;
    const admin = createClient(supabaseUrl, serviceKey);
    const userClient = createClient(supabaseUrl, anonKey, { global: { headers: { Authorization: authHeader } } });

    const { data: { user }, error: userError } = await userClient.auth.getUser();
    if (userError || !user) throw new Error("Sesja wygasła. Zaloguj się ponownie.");

    const body = await req.json().catch(() => ({}));
    const partnerCode = typeof body.partner_code === "string" ? body.partner_code.trim().toUpperCase() : "";
    const origin = req.headers.get("origin") || new URL(req.url).origin;
    const successUrl = body.success_url || `${origin}/?checkout=success`;
    const cancelUrl = body.cancel_url || `${origin}/?checkout=cancelled`;

    let partner: any = null;
    if (partnerCode) {
      const { data, error } = await admin.rpc("get_partner_code", { p_code: partnerCode });
      if (error) throw new Error("Nie udało się zweryfikować kodu partnera.");
      partner = data?.[0] || null;
      if (!partner || !partner.active) throw new Error("Kod partnera jest nieprawidłowy lub nieaktywny.");
      if (partner.max_uses !== null && partner.uses_count >= partner.max_uses) throw new Error("Limit użyć tego kodu został wyczerpany.");
    }

    // Weekly recurring PLN 29.99. Stripe creates the subscription after checkout.
    const params = new URLSearchParams();
    params.set("mode", "subscription");
    params.set("success_url", successUrl);
    params.set("cancel_url", cancelUrl);
    params.set("customer_email", user.email || "");
    params.set("line_items[0][quantity]", "1");
    params.set("line_items[0][price_data][currency]", "pln");
    params.set("line_items[0][price_data][unit_amount]", "2999");
    params.set("line_items[0][price_data][product_data][name]", "BetStats — dostęp tygodniowy");
    params.set("line_items[0][price_data][product_data][description]", "Pełny dostęp do BetStats przez 7 dni");
    params.set("line_items[0][price_data][recurring][interval]", "week");
    params.set("metadata[user_id]", user.id);
    params.set("metadata[partner_code]", partner?.code || "");
    params.set("subscription_data[metadata][user_id]", user.id);
    params.set("subscription_data[metadata][partner_code]", partner?.code || "");

    const stripeResponse = await fetch("https://api.stripe.com/v1/checkout/sessions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${stripeKey}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });
    const session = await stripeResponse.json();
    if (!stripeResponse.ok) {
      console.error("Stripe:", session);
      throw new Error(session?.error?.message || "Stripe nie utworzył płatności.");
    }

    return new Response(JSON.stringify({ url: session.url, session_id: session.id }), {
      headers: { ...cors, "Content-Type": "application/json" },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error?.message || "Błąd serwera." }), {
      status: 400,
      headers: { ...cors, "Content-Type": "application/json" },
    });
  }
});
