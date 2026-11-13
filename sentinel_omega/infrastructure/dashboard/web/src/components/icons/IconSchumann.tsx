import type { IconProps } from "./types";

export function IconSchumann({ size = 24, className = "", color = "currentColor", strokeWidth = 2, fill = "none" }: IconProps) {
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
      <path d="M12 22V12M12 12c0-3.3 2.7-6 6-6M12 12c0-3.3-2.7-6-6-6" />
      <path d="M12 12c0 3.3 2.7 6 6 6M12 12c0 3.3-2.7 6-6 6" strokeDasharray="3 3" opacity="0.4" />
      <path d="M2 12h2M20 12h2M12 2v2M12 20v2" strokeWidth={1.5} opacity="0.6" />
      <circle cx="12" cy="12" r="2" fill="currentColor" strokeWidth={0} />
    </svg>
  );
}