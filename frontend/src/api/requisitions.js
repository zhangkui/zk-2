import request from '@/utils/request'

export function listRequisitions(params = {}) {
  return request.get('/requisitions', { params })
}

export function getRequisition(id) {
  return request.get(`/requisitions/${id}`)
}

export function createRequisition(data) {
  return request.post('/requisitions', data)
}

export function approveRequisition(id, data = {}) {
  return request.post(`/requisitions/${id}/approve`, data)
}

export function rejectRequisition(id, data) {
  return request.post(`/requisitions/${id}/reject`, data)
}

export function cancelRequisition(id, data = {}) {
  return request.post(`/requisitions/${id}/cancel`, data)
}
