import { createServerClient } from "@supabase/ssr";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  if (process.env.NODE_ENV === "production") {
    return NextResponse.json({ error: "Not available" }, { status: 404 });
  }

  const { searchParams, origin } = new URL(request.url);
  const access_token = searchParams.get("access_token");
  const refresh_token = searchParams.get("refresh_token");

  if (!access_token || !refresh_token) {
    return NextResponse.json(
      { error: "Missing access_token or refresh_token" },
      { status: 400 }
    );
  }

  // Create redirect response first, then bind Supabase cookies to it
  const response = NextResponse.redirect(`${origin}/`);

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return [];
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const { error } = await supabase.auth.setSession({
    access_token,
    refresh_token,
  });

  if (error) {
    return NextResponse.json(
      { error: "Failed to set session" },
      { status: 500 }
    );
  }

  return response;
}
