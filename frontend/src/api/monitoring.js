import request from '@/utils/request'

export function listWarnings(params = {}) {
  return request.get('/warnings', { params })
}

export function handleWarning(id, data) {
  return request.put(`/warnings/${id}`, data)
}

export function triggerWarningScan() {
  return request.get('/warnings/scan')
}

export function listOperations(params = {}) {
  return request.get('/operations', { params })
}

export function getDashboardStats() {
  return request.get('/dashboard/stats')
}
