import type { Meta, StoryObj } from "@storybook/react";
import { CountdownBar } from "./CountdownBar";

const meta: Meta<typeof CountdownBar> = {
  title: "Base/CountdownBar",
  component: CountdownBar,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    active: { control: "boolean" },
    daysElapsed: { control: "number", min: 0, max: 30 },
  },
};

export default meta;
type Story = StoryObj<typeof CountdownBar>;

export const Active: Story = {
  args: {
    daysRemaining: [5, 8] as [number, number],
    daysElapsed: 2,
    active: true,
    label: "Ventana temporal activa",
  },
};

export const Inactive: Story = {
  args: {
    active: false,
    label: "Sin convergencia activa",
  },
};

export const Expiring: Story = {
  args: {
    daysRemaining: [0, 1] as [number, number],
    daysElapsed: 0,
    active: true,
    label: "Ventana por expirar",
  },
};

export const LongWindow: Story = {
  args: {
    daysRemaining: [10, 20] as [number, number],
    daysElapsed: 5,
    active: true,
    label: "Ventana extendida",
  },
};