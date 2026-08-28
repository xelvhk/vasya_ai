const TOKEN_KEY = "vasyaApiToken";

export function loadApiToken() {
  return sessionStorage.getItem(TOKEN_KEY) || "";
}

export function saveApiToken(token) {
  const normalized = token.trim();
  if (normalized) {
    sessionStorage.setItem(TOKEN_KEY, normalized);
  } else {
    sessionStorage.removeItem(TOKEN_KEY);
  }
}

export function clearApiToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

export function createApiClient({ getToken, onUnauthorized }) {
  async function requestJson(path, options = {}) {
    const token = getToken().trim();
    const response = await fetch(path, {
      ...options,
      headers: {
        ...(token ? { "x-api-key": token } : {}),
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {}),
      },
    });

    let responsePayload = {};
    if (response.status !== 204) {
      try {
        responsePayload = await response.json();
      } catch (_error) {
        responsePayload = {};
      }
    }

    if (!response.ok) {
      if (response.status === 401) {
        onUnauthorized();
      }
      const detail =
        typeof responsePayload.detail === "string"
          ? responsePayload.detail
          : "Запрос завершился с HTTP " + response.status + ".";
      throw new Error(detail);
    }
    return responsePayload;
  }

  return { requestJson };
}

