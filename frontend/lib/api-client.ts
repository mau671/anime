const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"

export async function apiFetch<T>(
  input: string,
  init?: RequestInit
): Promise<T> {
  const url = input.startsWith("http") ? input : `${API_BASE_URL}${input}`
  const res = await fetch(url, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  })

  if (!res.ok) {
    const body = await res.text()
    throw new Error(body || `Request failed with status ${res.status}`)
  }

  return (await res.json()) as T
}


