import client from './client.js'

/**
 * Get monthly summary.
 * @param {number} month - 1-12
 * @param {number} year
 */
export async function getMonthlySummary(month, year) {
  const { data } = await client.get('/analytics/monthly', { params: { month, year } })
  return data
}

/**
 * Get category breakdown.
 * @param {number} month - 1-12
 * @param {number} year
 */
export async function getCategories(month, year) {
  const { data } = await client.get('/analytics/categories', { params: { month, year } })
  return data
}
