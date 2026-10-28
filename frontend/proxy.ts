import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
    const token = request.cookies.get('access_token')?.value;
    const { pathname } = request.nextUrl;
    const host = (request.headers.get('host') || '').toLowerCase();
    
    const isProd = host.includes('aikrofy.com') || host.includes('fundacionunderlife.org');
    const isAppSubdomain = host.startsWith('app.');
    const isUnderlifeSubdomain = host.includes('aikrofy.fundacionunderlife.org') || host.includes('fundacionunderlife.org');

    // If accessing via aikrofy.fundacionunderlife.org at root '/' -> rewrite/serve the official community open-core portal
    if (isUnderlifeSubdomain && pathname === '/') {
        const url = new URL('/community', request.url);
        const response = NextResponse.rewrite(url);
        response.headers.set('x-is-community', 'true');
        return response;
    }

    // Public pages that belong on the main domain or institutional subdomains
    const publicPaths = ['/terms', '/privacy', '/refunds', '/pricing', '/wellness', '/beta-register', '/community', '/activate'];
    const isPublicPath = publicPaths.some(path => pathname.startsWith(path)) || pathname === '/';

    if (isProd) {
        if (isUnderlifeSubdomain) {
            // Underlife subdomain preserves public institutional routes directly
            return NextResponse.next();
        }

        if (isAppSubdomain) {
            // If accessing app.aikrofy.com on a public path without being logged in -> redirect to main domain
            if (isPublicPath && !token) {
                const targetPath = pathname === '/' ? '' : pathname;
                return NextResponse.redirect(`https://aikrofy.com${targetPath}`);
            }
            // If accessing root '/' on app subdomain and logged in -> go to dashboard
            if (pathname === '/' && token) {
                return NextResponse.redirect(new URL('/dashboard', request.url));
            }
        } else {
            // If accessing main domain (aikrofy.com)
            // If logged in -> redirect to app subdomain dashboard
            if (token) {
                return NextResponse.redirect('https://app.aikrofy.com/dashboard');
            }
            // If accessing a protected path on main domain -> redirect to app subdomain login
            const protectedPaths = ['/dashboard', '/pos', '/leads', '/customers', '/agents', '/settings', '/subscribe', '/landing-pages'];
            const isProtected = protectedPaths.some((path) => pathname.startsWith(path));
            if (isProtected) {
                return NextResponse.redirect('https://app.aikrofy.com/login');
            }
        }
    } else {
        // Localhost development behavior
        const protectedPaths = ['/dashboard', '/leads', '/customers', '/agents', '/settings', '/subscribe', '/landing-pages'];
        const isProtected = protectedPaths.some((path) => pathname.startsWith(path));
        
        if (isProtected && !token) {
            return NextResponse.redirect(new URL('/login', request.url));
        }
        
        if (pathname === '/' && token) {
            return NextResponse.redirect(new URL('/dashboard', request.url));
        }
    }

    const authPaths = ['/login', '/register'];
    const isAuthPath = authPaths.some((path) => pathname.startsWith(path));

    if (isAuthPath && token) {
        return NextResponse.redirect(isProd ? 'https://app.aikrofy.com/dashboard' : new URL('/dashboard', request.url));
    }

    return NextResponse.next();
}

export const config = {
    matcher: [
        '/',
        '/dashboard/:path*',
        '/pos/:path*',
        '/leads/:path*',
        '/customers/:path*',
        '/agents/:path*',
        '/settings/:path*',
        '/landing-pages/:path*',
        '/login',
        '/register',
        '/beta-register',
        '/subscribe',
        '/terms',
        '/privacy',
        '/refunds',
        '/pricing',
        '/wellness',
        '/community',
        '/activate'
    ],
};
