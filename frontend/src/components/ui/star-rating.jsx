import { useState } from 'react';

/**
 * Clickable 1-5 star rating. Click a star to set rating, click same star again to clear.
 * @param {number|null} value - current rating (1-5 or null)
 * @param {function} onChange - called with new rating (1-5 or null)
 * @param {boolean} readOnly - if true, stars are not clickable
 * @param {string} size - "sm" | "md" (default "sm")
 */
export function StarRating({ value, onChange, readOnly = false, size = 'sm' }) {
  const [hover, setHover] = useState(null);

  const starSize = size === 'md' ? 'text-lg' : 'text-sm';
  const gap = size === 'md' ? 'gap-0.5' : 'gap-px';

  return (
    <span
      className={`inline-flex ${gap} ${readOnly ? '' : 'cursor-pointer'}`}
      onMouseLeave={() => !readOnly && setHover(null)}
    >
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = star <= (hover ?? value ?? 0);
        return (
          <span
            key={star}
            className={`${starSize} select-none ${filled ? 'text-yellow-500' : 'text-muted-foreground/30'} ${readOnly ? '' : 'hover:scale-110 transition-transform'}`}
            onMouseEnter={() => !readOnly && setHover(star)}
            onClick={(e) => {
              if (readOnly) return;
              e.stopPropagation();
              onChange?.(star === value ? null : star);
            }}
          >
            ★
          </span>
        );
      })}
    </span>
  );
}
