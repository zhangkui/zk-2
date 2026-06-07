import request from '@/utils/request'

export function listInventory(params = {}) {
  return request.get('/inventory', { params })
}

export function getInventory(id) {
  return request.get(`/inventory/${id}`)
}

export function createInventory(data) {
  return request.post('/inventory', data)
}

export function openInventory(id, data = {}) {
  return request.post(`/inventory/${id}/open`, data)
}

export function outboundInventory(id, data) {
  return request.post(`/inventory/${id}/outbound`, data)
}

export function returnInventory(id, data) {
  return request.post(`/inventory/${id}/return`, data)
}

export function scrapInventory(id, data) {
  return request.post(`/inventory/${id}/scrap`, data)
}

export function inventoryCheck(id, data) {
  return request.post(`/inventory/${id}/inventory-check`, data)
}

export function getInventoryOperations(id) {
  return request.get(`/inventory/${id}/operations`)
}

export function reserveInventory(id, data) {
  return request.post(`/inventory/${id}/reserve`, data)
}

export function listInventoryReservations(id, params = {}) {
  return request.get(`/inventory/${id}/reservations`, { params })
}

export function releaseReservation(reservationId, data = {}) {
  return request.post(`/inventory/reservations/${reservationId}/release`, data)
}
