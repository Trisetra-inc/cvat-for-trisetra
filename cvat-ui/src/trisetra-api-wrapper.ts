export const TRISETRA_API_ENDPOINT = process.env.TRISETRA_API_ENDPOINT ?? 'http://localhost:4000/cvat';

export const TRISETRA_API_TOKEN = process.env.TRISETRA_API_TOKEN ?? 'trisetra_test';

export async function sendRequest(path: string, params?: { method?: 'PUT' | 'GET' | 'POST' | 'HEAD'; query?: Record<string, string>; body?: RequestInit['body']; headers?: RequestInit['headers'] }): Promise<any> {
    try {
        // eslint-disable-next-line no-param-reassign
        if (!params) params = { method: 'PUT', query: { token: TRISETRA_API_TOKEN } };
        if (!params.query) params.query = { token: TRISETRA_API_TOKEN };
        if (!params.method) params.method = 'PUT';
        if (!params.query.token) params.query.token = TRISETRA_API_TOKEN;

        const queryString = Object.entries(params.query).map(([k, v]) => `${k}=${v}`).join('&');

        const response = await fetch(`${TRISETRA_API_ENDPOINT}/${path}?${queryString}`, {
            method: params.method,
            body: params.body,
            headers: params.headers,
        });
        const json = await response.json();
        if (!response.ok) {
            throw new Error(json.message);
        }
        return json;
    } catch (err: any) {
        console.error(err.message, err);
        throw err;
    }
}
