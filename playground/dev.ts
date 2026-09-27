// Local development: serve the playground with hot reload and forward API calls,
// by default to the public deployment. Override with JULIA_API_URL=http://localhost:8000.
import playground from "./index.html";

const api = (process.env.JULIA_API_URL ?? "https://julia-1.rdgs.net").replace(/\/$/, "");

const forward = (request: Request) => {
  const url = new URL(request.url);
  return fetch(api + url.pathname + url.search, {
    method: request.method,
    headers: request.headers,
    body: request.body,
  });
};

const server = Bun.serve({
  port: Number(process.env.PORT ?? 3000),
  routes: {
    "/": Response.redirect("/playground", 302),
    "/playground": playground,
    "/v1/*": forward,
  },
  development: { hmr: true, console: true },
});

console.log(`Playground on ${server.url}playground, API calls go to ${api}`);
