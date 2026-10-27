export interface Env {
  BUCKET: R2Bucket;
  ALLOWED_KEYS: string; // JSON array of allowed R2 keys
}

function parseRange(rangeHeader: string, fullSize: number): { offset: number; length: number } | null {
  const match = rangeHeader.match(/^bytes=(\d+)-(\d*)$/);
  if (!match) return null;
  const start = parseInt(match[1], 10);
  const end = match[2] ? parseInt(match[2], 10) : fullSize - 1;
  if (isNaN(start) || start >= fullSize || (match[2] && (isNaN(end) || end < start || end >= fullSize))) {
    return null;
  }
  return { offset: start, length: end - start + 1 };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const key = decodeURIComponent(url.pathname.slice(1)); // remove leading /

    // 1. Method whitelist
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    // 2. Parse allowed keys from environment
    let allowedKeys: string[];
    try {
      allowedKeys = JSON.parse(env.ALLOWED_KEYS || "[]");
    } catch {
      return new Response("Server configuration error: invalid ALLOWED_KEYS", { status: 500 });
    }

    // 3. Authorization: only explicitly allowed keys
    if (!allowedKeys.includes(key)) {
      return new Response("Forbidden", { status: 403 });
    }

    // 4. Fetch object metadata first (for HEAD and size checks)
    let object = await env.BUCKET.get(key);
    if (!object) {
      return new Response("Not Found", { status: 404 });
    }

    const fullSize = object.size;
    const headers = new Headers();
    headers.set("Content-Type", object.httpMetadata?.contentType || "video/mp4");
    headers.set("Accept-Ranges", "bytes");
    headers.set("Cache-Control", "public, max-age=31536000, immutable");

    // HEAD: return metadata only
    if (request.method === "HEAD") {
      headers.set("Content-Length", String(fullSize));
      return new Response(null, { status: 200, headers });
    }

    // GET: handle Range support for video streaming
    const rangeHeader = request.headers.get("Range");
    if (rangeHeader) {
      const range = parseRange(rangeHeader, fullSize);
      if (range) {
        const rangedObject = await env.BUCKET.get(key, { range });
        if (!rangedObject) {
          return new Response("Not Found", { status: 404 });
        }
        const end = range.offset + rangedObject.size - 1;
        headers.set("Content-Length", String(rangedObject.size));
        headers.set("Content-Range", `bytes ${range.offset}-${end}/${fullSize}`);
        return new Response(rangedObject.body, { status: 206, headers });
      } else {
        headers.set("Content-Range", `bytes */${fullSize}`);
        return new Response("Range Not Satisfiable", { status: 416, headers });
      }
    }

    // GET: full object
    headers.set("Content-Length", String(fullSize));
    return new Response(object.body, { status: 200, headers });
  },
};
