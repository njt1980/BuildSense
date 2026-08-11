import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

const locales = ["en", "hi", "kn", "ta", "ml"];
const defaultLocale = "en";

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Split path to check for locale segment
  const segments = pathname.split("/");
  const hasLocale = locales.includes(segments[1]);
  const lang = hasLocale ? segments[1] : defaultLocale;

  const isApi = pathname.startsWith("/api");
  const isPublicAsset = 
    pathname.startsWith("/favicon.ico") || 
    pathname.startsWith("/fonts/") ||
    pathname.startsWith("/_next/");
  const isAuthCallback = pathname.startsWith("/auth/callback");

  // Redirect if no locale prefix and not a public asset, api route, or callback
  if (!hasLocale && !isApi && !isPublicAsset && !isAuthCallback) {
    const redirectUrl = new URL(`/${defaultLocale}${pathname}${request.nextUrl.search}`, request.url);
    return NextResponse.redirect(redirectUrl);
  }

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
  const pathWithoutLocale = hasLocale ? `/${segments.slice(2).join("/")}` : pathname;
  const isLoginPage = pathWithoutLocale === "/login" || pathWithoutLocale.startsWith("/login/");

  if (!user && !isLoginPage && !isAuthCallback && !isPublicAsset && !isApi) {
    const loginUrl = new URL(`/${lang}/login`, request.url);
    return NextResponse.redirect(loginUrl);
  }

  if (user && isLoginPage) {
    const homeUrl = new URL(`/${lang}`, request.url);
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
