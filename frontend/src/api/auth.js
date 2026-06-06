import request from '@/utils/request'

export function login(username, password) {
  const form = new FormData()
  form.append('username', username)
  form.append('password', password)
  return request.post('/auth/login', form)
}

export function getCurrentUser() {
  return request.get('/auth/me')
}

export function changePassword(oldPassword, newPassword) {
  return request.post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword
  })
}
