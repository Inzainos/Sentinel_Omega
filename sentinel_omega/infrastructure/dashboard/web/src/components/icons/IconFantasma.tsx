import type { IconProps } from "./types";

export function IconFantasma({ size = 24, className = "", color = "currentColor", strokeWidth = 2, fill = "none" }: IconProps) {
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
      <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2z" opacity="0.3" />
      <path d="M12 6v6M12 6a6 6 0 0 1 0 12M12 6a6 6 0 0 0 0 12" strokeDasharray="4 4" />
      <circle cx="12" cy="12" r="3" opacity="0.5" />
    </svg>
  );
}