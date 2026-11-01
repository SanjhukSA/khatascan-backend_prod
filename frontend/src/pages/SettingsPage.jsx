import React from 'react'

export default function SettingsPage() {
  return (
    <div className="page-inner" style={{ padding: '16px 20px 24px' }}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.title}>Settings</h2>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Profile Card */}
        <div style={styles.card}>
          <div style={styles.profileRow}>
            <div style={styles.avatarWrapper}>
              <div style={styles.avatarCircle}>
                <span style={styles.avatarInitials}>PC</span>
              </div>
              <div style={styles.activeDot} />
            </div>
            <div>
              <h3 style={styles.profileName}>Praveen C.</h3>
              <p style={styles.profileRole}>Khatascan User &bull; Free Plan</p>
            </div>
          </div>
        </div>

        {/* System & Connection Info */}
        <div style={styles.card}>
          <h3 style={styles.sectionHeading}>System Information</h3>
          <div style={styles.infoRow}>
            <span style={styles.infoKey}>Application</span>
            <span style={styles.infoValue}>Khatascan Mobile</span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoKey}>Version</span>
            <span style={styles.infoValue}>2.0.0</span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoKey}>Backend API</span>
            <span style={styles.infoValue}>{import.meta.env.VITE_API_URL || 'http://localhost:8000'}</span>
          </div>
          <div style={styles.infoRow}>
            <span style={styles.infoKey}>OCR Engine</span>
            <span style={styles.infoValue}>Google Gemini Flash / RapidOCR</span>
          </div>
        </div>
      </div>
    </div>
  )
}

const styles = {
  header: {
    marginBottom: '20px',
    paddingTop: '6px',
  },
  title: {
    fontSize: '24px',
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: '-0.5px',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: '24px',
    padding: '22px 20px',
    boxShadow: '0 2px 12px rgba(0, 0, 0, 0.03)',
  },
  profileRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  avatarWrapper: {
    position: 'relative',
  },
  avatarCircle: {
    width: '54px',
    height: '54px',
    borderRadius: '50%',
    backgroundColor: '#0f172a',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '2px solid #334155',
  },
  avatarInitials: {
    color: '#ffffff',
    fontSize: '18px',
    fontWeight: '700',
  },
  activeDot: {
    position: 'absolute',
    bottom: '0',
    right: '0',
    width: '13px',
    height: '13px',
    borderRadius: '50%',
    backgroundColor: '#22c55e',
    border: '2.5px solid #ffffff',
  },
  profileName: {
    fontSize: '17px',
    fontWeight: '700',
    color: '#0f172a',
  },
  profileRole: {
    fontSize: '13px',
    color: '#94a3b8',
    marginTop: '2px',
  },
  sectionHeading: {
    fontSize: '16px',
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '4px',
  },
  infoRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '11px 0',
    borderBottom: '1px solid #f1f5f9',
    fontSize: '13.5px',
  },
  infoKey: {
    color: '#64748b',
  },
  infoValue: {
    fontWeight: '600',
    color: '#0f172a',
    maxWidth: '60%',
    textAlign: 'right',
    wordBreak: 'break-all',
  },
}
