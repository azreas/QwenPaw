const CSRF_COOKIE_NAME = "qwenpaw_session";

export function readCsrfToken(cookieText = document.cookie): string | null {
  const parts = cookieText.split(";").map((part) => part.trim());
  const prefix = `${CSRF_COOKIE_NAME}=`;
  const found = parts.find((part) => part.startsWith(prefix));
  if (!found) return null;
  return decodeURIComponent(found.slice(prefix.length));
}

export function appendCsrfHeader(
  headers: Headers | Record<string, string>,
  cookieText = document.cookie,
): void {
  const token = readCsrfToken(cookieText);
  if (!token) return;
  if (headers instanceof Headers) {
    if (!headers.has("X-CSRF-Token")) {
      headers.set("X-CSRF-Token", token);
    }
  } else if (!("X-CSRF-Token" in headers)) {
    headers["X-CSRF-Token"] = token;
  }
}
