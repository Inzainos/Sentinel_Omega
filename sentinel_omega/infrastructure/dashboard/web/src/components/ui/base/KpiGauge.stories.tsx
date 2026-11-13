import type { Meta, StoryObj } from "@storybook/react";
import { KpiGauge } from "./KpiGauge";

const meta: Meta<typeof KpiGauge> = {
  title: "Base/KpiGauge",
  component: KpiGauge,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
  argTypes: {
    value: { control: "number", min: 0, max: 100 },
    label: { control: "text" },
    unit: { control: "text" },
    min: { control: "number" },
    max: { control: "number" },
    size: { control: "number" },
    strokeWidth: { control: "number" },
    animate: { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof KpiGauge>;

export const Default: Story = {
  args: {
    value: 67,
    label: "Fantasma",
    unit: "",
    animate: true,
  },
};

export const Critical: Story = {
  args: {
    value: 92,
    label: "Muro",
    unit: "/5",
    animate: true,
  },
};

export const Low: Story = {
  args: {
    value: 12,
    label: "Schumann Activity",
    unit: "%",
    animate: true,
  },
};

export const Large: Story = {
  args: {
    value: 45,
    label: "Ganancia Real",
    unit: "×",
    size: 180,
    strokeWidth: 10,
    animate: true,
  },
};

export const Static: Story = {
  args: {
    value: 38,
    label: "Asertividad",
    unit: "%",
    animate: false,
  },
};