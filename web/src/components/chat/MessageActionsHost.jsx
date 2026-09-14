import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { CloseIcon, TrashIcon } from '../icons'

/**
 * Single-instance contextual menu host for message actions.
 *
 * Rendered once per message list (not per bubble) so only ONE message menu /
 * reaction picker / delete confirmation can be open at a time. Everything is
 * rendered through a portal on document.body so restrictive ancestors
 * (overflow-y-auto lists, bubbles whose entrance animation keeps a transform)
 * can never clip or mis-constrain the popover.
 *
 * - Opens above the anchor, flipping below when there is no room.
 * - Clamps to viewport edges so it stays usable near both sides of the chat.
 * - Closes on outside click, on Escape, or after an action runs.
 */

const REACTION_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '🙏', '🔥', '👎']
const VIEWPORT_MARGIN = 8

function clamp(value, min, max) {
  return Math.max(min, Math.min(value, max))
}

export default function MessageActionsHost({
  menu,
  currentUserId,
  onClose,
  onDelete,
  onReact,
}) {
  const [position, setPosition] = useState(null)
  const [deletePhase, setDeletePhase] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const surfaceRef = useRef(null)

  // Reset internal phase whenever the active menu changes.
  useEffect(() => {
    setDeletePhase(false)
    setIsDeleting(false)
  }, [menu])

  // Close on outside click and on Escape.
  useEffect(() => {
    if (!menu) return undefined
    const handleMouseDown = (event) => {
      const insideSurface = surfaceRef.current?.contains(event.target)
      const insideAnchor = menu.anchorEl?.contains(event.target)
      if (insideSurface || insideAnchor) return
      onClose()
    }
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('mousedown', handleMouseDown)
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('mousedown', handleMouseDown)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [menu, onClose])
// Measure the popover, then position it and clamp it to the viewport.
  useLayoutEffect(() => {
    if (!menu || menu.kind === 'delete') {
      setPosition(null)
      return undefined
    }
    setPosition(null)
    let frame = 0
    frame = window.requestAnimationFrame(() => {
      const popover = surfaceRef.current
      const width = popover ? popover.offsetWidth : 208
      const height = popover ? popover.offsetHeight : 120
      const viewportWidth = window.innerWidth
      const viewportHeight = window.innerHeight

      // Prefer the rect captured at click time. The anchor element (the
      // message-toolbar button) lives in a group-hover container and may be
      // hidden by the time this effect re-runs (e.g. when the delete
      // confirmation replaces the More menu), which would report a
      // zero-rect and pin the popover to the top of the viewport.
      const anchorRect = menu.anchorRect
        ? {
            left: menu.anchorRect.left,
            right: menu.anchorRect.right,
            top: menu.anchorRect.top,
            bottom: menu.anchorRect.bottom,
          }
        : menu.anchorEl
          ? menu.anchorEl.getBoundingClientRect()
          : {
              left: menu.position?.x || 0,
              right: menu.position?.x || 0,
              top: menu.position?.y || 0,
              bottom: menu.position?.y || 0,
            }

      let left = anchorRect.right - width
      if (left < VIEWPORT_MARGIN) left = anchorRect.left
      left = clamp(left, VIEWPORT_MARGIN, Math.max(VIEWPORT_MARGIN, viewportWidth - width - VIEWPORT_MARGIN))

      const spaceAbove = anchorRect.top
      const spaceBelow = viewportHeight - anchorRect.bottom
      let top
      if (spaceAbove >= height + VIEWPORT_MARGIN) {
        top = anchorRect.top - height - VIEWPORT_MARGIN
      } else if (spaceBelow >= height + VIEWPORT_MARGIN) {
        top = anchorRect.bottom + VIEWPORT_MARGIN
      } else {
        const clampedHeight = Math.min(height, viewportHeight - 2 * VIEWPORT_MARGIN)
        top = clamp(anchorRect.bottom - clampedHeight, VIEWPORT_MARGIN, Math.max(VIEWPORT_MARGIN, viewportHeight - height - VIEWPORT_MARGIN))
      }
      setPosition({ left: Math.round(left), top: Math.round(top) })
    })
    return () => window.cancelAnimationFrame(frame)
  }, [menu, deletePhase])

  if (!menu) return null

  const isOutgoing = menu.message.sender_id === currentUserId

  const handleDelete = async (mode) => {
    setIsDeleting(true)
    try {
      await onDelete(menu.message, mode)
    } catch {
      // Parent components surface the error; the menu still closes.
    } finally {
      setIsDeleting(false)
      onClose()
    }
  }

  return createPortal(
    <div
      ref={surfaceRef}
      style={position
        ? { position: 'fixed', left: `${position.left}px`, top: `${position.top}px`, zIndex: 60 }
        : { position: 'fixed', visibility: 'hidden', zIndex: 60 }}
    >
      {deletePhase || menu.kind === 'delete' ? (
        <div
          className="w-72 max-w-[calc(100vw-16px)] max-h-[calc(100vh-32px)] overflow-y-auto bg-surface-elevated border border-border rounded-xl shadow-popover p-3 panel-enter"
          role="dialog"
          aria-label="Delete message"
        >
          <h3 className="text-sm font-semibold text-text-primary mb-1 px-1">Delete message?</h3>
          <button
            type="button"
            className="w-full flex items-center gap-2 px-2.5 py-2 text-left text-sm text-text-primary hover:bg-surface-hover rounded-lg transition-colors disabled:opacity-50"
            disabled={isDeleting}
            onClick={() => handleDelete('me')}
          >
            <TrashIcon className="w-4 h-4 text-text-muted" />
            Delete for Me
          </button>
          {isOutgoing && (
            <button
              type="button"
              className="w-full flex items-center gap-2 px-2.5 py-2 text-left text-sm text-danger hover:bg-danger/10 rounded-lg transition-colors disabled:opacity-50"
              disabled={isDeleting}
              onClick={() => handleDelete('everyone')}
            >
              <TrashIcon className="w-4 h-4" />
              Delete for Everyone
            </button>
          )}
          <button
            type="button"
            className="w-full flex items-center gap-2 px-2.5 py-2 text-left text-sm text-text-muted hover:bg-surface-hover rounded-lg transition-colors disabled:opacity-50"
            disabled={isDeleting}
            onClick={() => {
              if (menu.kind === 'delete') onClose()
              else setDeletePhase(false)
            }}
          >
            <CloseIcon className="w-4 h-4" />
            Cancel
          </button>
        </div>
      ) : (
        <>
          {menu.kind === 'reaction' && (
            <div className="flex gap-1 rounded-xl border border-border bg-surface-elevated p-1 shadow-popover menu-enter">
              {REACTION_EMOJIS.map((emoji) => (
                <button
                  key={emoji}
                  type="button"
                  className="rounded-md p-1 text-base hover:bg-surface-hover transition-all hover:scale-110"
                  title={`React with ${emoji}`}
                  onClick={() => {
                    onReact(menu.message, emoji)
                    onClose()
                  }}
                >
                  {emoji}
                </button>
              ))}
            </div>
          )}
          {menu.kind === 'more' && (
            <div className="glass rounded-xl shadow-popover p-1 w-52 menu-enter">
              <button
                type="button"
                className="w-full flex items-center gap-2 px-2.5 py-2 text-left text-sm text-text-primary hover:bg-surface-hover rounded-lg transition-colors disabled:opacity-50"
                disabled={isDeleting}
                onClick={() => setDeletePhase(true)}
              >
                <TrashIcon className="w-4 h-4 text-danger" />
                Delete message
              </button>
            </div>
          )}
        </>
      )}
    </div>,
    document.body,
  )
}