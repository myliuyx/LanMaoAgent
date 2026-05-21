import request from './request'

export const authApi = {
  login: (username: string, password: string) =>
    request.post<{ token: string; expires_in: number; user: { id: number; username: string; role: string } }>(
      '/auth/login',
      { username, password }
    ),

  verify: () =>
    request.get<{ valid: boolean; user: { id: number; username: string; role: string } }>('/auth/verify'),
}
