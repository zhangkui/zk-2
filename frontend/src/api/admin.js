import request from '@/utils/request'

export function listMaterials(params = {}) {
  return request.get('/admin/materials', { params })
}

export function getMaterial(id) {
  return request.get(`/admin/materials/${id}`)
}

export function createMaterial(data) {
  return request.post('/admin/materials', data)
}

export function updateMaterial(id, data) {
  return request.put(`/admin/materials/${id}`, data)
}

export function listUsers() {
  return request.get('/admin/users')
}

export function createUser(data) {
  return request.post('/admin/users', data)
}

export function updateUser(id, data) {
  return request.put(`/admin/users/${id}`, data)
}
