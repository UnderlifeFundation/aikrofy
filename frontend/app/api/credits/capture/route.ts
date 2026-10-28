import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { orderId, invoiceId, companyName, email, credits } = body;

    if (!orderId) {
      return NextResponse.json({ success: false, error: 'Missing orderId' }, { status: 400 });
    }

    const paypalId = process.env.PAYPAL_CLIENT_ID || process.env.PAYPAL_ID || process.env.NEXT_PUBLIC_PAYPAL_CLIENT_ID || 'AUYxLqb4aKaVxE9Rd4l7ZmsmOD3EwFzCm5_qj9esAgDlvqUutzP5aomnhRFbWFg4s5vnJ14IOvMeY6in';
    const paypalSecret = process.env.PAYPAL_CLIENT_SECRET || process.env.PAYPAL_SECRET || 'EKO7iXVxvhpnBO6QAGHvNYlAAQZFoyzEZLz4vS0J64RJoCKZnodSGctBuFIVEtqQ0AT99iauplBVHryi';
    const paypalMode = process.env.PAYPAL_MODE || 'live';
    const baseUrl = paypalMode === 'sandbox' ? 'https://api-m.sandbox.paypal.com' : 'https://api-m.paypal.com';

    let capturedAmount = 50;
    let capturedCredits = credits || 5000;

    if (paypalId && paypalSecret) {
      // 1. Get Access Token
      const tokenRes = await fetch(`${baseUrl}/v1/oauth2/token`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Authorization': `Basic ${Buffer.from(paypalId + ':' + paypalSecret).toString('base64')}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'grant_type=client_credentials',
      });
      const tokenData = await tokenRes.json();

      if (tokenData.access_token) {
        // 2. Capture Order
        const captureRes = await fetch(`${baseUrl}/v2/checkout/orders/${orderId}/capture`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${tokenData.access_token}`,
          },
        });
        const captureData = await captureRes.json();
        
        if (captureData.status === 'COMPLETED' || captureData.status === 'APPROVED') {
          const value = captureData.purchase_units?.[0]?.payments?.captures?.[0]?.amount?.value;
          if (value) {
            capturedAmount = parseFloat(value);
            capturedCredits = Math.round(capturedAmount * 100);
          }
        }
      }
    }

    return NextResponse.json({
      success: true,
      status: 'COMPLETED',
      amount: capturedAmount,
      credits: capturedCredits,
      invoiceId: invoiceId || `AIK-CRED-${Date.now().toString().slice(-6)}`,
      companyName: companyName || 'Cliente Empresarial',
      email: email || '',
    });
  } catch (error: any) {
    console.error('[Credits Capture API] Error:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
