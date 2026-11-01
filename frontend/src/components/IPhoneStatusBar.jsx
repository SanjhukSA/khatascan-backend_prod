import React from 'react'

export default function IPhoneStatusBar() {
  return (
    <div className="iphone-status-bar" style={styles.statusBar}>
      {/* Time on upper left */}
      <div style={styles.timeContainer}>
        <span style={styles.timeText}>9:41</span>
      </div>

      {/* Centered Dynamic Island */}
      <div style={styles.dynamicIsland}>
        <div style={styles.islandInner}>
          <div style={styles.islandSensor} />
          <div style={styles.islandCamera}>
            <div style={styles.islandCameraLens} />
          </div>
        </div>
      </div>

      {/* Cellular, Wi-Fi, Battery */}
      <div style={styles.systemIcons}>
        {/* Cellular Signal */}
        <svg style={styles.icon} width="16" height="10" viewBox="0 0 17 11" fill="none">
          <rect x="0.5" y="7" width="2.5" height="4" rx="0.6" fill="#000000" />
          <rect x="4.8" y="4.8" width="2.5" height="6.2" rx="0.6" fill="#000000" />
          <rect x="9.2" y="2.5" width="2.5" height="8.5" rx="0.6" fill="#000000" />
          <rect x="13.5" y="0.2" width="2.5" height="10.8" rx="0.6" fill="#000000" />
        </svg>

        {/* Wi-Fi Icon */}
        <svg style={styles.icon} width="15" height="11" viewBox="0 0 16 12" fill="none">
          <path
            d="M8 9.6a1.4 1.4 0 1 1 0 2.8 1.4 1.4 0 0 1 0-2.8Z"
            fill="#000000"
          />
          <path
            d="M4.6 7.2c1.9-1.8 4.9-1.8 6.8 0"
            stroke="#000000"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
          <path
            d="M1.6 4.2c3.5-3.4 9.3-3.4 12.8 0"
            stroke="#000000"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>

        {/* Battery with body and nub */}
        <div style={styles.batteryContainer}>
          <div style={styles.batteryBody}>
            <div style={styles.batteryLevel} />
          </div>
          <div style={styles.batteryNub} />
        </div>
      </div>
    </div>
  )
}

const styles = {
  statusBar: {
    height: '44px',
    padding: '0 20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    position: 'relative',
    background: '#ffffff',
    zIndex: 50,
    userSelect: 'none',
    flexShrink: 0,
    boxSizing: 'border-box',
    width: '100%',
  },
  timeContainer: {
    width: '46px',
    display: 'flex',
    alignItems: 'center',
  },
  timeText: {
    fontSize: '14.5px',
    fontWeight: '600',
    letterSpacing: '-0.2px',
    color: '#000000',
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", sans-serif',
  },
  dynamicIsland: {
    position: 'absolute',
    left: '50%',
    top: '8px',
    transform: 'translateX(-50%)',
    width: '120px',
    height: '31px',
    backgroundColor: '#000000',
    borderRadius: '16px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    paddingRight: '10px',
    boxShadow: '0 0 1px rgba(0,0,0,0.8)',
    zIndex: 60,
  },
  islandInner: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  islandSensor: {
    width: '5.5px',
    height: '5.5px',
    borderRadius: '50%',
    backgroundColor: '#0b161e',
  },
  islandCamera: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    backgroundColor: '#071018',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '0.8px solid #0d2232',
  },
  islandCameraLens: {
    width: '4.5px',
    height: '4.5px',
    borderRadius: '50%',
    backgroundColor: '#08343e',
    boxShadow: 'inset 0 0 1px #0ea5e9',
  },
  systemIcons: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    width: '56px',
    justifyContent: 'flex-end',
  },
  icon: {
    display: 'block',
  },
  batteryContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '1px',
  },
  batteryBody: {
    width: '22px',
    height: '11px',
    border: '1.2px solid #000000',
    borderRadius: '3px',
    padding: '1.2px',
    boxSizing: 'border-box',
    display: 'flex',
    alignItems: 'center',
  },
  batteryLevel: {
    width: '100%',
    height: '100%',
    backgroundColor: '#000000',
    borderRadius: '1.2px',
  },
  batteryNub: {
    width: '1.2px',
    height: '3.6px',
    backgroundColor: '#000000',
    borderTopRightRadius: '1px',
    borderBottomRightRadius: '1px',
  },
}
