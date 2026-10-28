import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { 
      amount, 
      companyName, 
      taxId, 
      email, 
      phone, 
      method,
      credits
    } = body;

    // 1. Validate & sanitize inputs
    const parsedAmount = Math.max(5, parseFloat(amount) || 20);
    const enterpriseName = (companyName && String(companyName).trim()) || 'Cliente Empresarial';
    const enterpriseTaxId = (taxId && String(taxId).trim()) || 'N/A';
    const enterpriseEmail = (email && String(email).trim()) || 'facturacion@empresa.com';
    const paymentMethod = method === 'paypal' ? 'paypal' : 'card';
    const calculatedCredits = credits || Math.round(parsedAmount * 100);
    const origin = req.headers.get('origin') || 'https://aikrofy.com';

    let orderId = '';
    let paymentUrl = '';
    const invoiceId = `AIK-CRED-${Date.now()}`;

    // 2. Read PayPal Credentials (live verified gateway)
    const paypalId = process.env.PAYPAL_CLIENT_ID || process.env.PAYPAL_ID || process.env.NEXT_PUBLIC_PAYPAL_CLIENT_ID || 'AUYxLqb4aKaVxE9Rd4l7ZmsmOD3EwFzCm5_qj9esAgDlvqUutzP5aomnhRFbWFg4s5vnJ14IOvMeY6in';
    const paypalSecret = process.env.PAYPAL_CLIENT_SECRET || process.env.PAYPAL_SECRET || 'EKO7iXVxvhpnBO6QAGHvNYlAAQZFoyzEZLz4vS0J64RJoCKZnodSGctBuFIVEtqQ0AT99iauplBVHryi';
    const paypalMode = process.env.PAYPAL_MODE || 'live';
    const baseUrl = paypalMode === 'sandbox' ? 'https://api-m.sandbox.paypal.com' : 'https://api-m.paypal.com';

    // 3. Create PayPal Dynamic Order
    if (paypalId && paypalSecret) {
      try {
        const tokenRes = await fetch(`${baseUrl}/v1/oauth2/token`, {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
            'Accept-Language': 'en_US',
            'Authorization': `Basic ${Buffer.from(paypalId + ':' + paypalSecret).toString('base64')}`,
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: 'grant_type=client_credentials',
        });
        const tokenData = await tokenRes.json();

        if (tokenData.access_token) {
          const isGuestCard = paymentMethod === 'card';
          const orderRes = await fetch(`${baseUrl}/v2/checkout/orders`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${tokenData.access_token}`,
            },
            body: JSON.stringify({
              intent: 'CAPTURE',
              purchase_units: [{
                reference_id: invoiceId,
                amount: { currency_code: 'USD', value: parsedAmount.toFixed(2) },
                description: `Recarga Combustible IA: ${calculatedCredits.toLocaleString()} creditos (${enterpriseName})`,
                custom_id: JSON.stringify({
                  companyName: enterpriseName,
                  taxId: enterpriseTaxId,
                  phone,
                  credits: calculatedCredits
                }).slice(0, 127),
              }],
              application_context: {
                brand_name: 'Aikrofy Enterprise AI',
                landing_page: isGuestCard ? 'BILLING' : 'NO_PREFERENCE',
                shipping_preference: 'NO_SHIPPING',
                user_action: 'PAY_NOW',
                return_url: `${origin}/pricing?success=true&provider=${isGuestCard ? 'card' : 'paypal'}&orderId=${invoiceId}&amount=${parsedAmount}&credits=${calculatedCredits}`,
                cancel_url: `${origin}/pricing?canceled=true#combustible`,
              },
            }),
          });
          const orderData = await orderRes.json();
          if (orderData.id) {
            orderId = orderData.id;
            const approveLink = orderData.links?.find((l: any) => l.rel === 'approve');
            if (approveLink?.href) {
              paymentUrl = approveLink.href;
            }
          }
        }
      } catch (err) {
        console.warn('[Credits Order API] PayPal dynamic error:', err);
      }
    }

    // Direct fallback if no dynamic order
    if (!paymentUrl && !orderId) {
      paymentUrl = `https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business=billing@aikrofy.com&currency_code=USD&amount=${parsedAmount}&item_name=Recarga+Creditos+Aikrofy+${calculatedCredits}+creditos&no_shipping=1&return=${encodeURIComponent(origin + '/pricing?success=true&orderId=' + invoiceId + '&amount=' + parsedAmount + '&credits=' + calculatedCredits)}`;
    }

    return NextResponse.json({
      success: true,
      orderId,
      paymentUrl,
      invoiceId,
      amount: parsedAmount,
      credits: calculatedCredits,
      clientId: paypalId || '',
    });
  } catch (error: any) {
    console.error('[Credits Order API] Error:', error);
    return NextResponse.json({
      success: false,
      error: error.message || 'Error processing credit order',
    }, { status: 500 });
  }
}
