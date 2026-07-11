export default function FlashMessages({ message, type }) {
  return (
    <div className="flash-messages" aria-live="polite" aria-atomic="true">
      <div className={`flash flash-${type}`} role="status">{message}</div>
    </div>
  );
}
