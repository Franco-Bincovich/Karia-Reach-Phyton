import { useEffect, useRef } from 'react'
import './Modal.css'

export default function Modal({ title, onClose, children }) {
  const contentRef = useRef(null)
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onCloseRef.current() }
    document.addEventListener('keydown', handleKey)

    const focusable = contentRef.current?.querySelector('input, button, textarea, select')
    focusable?.focus()

    return () => document.removeEventListener('keydown', handleKey)
  }, [])

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" ref={contentRef} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="modal-close" onClick={onClose} aria-label="Cerrar">&times;</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}
