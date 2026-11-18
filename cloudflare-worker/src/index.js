export default {
  async fetch(request, env) {
    if (!env.ORIGIN_URL || !env.ORIGIN_TOKEN) {
      return new Response('Blog proxy is not configured', { status: 503 });
    }

    const incoming = new URL(request.url);
    const origin = new URL(env.ORIGIN_URL);
    if (origin.protocol !== 'https:') {
      return new Response('Invalid origin configuration', { status: 503 });
    }
    origin.pathname = `${origin.pathname.replace(/\/+$/, '')}${incoming.pathname}`;
    origin.search = incoming.search;
    const headers = new Headers(request.headers);
    headers.delete('x-forwarded-host');
    headers.delete('x-forwarded-proto');
    headers.delete('x-forwarded-for');
    headers.set('x-forwarded-host', incoming.host);
    headers.set('x-forwarded-proto', 'https');
    headers.set('x-blog-origin-token', env.ORIGIN_TOKEN);
    return fetch(new Request(origin, { method: request.method, headers, body: request.body, redirect: 'manual' }));
  },
};
