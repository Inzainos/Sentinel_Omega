import type { IconProps } from "./types";

export function IconPadre({ size = 24, className = "", color = "currentColor", strokeWidth = 2, fill = "none" }: IconProps) {
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
      <ellipse cx="12" cy="14" rx="10" ry="7" />
      <path d="M12 7v7M7 14h10" strokeWidth={1.5} opacity="0.4" />
      <circle cx="10" cy="11" r="1.5" fill="currentColor" strokeWidth={0} />
      <circle cx="14" cy="11" r="1.5" fill="currentColor" strokeWidth={0} />
      <path d="M9 17c0-1.5 1.5-3 3.5-3s3.5 1.5 3.5 3" strokeWidth={1.5} fill="none" />
    </svg>
  );
}