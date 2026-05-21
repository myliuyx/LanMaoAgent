export default [
  {
    url: '/api/v1/auth/login',
    method: 'post',
    response: () => ({
      code: 0,
      message: 'ok',
      data: {
        token: 'mock_token_12345',
        expires_in: 86400,
        user: {
          id: 1,
          username: 'admin',
          role: 'admin',
        },
      },
    }),
  },
  {
    url: '/api/v1/auth/verify',
    method: 'get',
    response: () => ({
      code: 0,
      message: 'ok',
      data: {
        valid: true,
        user: {
          id: 1,
          username: 'admin',
          role: 'admin',
        },
      },
    }),
  },
]
