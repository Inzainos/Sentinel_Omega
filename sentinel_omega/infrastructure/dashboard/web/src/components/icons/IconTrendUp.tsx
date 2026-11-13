import type { IconProps } from "./types";

export function IconTrendUp({ size = 24, className = "", color = "currentColor", strokeWidth = 2, fill = "none" }: IconProps) {
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
      <polyline points="23 6 13 16 7 10 3 14" fill="none" />
      <line x1="17" y1="20" x2="17" y2="10" strokeDasharray="3 3" opacity="0.4" />
      <line x1="7" y1="20" x2="7" y2="14" strokeDasharray="3 3" opacity="0.4" />
    </svg>
  );
}