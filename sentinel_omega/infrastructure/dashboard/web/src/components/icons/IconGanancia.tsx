import type { IconProps } from "./types";

export function IconGanancia({ size = 24, className = "", color = "currentColor", strokeWidth = 2, fill = "none" }: IconProps) {
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
      <path d="M18 3L12 9l-6-6" />
      <path d="M12 9V3M12 9H3M12 9h9" strokeWidth={1.5} opacity="0.4" />
      <path d="M3 21h18M3 15h18M3 9h18" strokeWidth={1.5} strokeDasharray="2 4" opacity="0.3" />
      <polyline points="3,21 7,15 11,21 15,15 19,21" fill="none" strokeWidth={1.5} opacity="0.5" />
    </svg>
  );
}