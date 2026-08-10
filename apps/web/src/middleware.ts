import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  // If local development mock environment is active, we bypass JWT checkpointer redirections here
  // and handle authentication checks client-side to prevent blocking offline developers
  if (!supabaseUrl || !supabaseAnonKey || supabaseUrl.includes("mock.supabase.co")) {
    return response;
  }

  const supabase = createServerClient(
    supabaseUrl,
    supabaseAnonKey,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            request.cookies.set(name, value)
          );
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Redirect unauthenticated requests to login page
  const isLoginPage = request.nextUrl.pathname.startsWith("/login");
  const isAuthCallback = request.nextUrl.pathname.startsWith("/auth/callback");
  const isPublicAsset = 
    request.nextUrl.pathname.startsWith("/favicon.ico") || 
    request.nextUrl.pathname.startsWith("/fonts/") ||
    request.nextUrl.pathname.startsWith("/_next/");

  if (!user && !isLoginPage && !isAuthCallback && !isPublicAsset) {
    // Redirect to login page
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  if (user && isLoginPage) {
    // Redirect to home if user is logged in and trying to access login page
    const homeUrl = new URL("/", request.url);
    return NextResponse.redirect(homeUrl);
  }

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
