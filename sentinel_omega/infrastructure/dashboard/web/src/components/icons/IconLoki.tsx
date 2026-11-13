import type { IconProps } from "./types";

export function IconLoki({ size = 24, className = "", color = "currentColor", strokeWidth = 2, fill = "none" }: IconProps) {
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
      <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z" opacity="0.2" />
      <path d="M12 6v12M6 12h12" strokeWidth={1.5} opacity="0.4" />
      <path d="M16.24 7.76a6 6 0 1 1-8.48 8.48M7.76 7.76a6 6 0 1 0 8.48 8.48" opacity="0.5" />
      <circle cx="12" cy="12" r="3" fill="currentColor" strokeWidth={0} />
    </svg>
  );
}