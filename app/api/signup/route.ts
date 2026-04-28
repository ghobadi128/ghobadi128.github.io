import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { name, dispensary, email, phone, atm_situation, pain_point } = body;

    if (!email || !dispensary) {
      return NextResponse.json({ error: "Email and dispensary name are required." }, { status: 400 });
    }

    const entry = {
      submitted_at: new Date().toISOString(),
      name: name ?? "",
      dispensary,
      email,
      phone: phone ?? "",
      atm_situation: atm_situation ?? "",
      pain_point: pain_point ?? "",
    };

    // Submissions are captured in Vercel Function Logs (Dashboard → Functions → Logs)
    console.log("PAYTREE_SIGNUP", JSON.stringify(entry));

    return NextResponse.json({ success: true });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
