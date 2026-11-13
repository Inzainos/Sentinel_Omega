import type { IconProps } from "./types";

export function IconConsenso({ size = 24, className = "", color = "currentColor", strokeWidth = 2, fill = "none" }: IconProps) {
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
      <circle cx="6" cy="12" r="4" opacity="0.5" />
      <circle cx="18" cy="12" r="4" opacity="0.5" />
      <circle cx="12" cy="5" r="4" opacity="0.5" />
      <circle cx="12" cy="19" r="4" opacity="0.5" />
      <circle cx="12" cy="12" r="4" fill="currentColor" strokeWidth={0} />
      <path d="M10 12h4M12 10v4" strokeWidth={1.5} opacity="0.6" />
      <path d="M6 12h1.5M16.5 12H18M12 6.5V8M12 16v1.5" strokeWidth={1.5} opacity="0.4" />
    </svg>
  );
}