import type { Meta, StoryObj } from "@storybook/react";
import { RiskBadge } from "./RiskBadge";

const meta: Meta<typeof RiskBadge> = {
  title: "Base/RiskBadge",
  component: RiskBadge,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    level: { control: "select", options: ["LOW", "MODERATE", "HIGH", "CRITICAL"] },
    size: { control: "select", options: ["sm", "md", "lg"] },
    pulse: { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof RiskBadge>;

export const Low: Story = { args: { level: "LOW" } };
export const Moderate: Story = { args: { level: "MODERATE" } };
export const High: Story = { args: { level: "HIGH" } };
export const Critical: Story = { args: { level: "CRITICAL" } };
export const CriticalPulse: Story = { args: { level: "CRITICAL", pulse: true } };
export const AllSizes: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-4">
      <RiskBadge level="LOW" size="sm" />
      <RiskBadge level="LOW" size="md" />
      <RiskBadge level="LOW" size="lg" />
    </div>
  ),
};