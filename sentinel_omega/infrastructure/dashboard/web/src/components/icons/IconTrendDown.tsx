import type { IconProps } from "./types";

export function IconTrendDown({ size = 24, className = "", color = "currentColor", strokeWidth = 2, fill = "none" }: IconProps) {
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
      <polyline points="1 18 11 8 17 14 21 10" fill="none" />
      <line x1="7" y1="4" x2="7" y2="14" strokeDasharray="3 3" opacity="0.4" />
      <line x1="17" y1="4" x2="17" y2="10" strokeDasharray="3 3" opacity="0.4" />
    </svg>
  );
}