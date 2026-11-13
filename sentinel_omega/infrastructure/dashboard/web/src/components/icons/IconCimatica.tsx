import type { IconProps } from "./types";

export function IconCimatica({ size = 24, className = "", color = "currentColor", strokeWidth = 2, fill = "none" }: IconProps) {
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
      <circle cx="12" cy="12" r="10" opacity="0.2" />
      <circle cx="12" cy="12" r="6" opacity="0.4" />
      <circle cx="12" cy="12" r="3" fill="currentColor" strokeWidth={0} />
      <path d="M12 2v2M12 20v2M2 12h2M20 12h2" strokeWidth={1.5} opacity="0.6" />
      <path d="M4.9 4.9l2 2M17.1 4.9l-2 2M4.9 17.1l2-2M17.1 17.1l-2-2" strokeWidth={1.5} opacity="0.4" />
      <ellipse cx="12" cy="12" rx="8" ry="2" strokeDasharray="4 4" opacity="0.3" />
      <ellipse cx="12" cy="12" rx="2" ry="8" strokeDasharray="4 4" opacity="0.3" />
    </svg>
  );
}