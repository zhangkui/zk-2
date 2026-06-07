import request from '@/utils/request'

export function listStocktakeTasks(params = {}) {
  return request.get('/stocktake', { params })
}

export function getStocktakeTask(id) {
  return request.get(`/stocktake/${id}`)
}

export function createStocktakeTask(data) {
  return request.post('/stocktake', data)
}

export function saveStocktakeItems(taskId, data) {
  return request.post(`/stocktake/${taskId}/save`, data)
}

export function submitStocktakeTask(taskId) {
  return request.post(`/stocktake/${taskId}/submit`)
}

export function confirmStocktakeTask(taskId) {
  return request.post(`/stocktake/${taskId}/confirm`)
}

export function closeStocktakeTask(taskId, data = {}) {
  return request.post(`/stocktake/${taskId}/close`, data)
}

export function exportStocktakeDiff(taskId) {
  return request.get(`/stocktake/${taskId}/export-diff`, { responseType: 'blob' })
}

export function exportOperationsDiff(params = {}) {
  return request.get('/operations/export-diff', { params, responseType: 'blob' })
}
