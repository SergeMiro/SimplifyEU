import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const { prompt } = await request.json();

    if (!prompt) {
      return NextResponse.json(
        { error: "Prompt is required" },
        { status: 400 }
      );
    }

    const CHUTES_API_KEY =
      "cpk_2b8d86f9a766402d92d35d1edba975b5.f8003d77055654f78a00d2a590966c01.Aoldoa1mghrWc1qXlE04NfumQTfSmrQe";
    const CHUTES_BASE_URL = "https://llm.chutes.ai/v1";
    const CHUTES_MODEL = "chutesai/Mistral-Small-3.1-24B-Instruct-2503";

    const response = await fetch(`${CHUTES_BASE_URL}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${CHUTES_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: CHUTES_MODEL,
        messages: [{ role: "user", content: prompt }],
        max_tokens: 1024,
        stream: true, // Enable streaming
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: `API Error: ${response.status} - ${errorText}` },
        { status: response.status }
      );
    }

    // Proxy the stream
    return new NextResponse(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch (error) {
    console.error("AI Test API Error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}
