import type { Meta, StoryObj } from "@storybook/react";
import { KpiCard } from "./KpiCard";
import { IconFantasma, IconMuro, IconSchumann, IconGanancia } from "@/components/icons";

const meta: Meta<typeof KpiCard> = {
  title: "Base/KpiCard",
  component: KpiCard,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
  argTypes: {
    label: { control: "text" },
    value: { control: "text" },
    hint: { control: "text" },
    accent: { control: "color" },
    trend: { control: "select", options: ["up", "down", "neutral"] },
    trendValue: { control: "text" },
    size: { control: "select", options: ["sm", "md", "lg"] },
  },
};

export default meta;
type Story = StoryObj<typeof KpiCard>;

export const Default: Story = {
  args: {
    label: "FANTASMA",
    value: 42.7,
    hint: "índice de riesgo cósmico",
    accent: "#00d4ff",
    trend: "up",
    trendValue: "+2.3%",
    icon: <IconFantasma size={20} />,
    size: "md",
  },
};

export const Muro: Story = {
  args: {
    label: "MURO",
    value: "3 / 5",
    hint: "sin rotura",
    accent: "#ff9100",
    trend: "neutral",
    icon: <IconMuro size={20} />,
    size: "md",
  },
};

export const Schumann: Story = {
  args: {
    label: "SCHUMANN",
    value: "7.83 Hz",
    hint: "vs 7.83 · Δ +0.02",
    accent: "#7c4dff",
    trend: "down",
    trendValue: "-0.1%",
    icon: <IconSchumann size={20} />,
    size: "md",
  },
};

export const Ganancia: Story = {
  args: {
    label: "GANANCIA REAL",
    value: "1.17×",
    hint: "1× = no aporta",
    accent: "#d946ef",
    trend: "up",
    trendValue: "+0.04×",
    icon: <IconGanancia size={20} />,
    size: "md",
  },
};

export const Small: Story = {
  args: {
    label: "NODOS",
    value: "125",
    hint: "puntos de topología",
    accent: "#00d4ff",
    size: "sm",
  },
};

export const Large: Story = {
  args: {
    label: "SISMOS ≥4.5",
    value: "23",
    hint: "umbral de alerta del Padre",
    accent: "#ff1744",
    trend: "up",
    trendValue: "+5",
    size: "lg",
  },
};