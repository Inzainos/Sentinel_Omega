import type { IconProps } from "./types";

export function IconJuez({ size = 24, className = "", color = "currentColor", strokeWidth = 2, fill = "none" }: IconProps) {
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
      <path d="M12 2L4 8v12c0 2.2 1.8 4 4 4h12c2.2 0 4-1.8 4-4V8L12 2z" />
      <line x1="12" y1="14" x2="12" y2="22" strokeWidth={1.5} />
      <path d="M16 10H8M16 14H8" strokeWidth={1.5} opacity="0.4" />
      <polygon points="12,4 16,8 12,12 8,8" fill="currentColor" strokeWidth={0} opacity="0.5" />
    </svg>
  );
}