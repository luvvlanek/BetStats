// BetStats BETA — Stripe webhook
// Deploy: supabase functions deploy stripe-webhook --no-verify-jwt
// Secrets: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

async function stripeRequest(path: string, method = "GET") {
  const key = Deno.env.get("STRIPE_SECRET_KEY")!;
  const r = await fetch(`https://api.stripe.com/v1/${path}`, {
    method,
    headers: { Authorization: `Bearer ${key}` },
  });
  return await r.json();
}

Deno.serve(async (req) => {
  try {
    const secret = Deno.env.get("STRIPE_WEBHOOK_SECRET");
    if (!secret) throw new Error("Brak STRIPE_WEBHOOK_SECRET.");

    const signature = req.headers.get("stripe-signature");
    const payload = await req.text();
    // Stripe signature verification is intentionally performed here before parsing.
    // This implementation uses the Web Crypto API and supports Stripe's t=... ,v1=... format.
    if (!signature) return new Response("Missing signature", { status: 400 });

    const parts = Object.fromEntries(signature.split(",").map(x => x.split("=")));
    const timestamp = Number(parts.t);
    const sig = parts.v1;
    if (!timestamp || !sig) return new Response("Invalid signature", { status: 400 });
    if (Math.abs(Date.now() / 1000 - timestamp) > 300) return new Response("Expired signature", { status: 400 });

    const enc = new TextEncoder();
    const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
    const signed = await crypto.subtle.sign("HMAC", key, enc.encode(`${timestamp}.${payload}`));
    const expected = Array.from(new Uint8Array(signed)).map(b => b.toString(16).padStart(2, "0")).join("");
    if (expected !== sig) return new Response("Invalid signature", { status: 400 });

    const event = JSON.parse(payload);
    const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    if (event.type === "checkout.session.completed") {
      const session = event.data.object;
      const userId = session.metadata?.user_id;
      if (!userId) throw new Error("Checkout bez user_id.");
      const stripeSubId = session.subscription;
      const stripeCustomerId = session.customer;
      const partnerCode = session.metadata?.partner_code || null;

      let sub: any = null;
      if (stripeSubId) sub = await stripeRequest(`subscriptions/${stripeSubId}`);

      const periodEnd = sub?.current_period_end ? new Date(sub.current_period_end * 1000).toISOString() : null;
      const status = sub?.status || "active";

      const { data: savedSub, error: subError } = await supabase.from("subscriptions").upsert({
        user_id: userId,
        stripe_customer_id: stripeCustomerId,
        stripe_subscription_id: stripeSubId,
        status,
        plan_name: "BetStats Weekly",
        amount_pln: 29.99,
        current_period_end: periodEnd,
        cancel_at_period_end: !!sub?.cancel_at_period_end,
        partner_code: partnerCode,
        updated_at: new Date().toISOString(),
      }, { onConflict: "user_id" }).select("id").single();
      if (subError) throw subError;


    }

    if (event.type === "customer.subscription.updated" || event.type === "customer.subscription.deleted") {
      const sub = event.data.object;
      const userId = sub.metadata?.user_id;
      const status = event.type === "customer.subscription.deleted" ? "canceled" : sub.status;
      const periodEnd = sub.current_period_end ? new Date(sub.current_period_end * 1000).toISOString() : null;
      const update: any = {
        status,
        stripe_customer_id: sub.customer,
        stripe_subscription_id: sub.id,
        current_period_end: periodEnd,
        cancel_at_period_end: !!sub.cancel_at_period_end,
        updated_at: new Date().toISOString(),
      };
      if (userId) {
        await supabase.from("subscriptions").update(update).eq("user_id", userId);
      } else {
        await supabase.from("subscriptions").update(update).eq("stripe_subscription_id", sub.id);
      }
    }

    if (event.type === "invoice.paid") {
      const invoice = event.data.object;
      const subId = invoice.subscription;
      if (subId) {
        const sub = await stripeRequest(`subscriptions/${subId}`);
        const periodEnd = sub?.current_period_end ? new Date(sub.current_period_end * 1000).toISOString() : null;
        const { data: savedSub } = await supabase.from("subscriptions").update({
          status: "active",
          current_period_end: periodEnd,
          updated_at: new Date().toISOString(),
        }).eq("stripe_subscription_id", subId).select("*").maybeSingle();

        // Track partner commission on every successful recurring invoice.
        const partnerCode = sub?.metadata?.partner_code || savedSub?.partner_code || null;
        const userId = sub?.metadata?.user_id || savedSub?.user_id || null;
        if (partnerCode && userId) {
          const { data: partners } = await supabase.from("partner_codes").select("*").eq("code", partnerCode).eq("active", true).limit(1);
          const partner = partners?.[0];
          if (partner) {
            const gross = Number(((invoice.amount_paid || 0) / 100).toFixed(2));
            const commission = Number((gross * Number(partner.commission_percent) / 100).toFixed(2));
            if (gross > 0) {
              await supabase.from("partner_referrals").upsert({
                partner_code_id: partner.id,
                partner_code: partner.code,
                partner_name: partner.partner_name,
                user_id: userId,
                subscription_id: savedSub?.id || null,
                stripe_subscription_id: subId,
                stripe_invoice_id: invoice.id,
                gross_amount_pln: gross,
                commission_percent: partner.commission_percent,
                commission_amount_pln: commission,
                status: "pending",
              }, { onConflict: "stripe_invoice_id" });
            }
          }
        }
      }
    }

    if (event.type === "invoice.payment_failed") {
      const invoice = event.data.object;
      if (invoice.subscription) {
        await supabase.from("subscriptions").update({
          status: "past_due",
          updated_at: new Date().toISOString(),
        }).eq("stripe_subscription_id", invoice.subscription);
      }
    }

    return new Response(JSON.stringify({ received: true }), { headers: { "Content-Type": "application/json" } });
  } catch (error) {
    console.error(error);
    return new Response(JSON.stringify({ error: error?.message || "Webhook error" }), { status: 400 });
  }
});
