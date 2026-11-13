export interface IconProps {
  size?: number;
  className?: string;
  color?: string;
  strokeWidth?: number;
  fill?: string;
  style?: React.CSSProperties;
}

export const createIcon = (svg: React.ReactNode) => {
  return svg;
};