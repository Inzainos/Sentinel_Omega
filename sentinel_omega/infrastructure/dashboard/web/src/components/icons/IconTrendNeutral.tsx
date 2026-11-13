import type { IconProps } from "./types";

export function IconTrendNeutral({ size = 24, className = "", color = "currentColor", strokeWidth = 2, fill = "none" }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={fill}
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <line x1="3" y1="12" x2="21" y2="12" />
      <path d="M8 16h8M8 8h8" strokeWidth={1.5} opacity="0.4" />
      <circle cx="12" cy="12" r="3" fill="currentColor" strokeWidth={0} opacity="0.3" />
    </svg>
  );
}