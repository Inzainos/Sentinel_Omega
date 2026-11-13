import type { IconProps } from "./types";

export function IconAlertaCritical({ size = 24, className = "", color = "currentColor", strokeWidth = 2, fill = "none" }: IconProps) {
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
      <circle cx="12" cy="12" r="10" fill="currentColor" strokeWidth={0} opacity="0.15" />
      <path d="M12 2v4M12 18v4M2 12h4M18 12h4" strokeWidth={3} />
      <path d="M4.9 4.9l2.8 2.8M16.3 4.9l-2.8 2.8M4.9 17.1l2.8-2.8M16.3 17.1l-2.8-2.8" strokeWidth={3} />
      <path d="M12 8v4M12 16h.01" strokeWidth={2.5} />
    </svg>
  );
}