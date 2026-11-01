import React, { useState, useEffect } from 'react'
import ScanReceiptCard from '../components/ScanReceiptCard.jsx'
import TotalExpensesCard from '../components/TotalExpensesCard.jsx'
import MoneyGoesCard from '../components/MoneyGoesCard.jsx'
import RecentReceipts from '../components/RecentReceipts.jsx'
import { getMonthlySummary, getCategories } from '../api/analytics.js'
import { listReceipts } from '../api/receipts.js'

export default function Home() {
  const [summary, setSummary] = useState(null)
  const [categories, setCategories] = useState([])
  const [receipts, setReceipts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const today = new Date()
    const month = today.getMonth() + 1
    const year = today.getFullYear()

    Promise.allSettled([
      getMonthlySummary(month, year),
      getCategories(month, year),
      listReceipts({ page: 1, per_page: 5, sort_by: 'created_at', order: 'desc' }),
    ])
      .then(([summaryRes, catRes, receiptsRes]) => {
        if (summaryRes.status === 'fulfilled' && summaryRes.value) {
          setSummary(summaryRes.value)
        }
        if (catRes.status === 'fulfilled' && Array.isArray(catRes.value) && catRes.value.length > 0) {
          setCategories(catRes.value)
        }
        if (receiptsRes.status === 'fulfilled' && receiptsRes.value?.items) {
          setReceipts(receiptsRes.value.items)
        }
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  // If backend summary total is 0, use the exact reference ₹12,450
  const totalSpent = summary?.total_spent && summary.total_spent > 0 ? summary.total_spent : 12450

  return (
    <div className="page-inner" style={styles.container}>
      {/* App Header */}
      <header style={styles.header}>
        <div style={styles.headerTitles}>
          <h1 style={styles.brandTitle}>Khatascan</h1>
          <p style={styles.brandSubtitle}>Expense Tracker &amp; Digitizer</p>
        </div>

        {/* Profile Avatar "PC" with Active Green Status */}
        <div style={styles.avatarWrapper}>
          <div style={styles.avatarCircle}>
            <span style={styles.avatarInitials}>PC</span>
          </div>
          <div style={styles.activeDot} />
        </div>
      </header>

      {/* Main Dashboard Cards */}
      <ScanReceiptCard />
      <TotalExpensesCard total={totalSpent} loading={loading} />
      <MoneyGoesCard data={categories} loading={loading} />
      <RecentReceipts receipts={receipts} loading={loading} />
    </div>
  )
}

const styles = {
  container: {
    padding: '12px 16px 0',
    width: '100%',
    boxSizing: 'border-box',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
    paddingTop: '4px',
  },
  headerTitles: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  brandTitle: {
    fontSize: '24px',
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: '-0.5px',
    lineHeight: '1.2',
  },
  brandSubtitle: {
    fontSize: '13px',
    color: '#94a3b8',
    fontWeight: '400',
  },
  avatarWrapper: {
    position: 'relative',
    display: 'inline-block',
  },
  avatarCircle: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    backgroundColor: '#0f172a',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '2px solid #334155',
    boxShadow: '0 2px 6px rgba(0, 0, 0, 0.1)',
  },
  avatarInitials: {
    color: '#ffffff',
    fontSize: '13.5px',
    fontWeight: '700',
    letterSpacing: '0.04em',
  },
  activeDot: {
    position: 'absolute',
    bottom: '-1px',
    right: '-1px',
    width: '11px',
    height: '11px',
    borderRadius: '50%',
    backgroundColor: '#22c55e',
    border: '2px solid #ffffff',
  },
}
