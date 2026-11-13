import type { Meta, StoryObj } from "@storybook/react";
import { WallSegment } from "./WallSegment";

const meta: Meta<typeof WallSegment> = {
  title: "Base/WallSegment",
  component: WallSegment,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof WallSegment>;

export const Active: Story = {
  args: {
    name: "Geofísico",
    types: ["Seismic Cluster", "Volcánico", "Fantasma"],
    active: true,
    activeTypes: new Set(["SEISMICCLUSTER", "FANTASMA"]),
  },
};

export const Inactive: Story = {
  args: {
    name: "Atmosférico",
    types: ["Blue Jet", "Sprite Rojo", "Niebla Tule"],
    active: false,
  },
};

export const Breach: Story = {
  args: {
    name: "Solar / Geomag.",
    types: ["Silent Trigger", "Tormenta Solar", "Schumann", "GRB"],
    active: true,
    activeTypes: new Set(["TORMENTASOLAR", "SCHUMANN", "GRB", "SILENTTRIGGER"]),
  },
};

export const AllWalls: Story = {
  render: () => (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 w-full max-w-4xl">
      <WallSegment name="Geofísico" types={["Seismic Cluster", "Volcánico", "Fantasma"]} active={true} activeTypes={new Set(["SEISMICCLUSTER", "FANTASMA"])} />
      <WallSegment name="Atmosférico" types={["Blue Jet", "Sprite Rojo", "Niebla Tule"]} active={false} />
      <WallSegment name="Oceánico" types={["Tsunami", "Huracán"]} active={false} />
      <WallSegment name="Solar / Geomag." types={["Silent Trigger", "Tormenta Solar", "Schumann", "GRB"]} active={true} activeTypes={new Set(["TORMENTASOLAR", "SCHUMANN"])} />
      <WallSegment name="Financiero" types={["Correlación fin."]} active={false} />
    </div>
  ),
};