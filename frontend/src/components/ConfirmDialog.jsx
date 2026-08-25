import React from 'react';

export default function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmText = 'Delete',
  danger = true,
  onConfirm,
  onCancel
}) {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999
      }}
      onClick={onCancel}
    >
      <div
        id="confirm-dialog-modal"
        style={{
          background: '#ffffff',
          borderRadius: '8px',
          padding: '24px',
          maxWidth: '420px',
          width: '90%',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.2)',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 600, color: danger ? '#c62828' : '#111' }}>
          {title || 'Confirm Action'}
        </h3>
        <p style={{ margin: 0, fontSize: '14px', color: '#444', lineHeight: '1.5', whiteSpace: 'pre-line' }}>
          {message}
        </p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '6px' }}>
          <button
            id="confirm-dialog-cancel-btn"
            type="button"
            onClick={onCancel}
            style={{
              padding: '8px 16px',
              fontSize: '13px',
              fontWeight: 500,
              background: '#f5f5f5',
              color: '#444',
              border: '1px solid #ccc',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
          <button
            id="confirm-dialog-confirm-btn"
            type="button"
            onClick={onConfirm}
            style={{
              padding: '8px 16px',
              fontSize: '13px',
              fontWeight: 600,
              background: danger ? '#d32f2f' : '#1976d2',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
