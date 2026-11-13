import type { Meta, StoryObj } from "@storybook/react";
import { LoadingSkeleton } from "./LoadingSkeleton";

const meta: Meta<typeof LoadingSkeleton> = {
  title: "Base/LoadingSkeleton",
  component: LoadingSkeleton,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  argTypes: {
    variant: { control: "select", options: ["card", "kpi", "table", "chart", "text", "gauge"] },
    rows: { control: "number", min: 1, max: 10 },
  },
};

export default meta;
type Story = StoryObj<typeof LoadingSkeleton>;

export const Card: Story = { args: { variant: "card" } };
export const Kpi: Story = { args: { variant: "kpi" } };
export const Table: Story = { args: { variant: "table", rows: 5 } };
export const Chart: Story = { args: { variant: "chart" } };
export const Text: Story = { args: { variant: "text", rows: 4 } };
export const Gauge: Story = { args: { variant: "gauge" } };

export const AllVariants: Story = {
  render: () => (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 w-full max-w-5xl">
      <LoadingSkeleton variant="card" />
      <LoadingSkeleton variant="kpi" />
      <LoadingSkeleton variant="table" rows={3} />
      <LoadingSkeleton variant="chart" />
      <LoadingSkeleton variant="text" rows={4} />
      <LoadingSkeleton variant="gauge" />
    </div>
  ),
};